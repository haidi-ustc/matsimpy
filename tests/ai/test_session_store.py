"""Tests for SQLite AI session and trace storage."""

from matsimpy.ai.session_store import SessionStore


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
