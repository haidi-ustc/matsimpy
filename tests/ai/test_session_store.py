"""Tests for SQLite AI session and trace storage."""

import sqlite3

import pytest

from matsimpy.ai.session_store import AttemptRecord, ConversationRecord, SessionStore


def test_legacy_database_migrates_without_losing_existing_rows(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY, source TEXT NOT NULL, workspace TEXT NOT NULL,
            model TEXT NOT NULL, provider TEXT NOT NULL, status TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, ended_at TEXT
        );
        CREATE TABLE task_traces (
            id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL,
            user_request TEXT NOT NULL, plan_summary TEXT NOT NULL,
            validation_status TEXT NOT NULL, final_response TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO sessions VALUES
            (7, 'legacy', '/work', 'old-model', 'old-provider', 'success',
             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        INSERT INTO task_traces (
            id, session_id, user_request, plan_summary, validation_status, final_response
        ) VALUES (9, 7, 'keep me', 'kept', 'success', 'still here');
        """
    )
    conn.close()

    store = SessionStore(path)

    assert store.conn.execute("SELECT user_request FROM task_traces WHERE id = 9").fetchone()[0] == "keep me"
    assert store.conn.execute("SELECT version FROM schema_meta").fetchone()[0] == 2
    assert {"conversations", "attempts"} <= {
        row[0] for row in store.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def test_conversation_and_linked_attempts_round_trip(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    conversation = store.create_conversation("repl", str(tmp_path), "model", "provider")
    assert isinstance(conversation, ConversationRecord)

    first = store.start_attempt(conversation.id, "build copper")
    assert first.state == "running"
    first = store.finish_attempt(first.id, "failed", error="retryable")
    second = store.start_attempt(conversation.id, "build copper", parent_attempt_id=first.id)
    second = store.finish_attempt(second.id, "succeeded", final_response="Created Cu4", trace_id=None)

    loaded, attempts = store.load_conversation(conversation.id)
    assert loaded == conversation
    assert [attempt.state for attempt in attempts] == ["failed", "succeeded"]
    assert attempts[1].parent_attempt_id == attempts[0].id
    assert attempts[1].final_response == "Created Cu4"
    assert all(isinstance(attempt, AttemptRecord) for attempt in attempts)


def test_conversations_and_attempts_are_ordered_oldest_first(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    first = store.create_conversation("repl", "/one", "m1", "p1")
    second = store.create_conversation("command", "/two", "m2", "p2")
    attempt_one = store.start_attempt(first.id, "first")
    attempt_two = store.start_attempt(first.id, "second", attempt_one.id)

    assert [item.id for item in store.list_conversations()] == [first.id, second.id]
    assert [item.id for item in store.load_conversation(first.id)[1]] == [
        attempt_one.id,
        attempt_two.id,
    ]


def test_attempt_can_be_marked_interrupted_and_cannot_be_finished_twice(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    conversation = store.create_conversation("repl", "/work", "model", "provider")
    attempt = store.start_attempt(conversation.id, "long calculation")

    interrupted = store.mark_attempt_interrupted(attempt.id, error="process stopped")

    assert interrupted.state == "interrupted"
    assert interrupted.error == "process stopped"
    assert interrupted.finished_at is not None
    with pytest.raises(ValueError, match="already interrupted"):
        store.finish_attempt(attempt.id, "failed")


def test_attempt_api_rejects_unknown_ids_invalid_states_and_cross_links(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    first = store.create_conversation("repl", "/one", "model", "provider")
    second = store.create_conversation("repl", "/two", "model", "provider")
    attempt = store.start_attempt(first.id, "request")

    with pytest.raises(KeyError, match="unknown conversation"):
        store.load_conversation(999)
    with pytest.raises(KeyError, match="unknown attempt"):
        store.mark_attempt_interrupted(999)
    with pytest.raises(ValueError, match="succeeded.*failed"):
        store.finish_attempt(attempt.id, "interrupted")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="different conversation"):
        store.start_attempt(second.id, "retry", parent_attempt_id=attempt.id)


def test_pending_state_parses_and_migrated_database_reopens(tmp_path):
    path = tmp_path / "state.db"
    store = SessionStore(path)
    conversation = store.create_conversation("repl", "/work", "model", "provider")
    cursor = store.conn.execute(
        """
        INSERT INTO attempts (conversation_id, state, user_request)
        VALUES (?, 'pending', 'queued request')
        """,
        (conversation.id,),
    )
    store.conn.commit()
    pending_id = int(cursor.lastrowid)
    store.close()

    reopened = SessionStore(path)

    assert reopened.load_conversation(conversation.id)[1][0].state == "pending"
    assert reopened.conn.execute("SELECT version FROM schema_meta").fetchone()[0] == 2
    assert reopened.conn.execute("SELECT COUNT(*) FROM attempts WHERE id = ?", (pending_id,)).fetchone()[0] == 1


def test_failed_migration_rolls_back_its_schema_and_version(tmp_path):
    path = tmp_path / "state.db"

    class FailingMigrationStore(SessionStore):
        def _migrate_to_v2(self):
            super()._migrate_to_v2()
            raise RuntimeError("injected migration failure")

    with pytest.raises(RuntimeError, match="injected migration failure"):
        FailingMigrationStore(path)

    conn = sqlite3.connect(path)
    assert conn.execute("SELECT version FROM schema_meta").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'attempts'"
    ).fetchone()[0] == 0


def test_session_store_records_session_message_tool_and_trace(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session(source="test", workspace=str(tmp_path), model="fake", provider="fake")

    store.add_message(session_id, role="user", content="create fcc Cu")
    store.add_tool_call(
        session_id,
        tool_name="from_prototype",
        arguments={"prototype": "fcc", "species": "Cu"},
        result={"formula": "Cu4", "num_atoms": 4, "_obj_ref": 1},
        status="success",
    )
    trace_id = store.add_task_trace(
        session_id,
        user_request="create fcc Cu",
        plan_summary="Build an FCC copper structure.",
        validation_status="success",
        final_response="Created Cu4.",
    )
    store.end_session(session_id, status="success")

    traces = store.search_traces("copper")
    assert trace_id > 0
    assert len(traces) == 1
    assert traces[0]["session_id"] == session_id
    assert traces[0]["validation_status"] == "success"


def test_session_store_search_traces_handles_literal_punctuation(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session(source="test", workspace=str(tmp_path), model="fake", provider="fake")
    trace_id = store.add_task_trace(
        session_id,
        user_request="create fcc Cu",
        plan_summary="Build an FCC copper structure.",
        validation_status="success",
        final_response="Created Cu4.",
    )

    assert [trace["id"] for trace in store.search_traces("copper?")] == [trace_id]
    assert [trace["id"] for trace in store.search_traces('"copper"')] == [trace_id]
    assert store.search_traces("???") == []


def test_skill_draft_lifecycle(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session(source="test", workspace=str(tmp_path), model="fake", provider="fake")
    store.save_skill_draft(
        name="fcc-copper",
        status="draft",
        source_session_id=session_id,
        trigger_keywords=["fcc", "copper"],
        body="# FCC Copper\n",
        metadata={"tools": ["from_prototype"]},
    )

    drafts = store.list_skill_drafts(status="draft")
    assert [d["name"] for d in drafts] == ["fcc-copper"]

    store.set_skill_draft_status("fcc-copper", "approved")
    approved = store.list_skill_drafts(status="approved")
    assert [d["name"] for d in approved] == ["fcc-copper"]


def test_add_messages_batch_inserts_all_rows_in_one_transaction(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session(
        source="test", workspace=str(tmp_path), model="fake", provider="fake"
    )

    rows = [
        {"role": "user", "content": "create fcc Cu"},
        {"role": "assistant", "content": "Creating FCC copper...",
         "tool_calls": [{"id": "c1", "type": "function",
                         "function": {"name": "from_prototype", "arguments": "{}"}}]},
        {"role": "tool", "content": '{"formula": "Cu4"}', "tool_call_id": "c1"},
    ]
    store.add_messages_batch(session_id, rows)

    db_rows = store.conn.execute(
        "SELECT role, content, tool_calls_json, tool_call_id FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    assert len(db_rows) == 3
    assert db_rows[0]["role"] == "user"
    assert db_rows[0]["content"] == "create fcc Cu"
    assert db_rows[0]["tool_call_id"] is None
    assert db_rows[1]["role"] == "assistant"
    assert db_rows[1]["tool_calls_json"] is not None
    assert db_rows[2]["role"] == "tool"
    assert db_rows[2]["tool_call_id"] == "c1"


def test_add_tool_calls_batch_inserts_all_rows_in_one_transaction(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session(
        source="test", workspace=str(tmp_path), model="fake", provider="fake"
    )

    rows = [
        {"tool_name": "from_prototype",
         "arguments": {"prototype": "fcc", "species": "Cu"},
         "result": {"formula": "Cu4", "num_atoms": 4, "_obj_ref": 1},
         "status": "success"},
        {"tool_name": "save_structure",
         "arguments": {"path": "cu.vasp"},
         "result": {"saved_to": "cu.vasp", "formula": "Cu4", "num_atoms": 4},
         "status": "success"},
    ]
    store.add_tool_calls_batch(session_id, rows)

    db_rows = store.conn.execute(
        "SELECT tool_name, arguments_json, result_json, status FROM tool_calls WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    assert len(db_rows) == 2
    assert db_rows[0]["tool_name"] == "from_prototype"
    assert db_rows[0]["status"] == "success"
    assert db_rows[1]["tool_name"] == "save_structure"
    assert db_rows[1]["status"] == "success"


def test_wal_mode_is_enabled(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    row = store.conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0].upper() == "WAL"
    store.close()
