"""SQLite-backed AI session, trace, and skill draft storage."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

STATE_DB = Path.home() / ".matsimpy" / "ai" / "state.db"


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
        self._refresh_trace_fts_for_session(session_id)
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_task_trace(
        self,
        session_id: int,
        user_request: str,
        plan_summary: str,
        validation_status: str,
        final_response: str,
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
        self._upsert_trace_fts(trace_id)
        self.conn.commit()
        return trace_id

    def search_traces(self, query: str, limit: int = 10) -> list[dict]:
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
            (query, limit),
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
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                workspace TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls_json TEXT,
                tool_call_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                arguments_json TEXT,
                result_json TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS task_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_request TEXT NOT NULL,
                plan_summary TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                final_response TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS skill_drafts (
                name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                source_session_id INTEGER,
                trigger_keywords_json TEXT NOT NULL,
                body TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_session_id) REFERENCES sessions(id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS trace_fts USING fts5(
                trace_id UNINDEXED,
                session_id UNINDEXED,
                user_request,
                plan_summary,
                validation_status UNINDEXED,
                final_response,
                tool_names
            );
            """
        )
        self.conn.commit()

    def _upsert_trace_fts(self, trace_id: int) -> None:
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
                self._tool_names_for_session(row["session_id"]),
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


__all__ = ["STATE_DB", "SessionStore"]
