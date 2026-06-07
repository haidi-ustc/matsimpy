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
