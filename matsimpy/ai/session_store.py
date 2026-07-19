"""SQLite-backed AI session, trace, and skill draft storage."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

STATE_DB = Path.home() / ".matsimpy" / "ai" / "state.db"
_SEARCH_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_SCHEMA_VERSION = 2
AttemptState = Literal["pending", "running", "interrupted", "succeeded", "failed"]
_FINISHED_ATTEMPT_STATES = frozenset({"succeeded", "failed"})


@dataclass(frozen=True)
class ConversationRecord:
    """A durable logical conversation spanning one or more attempts."""

    id: int
    source: str
    workspace: str
    model: str
    provider: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AttemptRecord:
    """One durable execution attempt within a conversation."""

    id: int
    conversation_id: int
    parent_attempt_id: int | None
    state: AttemptState
    user_request: str
    final_response: str | None
    trace_id: int | None
    error: str | None
    created_at: str
    finished_at: str | None


class SessionStore:
    """Persist AI session evidence in a local SQLite database."""

    def __init__(self, path: str | Path = STATE_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def start_session(self, source: str, workspace: str, model: str, provider: str) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO sessions (source, workspace, model, provider, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source, workspace, model, provider, "running"),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def create_conversation(
        self, source: str, workspace: str, model: str, provider: str
    ) -> ConversationRecord:
        """Create and return a durable conversation."""
        cursor = self.conn.execute(
            """
            INSERT INTO conversations (source, workspace, model, provider)
            VALUES (?, ?, ?, ?)
            """,
            (source, workspace, model, provider),
        )
        self.conn.commit()
        return self._get_conversation(int(cursor.lastrowid))

    def list_conversations(self) -> list[ConversationRecord]:
        """Return conversations in stable creation order."""
        rows = self.conn.execute("SELECT * FROM conversations ORDER BY id").fetchall()
        return [self._conversation_from_row(row) for row in rows]

    def load_conversation(
        self, conversation_id: int
    ) -> tuple[ConversationRecord, list[AttemptRecord]]:
        """Load a conversation and its attempts in stable creation order."""
        conversation = self._get_conversation(conversation_id)
        rows = self.conn.execute(
            "SELECT * FROM attempts WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        return conversation, [self._attempt_from_row(row) for row in rows]

    def start_attempt(
        self,
        conversation_id: int,
        user_request: str,
        parent_attempt_id: int | None = None,
    ) -> AttemptRecord:
        """Persist a running attempt, optionally linked to a prior attempt."""
        self._get_conversation(conversation_id)
        if parent_attempt_id is not None:
            parent = self._get_attempt(parent_attempt_id)
            if parent.conversation_id != conversation_id:
                raise ValueError("parent attempt belongs to a different conversation")
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO attempts (
                    conversation_id, parent_attempt_id, state, user_request
                ) VALUES (?, ?, 'running', ?)
                """,
                (conversation_id, parent_attempt_id, user_request),
            )
            self._touch_conversation(conversation_id)
        return self._get_attempt(int(cursor.lastrowid))

    def finish_attempt(
        self,
        attempt_id: int,
        state: Literal["succeeded", "failed"],
        final_response: str | None = None,
        trace_id: int | None = None,
        error: str | None = None,
    ) -> AttemptRecord:
        """Finish a running attempt as succeeded or failed."""
        if state not in _FINISHED_ATTEMPT_STATES:
            raise ValueError("finished attempt state must be 'succeeded' or 'failed'")
        attempt = self._get_attempt(attempt_id)
        if attempt.state != "running":
            raise ValueError(f"attempt {attempt_id} is already {attempt.state}")
        with self.conn:
            self.conn.execute(
                """
                UPDATE attempts
                SET state = ?, final_response = ?, trace_id = ?, error = ?,
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (state, final_response, trace_id, error, attempt_id),
            )
            self._touch_conversation(attempt.conversation_id)
        return self._get_attempt(attempt_id)

    def mark_attempt_interrupted(
        self, attempt_id: int, error: str | None = None
    ) -> AttemptRecord:
        """Durably mark a running attempt as interrupted."""
        attempt = self._get_attempt(attempt_id)
        if attempt.state != "running":
            raise ValueError(f"attempt {attempt_id} is already {attempt.state}")
        with self.conn:
            self.conn.execute(
                """
                UPDATE attempts
                SET state = 'interrupted', error = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (error, attempt_id),
            )
            self._touch_conversation(attempt.conversation_id)
        return self._get_attempt(attempt_id)

    def end_session(self, session_id: int, status: str) -> None:
        self.conn.execute(
            """
            UPDATE sessions
            SET status = ?, ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, session_id),
        )
        self.conn.commit()

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        tool_calls: Any | None = None,
        tool_call_id: str | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO messages (session_id, role, content, tool_calls_json, tool_call_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, self._json_dump(tool_calls), tool_call_id),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_messages_batch(self, session_id: int, rows: list[dict]) -> None:
        """Insert all messages for a session in one transaction."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO messages (session_id, role, content, tool_calls_json, tool_call_id) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        session_id,
                        row["role"],
                        row["content"],
                        self._json_dump(row.get("tool_calls")),
                        row.get("tool_call_id"),
                    )
                    for row in rows
                ],
            )

    def add_tool_calls_batch(self, session_id: int, rows: list[dict]) -> None:
        """Insert all tool calls for a session in one transaction."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO tool_calls (session_id, tool_name, arguments_json, result_json, status) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        session_id,
                        row["tool_name"],
                        self._json_dump(row.get("arguments")),
                        self._json_dump(row.get("result")),
                        row["status"],
                    )
                    for row in rows
                ],
            )

    def add_tool_call(
        self,
        session_id: int,
        tool_name: str,
        arguments: Any,
        result: Any,
        status: str,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO tool_calls (session_id, tool_name, arguments_json, result_json, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                tool_name,
                self._json_dump(arguments),
                self._json_dump(result),
                status,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_task_trace(
        self,
        session_id: int,
        user_request: str,
        plan_summary: str,
        validation_status: str,
        final_response: str,
        tool_names: list[str] | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO task_traces (
                session_id, user_request, plan_summary, validation_status, final_response
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_request, plan_summary, validation_status, final_response),
        )
        trace_id = int(cursor.lastrowid)
        self._upsert_trace_fts(trace_id, tool_names=tool_names)
        self.conn.commit()
        return trace_id

    def search_traces(self, query: str, limit: int = 10) -> list[dict]:
        fts_query = _trace_search_query(query)
        if fts_query is None:
            return []

        rows = self.conn.execute(
            """
            SELECT
                task_traces.id,
                task_traces.session_id,
                task_traces.user_request,
                task_traces.plan_summary,
                task_traces.validation_status,
                task_traces.final_response,
                task_traces.created_at
            FROM trace_fts
            JOIN task_traces ON task_traces.id = trace_fts.trace_id
            WHERE trace_fts MATCH ?
            ORDER BY bm25(trace_fts)
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def save_skill_draft(
        self,
        name: str,
        status: str,
        source_session_id: int,
        trigger_keywords: Any,
        body: str,
        metadata: Any,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO skill_drafts (
                name,
                status,
                source_session_id,
                trigger_keywords_json,
                body,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                status = excluded.status,
                source_session_id = excluded.source_session_id,
                trigger_keywords_json = excluded.trigger_keywords_json,
                body = excluded.body,
                metadata_json = excluded.metadata_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                name,
                status,
                source_session_id,
                self._json_dump(trigger_keywords),
                body,
                self._json_dump(metadata),
            ),
        )
        self.conn.commit()

    def list_skill_drafts(self, status: str | None = None) -> list[dict]:
        if status is None:
            rows = self.conn.execute(
                """
                SELECT *
                FROM skill_drafts
                ORDER BY created_at, name
                """
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT *
                FROM skill_drafts
                WHERE status = ?
                ORDER BY created_at, name
                """,
                (status,),
            ).fetchall()
        return [self._skill_draft_row_to_dict(row) for row in rows]

    def set_skill_draft_status(self, name: str, status: str) -> None:
        self.conn.execute(
            """
            UPDATE skill_drafts
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
            """,
            (status, name),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    version INTEGER NOT NULL CHECK (version >= 0)
                )
                """
            )
            row = self.conn.execute("SELECT version FROM schema_meta").fetchone()
            if row is None:
                self.conn.execute("INSERT INTO schema_meta (version) VALUES (0)")

        version = int(self.conn.execute("SELECT version FROM schema_meta").fetchone()[0])
        if version > _SCHEMA_VERSION:
            raise RuntimeError(
                f"database schema version {version} is newer than supported version {_SCHEMA_VERSION}"
            )
        migrations = (self._migrate_to_v1, self._migrate_to_v2)
        for target_version in range(version + 1, _SCHEMA_VERSION + 1):
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                migrations[target_version - 1]()
                self.conn.execute("UPDATE schema_meta SET version = ?", (target_version,))
            except Exception:
                self.conn.rollback()
                raise
            else:
                self.conn.commit()

    def _migrate_to_v1(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                workspace TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls_json TEXT,
                tool_call_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )""",
            """CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                arguments_json TEXT,
                result_json TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )""",
            """CREATE TABLE IF NOT EXISTS task_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_request TEXT NOT NULL,
                plan_summary TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                final_response TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )""",
            """CREATE TABLE IF NOT EXISTS skill_drafts (
                name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                source_session_id INTEGER,
                trigger_keywords_json TEXT NOT NULL,
                body TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_session_id) REFERENCES sessions(id)
            )""",
            """CREATE VIRTUAL TABLE IF NOT EXISTS trace_fts USING fts5(
                trace_id UNINDEXED,
                session_id UNINDEXED,
                user_request,
                plan_summary,
                validation_status UNINDEXED,
                final_response,
                tool_names
            )""",
        )
        for statement in statements:
            self.conn.execute(statement)

    def _migrate_to_v2(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                workspace TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                parent_attempt_id INTEGER,
                state TEXT NOT NULL CHECK (
                    state IN ('pending', 'running', 'interrupted', 'succeeded', 'failed')
                ),
                user_request TEXT NOT NULL,
                final_response TEXT,
                trace_id INTEGER,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (parent_attempt_id) REFERENCES attempts(id),
                FOREIGN KEY (trace_id) REFERENCES task_traces(id)
            )
            """
        )

    def _get_conversation(self, conversation_id: int) -> ConversationRecord:
        row = self.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown conversation id: {conversation_id}")
        return self._conversation_from_row(row)

    def _get_attempt(self, attempt_id: int) -> AttemptRecord:
        row = self.conn.execute(
            "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown attempt id: {attempt_id}")
        return self._attempt_from_row(row)

    def _touch_conversation(self, conversation_id: int) -> None:
        self.conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

    @staticmethod
    def _conversation_from_row(row: sqlite3.Row) -> ConversationRecord:
        return ConversationRecord(**dict(row))

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> AttemptRecord:
        state = row["state"]
        if state not in {"pending", "running", "interrupted", "succeeded", "failed"}:
            raise ValueError(f"unknown persisted attempt state: {state!r}")
        return AttemptRecord(**dict(row))

    def _upsert_trace_fts(self, trace_id: int, tool_names: list[str] | None = None) -> None:
        row = self.conn.execute(
            """
            SELECT
                id,
                session_id,
                user_request,
                plan_summary,
                validation_status,
                final_response
            FROM task_traces
            WHERE id = ?
            """,
            (trace_id,),
        ).fetchone()
        if row is None:
            return

        if tool_names is None:
            tool_names_str = self._tool_names_for_session(row["session_id"])
        else:
            tool_names_str = " ".join(tool_names)

        self.conn.execute("DELETE FROM trace_fts WHERE trace_id = ?", (trace_id,))
        self.conn.execute(
            """
            INSERT INTO trace_fts (
                trace_id,
                session_id,
                user_request,
                plan_summary,
                validation_status,
                final_response,
                tool_names
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["session_id"],
                row["user_request"],
                row["plan_summary"],
                row["validation_status"],
                row["final_response"],
                tool_names_str,
            ),
        )

    def _refresh_trace_fts_for_session(self, session_id: int) -> None:
        rows = self.conn.execute(
            "SELECT id FROM task_traces WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        for row in rows:
            self._upsert_trace_fts(row["id"])

    def _tool_names_for_session(self, session_id: int) -> str:
        rows = self.conn.execute(
            """
            SELECT tool_name
            FROM tool_calls
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
        return " ".join(row["tool_name"] for row in rows)

    @staticmethod
    def _json_dump(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str)

    @staticmethod
    def _json_load(value: str | None, default: Any) -> Any:
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def _skill_draft_row_to_dict(self, row: sqlite3.Row) -> dict:
        result = dict(row)
        result["trigger_keywords"] = self._json_load(
            result.pop("trigger_keywords_json"),
            [],
        )
        result["metadata"] = self._json_load(result.pop("metadata_json"), {})
        return result


def _trace_search_query(query: str) -> str | None:
    tokens = _SEARCH_TOKEN_RE.findall(query)
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in tokens)


__all__ = ["AttemptRecord", "ConversationRecord", "STATE_DB", "SessionStore"]
