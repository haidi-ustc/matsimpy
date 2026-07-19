"""Lifecycle and security tests for approval-gated skill evolution."""

import os
from pathlib import Path

import pytest

from matsimpy.ai.agent_skills import SkillLibrary
from matsimpy.ai.evolution import EvolutionManager, SkillEvolutionError
from matsimpy.ai.session_store import SessionStore
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.repl import ReplController
from matsimpy.core import Molecule


def _tool(name):
    return FunctionDef(
        name=name,
        description="test tool",
        parameters={"type": "object", "properties": {}},
        callable=lambda **kwargs: {"ok": True},
    )


@pytest.fixture
def manager(tmp_path):
    store = SessionStore(tmp_path / "state.db")
    session_id = store.start_session("test", str(tmp_path), "fake", "fake")
    for index in range(100):
        store.add_task_trace(
            session_id,
            f"request {index}",
            "plan",
            "success",
            "done",
        )
    return EvolutionManager(
        store,
        user_skill_root=tmp_path / "skills",
        available_tools={
            "from_prototype": _tool("from_prototype"),
            "write_structure": _tool("write_structure"),
        },
        replay=lambda version, context: {
            "passed": "FAIL_REPLAY" not in version.body,
            "details": {"workspace": str(context.workspace.path)},
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


def test_revision_requires_active_approved_parent(manager):
    draft = manager.draft_skill(
        "draft-parent", "Draft", "Use `from_prototype`.", ["from_prototype"], [10]
    )
    with pytest.raises(SkillEvolutionError, match="active approved"):
        manager.draft_revision(draft.id, body="changed", source_trace_ids=[11])


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

    rollback = manager.rollback(first.id)

    assert rollback.version == 3
    assert rollback.parent_version_id == second.id
    assert rollback.rollback_of_version_id == first.id
    assert rollback.status == "approved"
    assert rollback.source_trace_ids == first.source_trace_ids
    assert f"skill_version_id={first.id}" in rollback.diff
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


def test_approval_refuses_symlinked_active_manifest(manager, tmp_path):
    draft = manager.draft_skill(
        "linked-skill", "Linked", "Use `from_prototype`.", ["from_prototype"], [72]
    )
    manager.evaluate(draft.id)
    destination = manager.user_skill_root / draft.name
    destination.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    (destination / "SKILL.md").symlink_to(outside)

    with pytest.raises(SkillEvolutionError, match="symlink"):
        manager.approve(draft.id)


def test_content_tampering_before_evaluation_is_detected(manager):
    draft = manager.draft_skill(
        "tamper-skill", "Tamper", "Use `from_prototype`.", ["from_prototype"], [81]
    )
    manager.store.conn.execute(
        "UPDATE skill_versions SET body = 'changed' WHERE id = ?", (draft.id,)
    )
    manager.store.conn.commit()

    with pytest.raises(SkillEvolutionError, match="content hash"):
        manager.evaluate(draft.id)


def test_content_tampering_after_evaluation_is_detected(manager):
    draft = manager.draft_skill(
        "tamper-skill", "Tamper", "Use `from_prototype`.", ["from_prototype"], [82]
    )
    manager.evaluate(draft.id)
    manager.store.conn.execute(
        "UPDATE skill_versions SET body = 'changed' WHERE id = ?", (draft.id,)
    )
    manager.store.conn.commit()

    with pytest.raises(SkillEvolutionError, match="changed after evaluation"):
        manager.approve(draft.id)


def test_evaluation_is_append_once_and_state_transitions_are_strict(manager):
    draft = manager.draft_skill(
        "once-skill", "Once", "Use `from_prototype`.", ["from_prototype"], [83]
    )
    manager.evaluate(draft.id)
    with pytest.raises(SkillEvolutionError, match="cannot evaluate"):
        manager.evaluate(draft.id)
    with pytest.raises(ValueError, match="invalid.*transition"):
        manager.store.set_skill_version_status(draft.id, "draft")


def test_approval_db_failure_restores_prior_file_and_activation(manager, monkeypatch):
    first = manager.draft_skill(
        "restore-skill", "Restore", "First `from_prototype`.", ["from_prototype"], [84]
    )
    manager.evaluate(first.id)
    manager.approve(first.id)
    prior_bytes = (manager.user_skill_root / first.name / "SKILL.md").read_bytes()
    second = manager.draft_revision(
        first.id, body="Second `from_prototype`.", source_trace_ids=[85]
    )
    manager.evaluate(second.id)
    original = manager.store.set_skill_version_status

    def fail_after_commit(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected database failure")

    monkeypatch.setattr(manager.store, "set_skill_version_status", fail_after_commit)
    with pytest.raises(RuntimeError, match="injected"):
        manager.approve(second.id)

    assert (manager.user_skill_root / first.name / "SKILL.md").read_bytes() == prior_bytes
    assert manager.store.get_active_skill_version(first.name).id == first.id
    assert manager.store.get_skill_version(second.id).status == "evaluated"


def test_first_approval_db_failure_leaves_no_active_file_or_version(manager, monkeypatch):
    draft = manager.draft_skill(
        "first-failure", "Failure", "Use `from_prototype`.", ["from_prototype"], [93]
    )
    manager.evaluate(draft.id)

    def fail(*args, **kwargs):
        raise RuntimeError("injected database failure")

    monkeypatch.setattr(manager.store, "set_skill_version_status", fail)
    with pytest.raises(RuntimeError, match="injected"):
        manager.approve(draft.id)

    assert not (manager.user_skill_root / draft.name).exists()
    with pytest.raises(KeyError, match="no active"):
        manager.store.get_active_skill_version(draft.name)
    assert manager.store.get_skill_version(draft.id).status == "evaluated"


def test_legacy_approval_only_migrates_to_inactive_version(manager):
    session_id = manager.store.conn.execute("SELECT id FROM sessions LIMIT 1").fetchone()[0]
    manager.store.save_skill_draft(
        "legacy-skill",
        "draft",
        session_id,
        [],
        "Use `from_prototype`.",
        {"tools": ["from_prototype"], "evolution": {"source_trace_ids": [94]}},
    )

    with pytest.raises(SkillEvolutionError, match="migrated to version"):
        manager.approve("legacy-skill")

    migrated = manager.store.get_skill_version(1)
    assert migrated.status == "draft"
    assert not (manager.user_skill_root / "legacy-skill").exists()


def test_rollback_uses_current_replay_and_cannot_fabricate_pass(manager):
    first = manager.draft_skill(
        "rollback-skill", "Rollback", "First `from_prototype`.", ["from_prototype"], [86]
    )
    manager.evaluate(first.id)
    manager.approve(first.id)
    second = manager.draft_revision(
        first.id, body="Second `from_prototype`.", source_trace_ids=[87]
    )
    manager.evaluate(second.id)
    manager.approve(second.id)
    manager.replay = lambda version, context: {"passed": False}

    with pytest.raises(SkillEvolutionError, match="not approvable"):
        manager.rollback(first.id, source_trace_ids=[88])


def test_replay_context_restores_cwd_and_restricts_tools(manager):
    caller = Path.cwd()

    def replay(version, context):
        assert Path.cwd() == context.workspace.path
        assert "error" in context.execute("shell", {})
        assert context.execute("from_prototype", {}) == {"ok": True}
        return {"passed": True}

    manager.replay = replay
    draft = manager.draft_skill(
        "context-skill", "Context", "Use `from_prototype`.", ["from_prototype"], [89]
    )
    manager.evaluate(draft.id)
    assert Path.cwd() == caller


def test_replay_context_preserves_executor_structure_references(manager):
    make = FunctionDef(
        name="make_molecule",
        description="make",
        parameters={"type": "object", "properties": {}},
        callable=lambda: Molecule(["H"], [[0.0, 0.0, 0.0]]),
    )
    count = FunctionDef(
        name="count_atoms",
        description="count",
        parameters={
            "type": "object",
            "properties": {"structure": {"type": "object"}},
            "required": ["structure"],
        },
        callable=lambda structure: len(structure),
    )
    replay_manager = EvolutionManager(
        manager.store,
        user_skill_root=manager.user_skill_root,
        available_tools={"make_molecule": make, "count_atoms": count},
    )

    def replay(version, context):
        structure = context.execute("make_molecule", {})
        assert context.execute("count_atoms", {"structure": structure}) == {"result": 1}
        return {"passed": True}

    replay_manager.replay = replay
    draft = replay_manager.draft_skill(
        "reference-skill", "Reference", "Use both registered tools.",
        ["make_molecule", "count_atoms"], [96]
    )
    assert replay_manager.evaluate(draft.id).deterministic_pass is True


def test_replay_rejects_path_escape_and_symlink_artifacts(manager, tmp_path):
    def escape(version, context):
        context.artifact_path("../escape")
        return {"passed": True}

    manager.replay = escape
    draft = manager.draft_skill(
        "escape-skill", "Escape", "Use `from_prototype`.", ["from_prototype"], [90]
    )
    with pytest.raises(SkillEvolutionError, match="escapes"):
        manager.evaluate(draft.id)

    def symlink(version, context):
        (context.workspace.path / "link").symlink_to(tmp_path)
        return {"passed": True, "artifacts": ["link"]}

    manager.replay = symlink
    second = manager.draft_skill(
        "symlink-skill", "Symlink", "Use `from_prototype`.", ["from_prototype"], [91]
    )
    with pytest.raises(SkillEvolutionError, match="symlink"):
        manager.evaluate(second.id)


def test_replay_rejects_declared_missing_artifact(manager):
    manager.replay = lambda version, context: {
        "passed": True,
        "artifacts": ["missing.cif"],
    }
    draft = manager.draft_skill(
        "missing-artifact", "Artifact", "Use `from_prototype`.",
        ["from_prototype"], [95]
    )
    with pytest.raises(SkillEvolutionError, match="not a regular file"):
        manager.evaluate(draft.id)


@pytest.mark.parametrize(
    "body",
    [
        "python -m pip install bad",
        "PYTHON -m PIP   INSTALL bad",
        "Run scripts / run.sh",
        "modify MATSIMPY / core / structure.py",
        "rewrite soul.md",
    ],
)
def test_adversarial_unsafe_instruction_variants_are_rejected(manager, body):
    with pytest.raises(SkillEvolutionError):
        manager.draft_skill("adversarial", "Unsafe", body, ["from_prototype"], [92])


def test_missing_source_trace_is_rejected(manager):
    with pytest.raises(SkillEvolutionError, match="do not exist"):
        manager.draft_skill(
            "missing-trace", "Missing", "Use `from_prototype`.",
            ["from_prototype"], [9999]
        )


def test_evaluation_requires_concrete_function_definitions(manager):
    names_only = EvolutionManager(
        manager.store,
        user_skill_root=manager.user_skill_root,
        available_tools=["from_prototype"],
        replay=lambda version, context: {"passed": True},
    )
    draft = names_only.draft_skill(
        "names-only", "Names", "Use `from_prototype`.", ["from_prototype"], [97]
    )
    with pytest.raises(SkillEvolutionError, match="FunctionDef"):
        names_only.evaluate(draft.id)

    malformed = EvolutionManager(
        manager.store,
        user_skill_root=manager.user_skill_root,
        available_tools={"from_prototype": object()},
        replay=lambda version, context: {"passed": True},
    )
    second = malformed.draft_skill(
        "malformed-catalog", "Malformed", "Use `from_prototype`.",
        ["from_prototype"], [98]
    )
    with pytest.raises(SkillEvolutionError, match="FunctionDef"):
        malformed.evaluate(second.id)


def test_repl_rollback_numeric_id_runs_full_version_lifecycle(manager):
    first = manager.draft_skill(
        "repl-rollback", "Rollback", "First `from_prototype`.", ["from_prototype"], [99]
    )
    manager.evaluate(first.id)
    manager.approve(first.id)
    second = manager.draft_revision(
        first.id, body="Second `from_prototype`.", source_trace_ids=[100]
    )
    manager.evaluate(second.id)
    manager.approve(second.id)

    session = type("Session", (), {"session_store": manager.store})()
    result = ReplController(session, evolution=manager).execute(f"/rollback {first.id}")

    assert result.ok is True
    assert result.data["target_version_id"] == first.id
    active = manager.store.get_active_skill_version(first.name)
    assert active.rollback_of_version_id == first.id
    assert active.source_trace_ids == first.source_trace_ids
