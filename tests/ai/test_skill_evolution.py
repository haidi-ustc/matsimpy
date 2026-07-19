"""Lifecycle and security tests for approval-gated skill evolution."""

from pathlib import Path

import pytest

from matsimpy.ai.agent_skills import SkillLibrary
from matsimpy.ai.evolution import EvolutionManager, SkillEvolutionError
from matsimpy.ai.session_store import SessionStore


@pytest.fixture
def manager(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    return EvolutionManager(
        store,
        user_skill_root=tmp_path / "skills",
        available_tools={"from_prototype", "write_structure"},
        replay=lambda version, workspace: {
            "passed": "FAIL_REPLAY" not in version.body,
            "details": {"workspace": str(workspace)},
        },
    )


def test_new_draft_is_immutable_and_inactive(manager):
    version = manager.draft_skill(
        name="rocksalt-workflow",
        description="Build a named rocksalt crystal",
        body="Use `from_prototype` then `write_structure`.",
        tools=["from_prototype", "write_structure"],
        source_trace_ids=[11],
    )

    assert version.version == 1
    assert version.status == "draft"
    assert version.parent_version_id is None
    assert version.source_trace_ids == (11,)
    assert not (manager.user_skill_root / version.name).exists()
    with pytest.raises(Exception):
        version.status = "approved"


def test_revision_has_parent_diff_and_remains_inactive(manager):
    first = manager.draft_skill(
        "rocksalt-workflow", "Build rocksalt", "Use `from_prototype`.",
        ["from_prototype"], [11]
    )
    manager.evaluate(first.id)
    manager.approve(first.id)

    revision = manager.draft_revision(
        first.id, body="Use `from_prototype` then `write_structure`.",
        tools=["from_prototype", "write_structure"], source_trace_ids=[12]
    )

    assert revision.version == 2
    assert revision.parent_version_id == first.id
    assert "write_structure" in revision.diff
    assert revision.status == "draft"
    assert manager.store.get_active_skill_version(first.name).id == first.id


def test_deterministic_failure_is_never_approvable_even_if_judge_passes(manager):
    draft = manager.draft_skill(
        "broken-workflow", "Broken workflow", "FAIL_REPLAY `from_prototype`.",
        ["from_prototype"], [21]
    )
    evaluated = manager.evaluate(draft.id, judge_result={"passed": True, "score": 1.0})

    assert evaluated.deterministic_pass is False
    assert evaluated.approvable is False
    with pytest.raises(SkillEvolutionError, match="not approvable"):
        manager.approve(draft.id)


def test_approval_atomically_materializes_standard_skill(manager):
    draft = manager.draft_skill(
        "rocksalt-workflow", "Build rocksalt", "Use `from_prototype`.",
        ["from_prototype"], [31]
    )
    manager.evaluate(draft.id)
    approved = manager.approve(draft.id)

    manifest = SkillLibrary(
        user=manager.user_skill_root,
        available_tools=manager.available_tools,
    )
    assert [item.name for item in manifest.discover()] == ["rocksalt-workflow"]
    assert manifest.activate("rocksalt-workflow").body == "Use `from_prototype`."
    assert approved.status == "approved"
    assert manager.store.get_active_skill_version(approved.name).id == approved.id
    assert not list(manager.user_skill_root.glob(".*.tmp-*"))


def test_rollback_creates_new_auditable_approved_version(manager):
    first = manager.draft_skill(
        "rocksalt-workflow", "Build rocksalt", "First `from_prototype`.",
        ["from_prototype"], [41]
    )
    manager.evaluate(first.id)
    manager.approve(first.id)
    second = manager.draft_revision(
        first.id, body="Second `from_prototype`.", source_trace_ids=[42]
    )
    manager.evaluate(second.id)
    manager.approve(second.id)

    rollback = manager.rollback(first.id, source_trace_ids=[43])

    assert rollback.version == 3
    assert rollback.parent_version_id == second.id
    assert rollback.rollback_of_version_id == first.id
    assert rollback.status == "approved"
    assert rollback.source_trace_ids == (43,)
    assert manager.store.get_active_skill_version(first.name).id == rollback.id
    assert "First" in (manager.user_skill_root / first.name / "SKILL.md").read_text()


@pytest.mark.parametrize(
    "body,tools,error",
    [
        ("Run scripts/build.sh", ["from_prototype"], "scripts"),
        ("pip install unsafe-package", ["from_prototype"], "dependencies"),
        ("Edit matsimpy/core/structure.py", ["from_prototype"], "source"),
        ("Update SOUL.md", ["from_prototype"], "SOUL"),
        ("Use a safe workflow.", ["shell"], "unknown tool"),
    ],
)
def test_unsafe_or_permission_expanding_draft_is_rejected(manager, body, tools, error):
    with pytest.raises(SkillEvolutionError, match=error):
        manager.draft_skill("unsafe-skill", "Unsafe", body, tools, [51])


def test_reject_archives_without_materializing(manager):
    draft = manager.draft_skill(
        "rejected-skill", "Reject me", "Use `from_prototype`.",
        ["from_prototype"], [61]
    )
    rejected = manager.reject(draft.id)
    assert rejected.status == "rejected"
    assert not (manager.user_skill_root / draft.name).exists()


def test_approval_refuses_existing_bundled_script(manager):
    draft = manager.draft_skill(
        "safe-skill", "Safe", "Use `from_prototype`.", ["from_prototype"], [71]
    )
    manager.evaluate(draft.id)
    destination = manager.user_skill_root / draft.name
    (destination / "scripts").mkdir(parents=True)
    (destination / "scripts" / "run.sh").write_text("exit 0")

    with pytest.raises(SkillEvolutionError, match="scripts.*resources"):
        manager.approve(draft.id)
