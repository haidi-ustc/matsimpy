"""Tests for workflow skill draft generation and approval."""

from matsimpy.ai.evolution import EvolutionManager
from matsimpy.ai.session_store import SessionStore


def test_evolution_drafts_reusable_success_trace(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.add_tool_call(session_id, "from_prototype", {"prototype": "fcc"}, {"formula": "Cu4"}, "success")
    store.add_tool_call(session_id, "save_structure", {"path": "cu.vasp"}, {"saved_to": "cu.vasp"}, "success")

    manager = EvolutionManager(store)
    draft = manager.draft_from_trace(
        session_id=session_id,
        user_request="create fcc copper and save it",
        final_response="Created and saved copper.",
        validation_status="success",
    )

    assert draft is not None
    assert draft["status"] == "draft"
    assert "from_prototype" in draft["body"]
    assert "save_structure" in draft["body"]
    assert "Validation evidence" in draft["body"]
    assert draft["metadata"]["tools"] == ["from_prototype", "save_structure"]
    assert draft["metadata"]["source_request"] == "create fcc copper and save it"


def test_evolution_skips_failed_or_single_tool_trace(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.add_tool_call(session_id, "from_prototype", {}, {"error": "bad"}, "failure")

    manager = EvolutionManager(store)
    assert manager.draft_from_trace(session_id, "bad run", "failed", "failure") is None


def test_approve_and_reject_skill_draft(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.save_skill_draft(
        "fcc-copper",
        "draft",
        session_id,
        ["fcc", "copper"],
        "# FCC Copper\n",
        {"tools": ["from_prototype"]},
    )

    manager = EvolutionManager(store)
    manager.approve("fcc-copper")
    assert store.list_skill_drafts("approved")[0]["name"] == "fcc-copper"

    manager.reject("fcc-copper")
    assert store.list_skill_drafts("archived")[0]["name"] == "fcc-copper"
