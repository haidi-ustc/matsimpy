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


def test_evolution_preserves_approved_draft_when_slug_collides(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    first_session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.add_tool_call(first_session_id, "from_prototype", {"prototype": "fcc"}, {"formula": "Cu4"}, "success")
    store.add_tool_call(first_session_id, "save_structure", {"path": "cu.vasp"}, {"saved_to": "cu.vasp"}, "success")

    manager = EvolutionManager(store)
    first_draft = manager.draft_from_trace(
        session_id=first_session_id,
        user_request="create fcc copper and save it",
        final_response="Created and saved copper.",
        validation_status="success",
    )
    assert first_draft is not None
    manager.approve(first_draft["name"])

    second_session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.add_tool_call(second_session_id, "from_prototype", {"prototype": "fcc"}, {"formula": "Cu4"}, "success")
    store.add_tool_call(second_session_id, "save_structure", {"path": "cu2.vasp"}, {"saved_to": "cu2.vasp"}, "success")

    second_draft = manager.draft_from_trace(
        session_id=second_session_id,
        user_request="create fcc copper and save it",
        final_response="Created and saved a second copper structure.",
        validation_status="success",
    )

    assert second_draft is not None
    assert first_draft["name"] == "create-fcc-copper-and-save-it"
    assert second_draft["name"] == "create-fcc-copper-and-save-it-2"
    assert second_draft["status"] == "draft"

    approved = store.list_skill_drafts("approved")
    drafts = store.list_skill_drafts("draft")
    assert [draft["name"] for draft in approved] == [first_draft["name"]]
    assert [draft["name"] for draft in drafts] == [second_draft["name"]]


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
