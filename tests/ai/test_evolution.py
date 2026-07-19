"""Tests for workflow skill draft generation and approval."""

import pytest

from matsimpy.ai import skill_loader
from matsimpy.ai.evolution import EvolutionCandidate, EvolutionManager, EvolutionPolicy
from matsimpy.ai.session_store import SessionStore


@pytest.fixture(autouse=True)
def generated_skill_dir(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    monkeypatch.setattr(skill_loader, "SKILLS_DIR", generated)
    return generated


def test_evolution_does_not_draft_routine_two_tool_success(tmp_path):
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

    assert draft is None


def test_policy_classifies_repeated_workflow_with_trace_provenance():
    policy = EvolutionPolicy()
    history = [
        {"trace_id": 11, "validation_status": "success", "user_request": "build copper", "tools": ["build", "save"]},
        {"trace_id": 12, "validation_status": "success", "user_request": "build nickel", "tools": ["build", "save"]},
    ]

    candidate = policy.classify(history)

    assert candidate == EvolutionCandidate(
        kind="skill",
        rationale="repeated validated workflow",
        source_trace_ids=(11, 12),
        payload={"tool_sequence": ["build", "save"], "occurrences": 2},
    )


def test_policy_classifies_validated_recovery():
    candidate = EvolutionPolicy().classify([
        {
            "trace_id": 21,
            "validation_status": "success",
            "user_request": "recover this structure",
            "tool_calls": [
                {"name": "read_structure", "status": "failure"},
                {"name": "read_structure", "status": "success"},
            ],
        }
    ])

    assert candidate is not None
    assert candidate.kind == "skill"
    assert candidate.rationale == "validated recovery from tool failure"
    assert candidate.source_trace_ids == (21,)


def test_policy_does_not_classify_failure_after_success_as_recovery():
    candidate = EvolutionPolicy().classify([
        {
            "trace_id": 22,
            "validation_status": "success",
            "user_request": "attempt a structure operation",
            "tool_calls": [
                {"name": "read_structure", "status": "success"},
                {"name": "read_structure", "status": "failure"},
            ],
        }
    ])

    assert candidate is None


def test_policy_does_not_classify_unrelated_success_as_recovery():
    candidate = EvolutionPolicy().classify([
        {
            "trace_id": 23,
            "validation_status": "success",
            "user_request": "save and inspect a structure",
            "tool_calls": [
                {"name": "save_structure", "status": "failure"},
                {"name": "inspect_structure", "status": "success"},
            ],
        }
    ])

    assert candidate is None


def test_policy_classifies_explicit_correction_as_memory():
    candidate = EvolutionPolicy().classify(
        [{"trace_id": 31, "validation_status": "success", "user_request": "save POSCAR"}],
        correction="Use VASP format for my crystal files.",
    )

    assert candidate is not None
    assert candidate.kind == "memory"
    assert candidate.rationale == "explicit user correction"
    assert candidate.payload["content"] == "Use VASP format for my crystal files."
    assert candidate.source_trace_ids == (31,)


def test_correction_uses_explicit_trace_id_not_unrelated_history():
    candidate = EvolutionPolicy().classify(
        [
            {"trace_id": 31, "validation_status": "success", "user_request": "old task"},
            {"trace_id": 32, "validation_status": "failure", "user_request": "new task"},
        ],
        correction="Use VASP format.",
        source_trace_id=31,
    )

    assert candidate is not None
    assert candidate.source_trace_ids == (31,)
    assert candidate.payload["provenance"] == "trace"


def test_correction_defaults_to_newest_trace_and_has_empty_request_policy():
    policy = EvolutionPolicy()

    latest = policy.classify(
        [
            {"trace_id": 31, "validation_status": "success", "user_request": "old"},
            {"trace_id": 32, "validation_status": "failure", "user_request": "new"},
        ],
        correction="Use VASP format.",
    )
    request_only = policy.classify([], correction="Use VASP format.")

    assert latest is not None and latest.source_trace_ids == (32,)
    assert latest.payload["provenance"] == "trace"
    assert request_only is not None and request_only.source_trace_ids == ()
    assert request_only.payload["provenance"] == "explicit_request"


def test_correction_rejects_invalid_explicit_trace_id():
    with pytest.raises(ValueError, match="positive integer"):
        EvolutionPolicy().classify(
            [], correction="Use VASP format.", source_trace_id=True
        )


def test_correction_rejects_source_trace_id_missing_from_history():
    with pytest.raises(ValueError, match="not present"):
        EvolutionPolicy().classify(
            [{"trace_id": 70, "validation_status": "success"}],
            correction="Use VASP format.",
            source_trace_id=71,
        )


def test_policy_classifies_explicit_learn_request_without_provider_call():
    candidate = EvolutionPolicy().classify([
        {
            "trace_id": 41,
            "validation_status": "success",
            "user_request": "Remember this workflow for next time",
            "tools": ["build", "write"],
        }
    ])

    assert candidate is not None
    assert candidate.kind == "skill"
    assert candidate.rationale == "explicit learn request"


def test_policy_classifies_nontrivial_validated_workflow():
    candidate = EvolutionPolicy().classify([
        {
            "trace_id": 45,
            "validation_status": "success",
            "user_request": "prepare an analysis model",
            "tools": ["build", "transform", "analyze"],
        }
    ])

    assert candidate is not None
    assert candidate.rationale == "nontrivial validated workflow"
    assert candidate.payload["tool_sequence"] == ["build", "transform", "analyze"]


def test_policy_does_not_call_evaluator_when_deterministic_signal_exists():
    def evaluator(history):
        raise AssertionError("deterministic classification should win")

    candidate = EvolutionPolicy(evaluator=evaluator).classify([
        {
            "trace_id": 46,
            "validation_status": "success",
            "user_request": "learn this workflow",
            "tools": ["build"],
        }
    ])

    assert candidate is not None
    assert candidate.rationale == "explicit learn request"


def test_policy_uses_optional_evaluator_only_after_deterministic_signals():
    calls = []

    def evaluator(history):
        calls.append(history)
        return EvolutionCandidate("skill", "semantic reuse", (51,), {})

    policy = EvolutionPolicy(evaluator=evaluator)
    candidate = policy.classify([
        {"trace_id": 51, "validation_status": "success", "user_request": "complex niche operation", "tools": ["one"]}
    ])

    assert candidate is not None
    assert calls


def test_policy_does_not_reuse_stale_explicit_signal_for_new_routine_trace():
    candidate = EvolutionPolicy().classify([
        {"trace_id": 61, "validation_status": "success", "user_request": "remember this workflow", "tools": ["build"]},
        {"trace_id": 62, "validation_status": "success", "user_request": "show the current structure", "tools": ["inspect"]},
    ])

    assert candidate is None


def test_evolution_preserves_approved_draft_when_slug_collides(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    first_session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.add_tool_call(first_session_id, "from_prototype", {"prototype": "fcc"}, {"formula": "Cu4"}, "success")
    store.add_tool_call(first_session_id, "save_structure", {"path": "cu.vasp"}, {"saved_to": "cu.vasp"}, "success")

    manager = EvolutionManager(store)
    first_draft = manager.draft_from_trace(
        session_id=first_session_id,
        user_request="remember this workflow: create fcc copper and save it",
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
        user_request="remember this workflow: create fcc copper and save it",
        final_response="Created and saved a second copper structure.",
        validation_status="success",
    )

    assert second_draft is not None
    assert first_draft["name"] == "remember-this-workflow-create-fcc-copper-and-save"
    assert second_draft["name"] == "remember-this-workflow-create-fcc-copper-and-save-2"
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


def test_approve_materializes_generated_skill_for_loader(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.save_skill_draft(
        "relax-copper",
        "draft",
        session_id,
        ["relax", "copper"],
        "# Relax Copper\n\nUse the stored relaxation workflow.\n",
        {
            "description": "Relax a copper structure",
            "tools": ["from_prototype", {"function": "relax_structure"}],
        },
    )

    manager = EvolutionManager(store)
    manager.approve("relax-copper")

    approved_drafts = store.list_skill_drafts("approved")
    assert [draft["name"] for draft in approved_drafts] == ["relax-copper"]

    approved_skills = skill_loader.list_generated_skills(status="approved")
    assert len(approved_skills) == 1
    assert approved_skills[0]["name"] == "relax-copper"
    assert approved_skills[0]["status"] == "approved"
    assert approved_skills[0]["body"] == "# Relax Copper\n\nUse the stored relaxation workflow."
    assert approved_skills[0]["description"] == "Relax a copper structure"
    assert approved_skills[0]["load_mode"] == "auto_choice"
    assert approved_skills[0]["tools"] == [
        {"function": "from_prototype"},
        {"function": "relax_structure"},
    ]


def test_approve_materializes_unsafe_draft_name_under_generated_skills(tmp_path, generated_skill_dir):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.save_skill_draft(
        "../outside",
        "draft",
        session_id,
        ["outside"],
        "# Unsafe Draft\n",
        {"tools": ["from_prototype"]},
    )

    manager = EvolutionManager(store)
    manager.approve("../outside")

    paths = list(generated_skill_dir.glob("*.skill.md"))
    assert len(paths) == 1
    assert paths[0].resolve().is_relative_to(generated_skill_dir.resolve())
    assert paths[0].name == "outside.skill.md"
    assert (tmp_path / "outside.skill.md").exists() is False

    approved_skills = skill_loader.list_generated_skills(status="approved")
    assert [skill["name"] for skill in approved_skills] == ["outside"]
    assert ".." not in approved_skills[0]["name"]
    assert "/" not in approved_skills[0]["name"]
    assert "\\" not in approved_skills[0]["name"]


def test_reject_does_not_materialize_generated_skill(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    store.save_skill_draft(
        "draft-only",
        "draft",
        session_id,
        ["draft"],
        "# Draft Only\n",
        {"tools": ["from_prototype"]},
    )

    manager = EvolutionManager(store)
    manager.reject("draft-only")

    assert store.list_skill_drafts("archived")[0]["name"] == "draft-only"
    assert skill_loader.list_generated_skills(status=None) == []


def test_approve_unknown_skill_draft_raises_key_error(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    manager = EvolutionManager(store)

    try:
        manager.approve("missing-draft")
    except KeyError as exc:
        assert "Unknown generated skill draft: missing-draft" in str(exc)
    else:
        raise AssertionError("Expected KeyError for unknown skill draft")
