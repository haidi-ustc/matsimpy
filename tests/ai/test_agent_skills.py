"""Tests for parsing standard Agent Skills directories."""

from pathlib import Path
from types import MappingProxyType

import pytest

from matsimpy.ai.agent_skills import (
    MAX_SKILL_BYTES,
    SkillLibrary,
    SkillValidationError,
    parse_skill,
)


def write_skill(tmp_path: Path, *, name: str) -> Path:
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A test skill\n---\nBody.\n",
        encoding="utf-8",
    )
    return root


def test_parse_standard_skill(tmp_path):
    root = tmp_path / "rocksalt-workflow"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: rocksalt-workflow\ndescription: Build named rocksalt structures\n---\nUse from_prototype.\n"
    )
    skill = parse_skill(root)
    assert skill.name == "rocksalt-workflow"
    assert skill.body == "Use from_prototype."


def test_skill_name_must_match_resolved_directory_name(tmp_path):
    root = tmp_path / "directory-name"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: manifest-name\ndescription: Mismatch\n---\nBody.\n"
    )

    with pytest.raises(SkillValidationError, match="directory name"):
        parse_skill(root)


def test_skill_name_matches_resolved_symlinked_directory(tmp_path):
    root = tmp_path / "resolved-name"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: resolved-name\ndescription: Match\n---\nBody.\n"
    )
    alias = tmp_path / "alias-name"
    alias.symlink_to(root, target_is_directory=True)

    assert parse_skill(alias).name == "resolved-name"


@pytest.mark.parametrize("name", ["Bad Name", "-bad", "bad-", "x" * 65])
def test_reject_invalid_standard_name(tmp_path, name):
    root = write_skill(tmp_path, name=name)
    with pytest.raises(SkillValidationError):
        parse_skill(root)


def test_reject_skill_file_symlink_that_escapes_root(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("---\nname: safe\ndescription: Unsafe path\n---\nBody.\n")
    root = tmp_path / "safe"
    root.mkdir()
    (root / "SKILL.md").symlink_to(outside)

    with pytest.raises(SkillValidationError, match="outside skill root"):
        parse_skill(root)


def test_reject_non_mapping_metadata(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: skill\ndescription: Safe skill\nmetadata:\n  - invalid\n---\nBody.\n"
    )

    with pytest.raises(SkillValidationError, match="metadata.*mapping"):
        parse_skill(root)


@pytest.mark.parametrize("frontmatter", ["description: Missing name", "name: missing-description"])
def test_reject_missing_required_fields(tmp_path, frontmatter):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text(f"---\n{frontmatter}\n---\nBody.\n")

    with pytest.raises(SkillValidationError, match="required"):
        parse_skill(root)


def test_reject_duplicate_yaml_documents(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: safe\ndescription: First document\n---\n"
        "---\nname: second-document\n---\nBody.\n"
    )

    with pytest.raises(SkillValidationError, match="multiple YAML documents"):
        parse_skill(root)


def test_reject_oversized_skill_file(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_bytes(b"x" * (MAX_SKILL_BYTES + 1))

    with pytest.raises(SkillValidationError, match="size limit"):
        parse_skill(root)


def test_size_limit_is_enforced_from_bytes_read_not_prior_stat(tmp_path, monkeypatch):
    root = tmp_path / "skill"
    root.mkdir()
    skill_path = root / "SKILL.md"
    skill_path.write_bytes(b"x" * (MAX_SKILL_BYTES + 1))
    real_stat = Path.stat

    def misleading_stat(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if path.name == "SKILL.md":
            return type("Stat", (), {"st_size": 0})()
        return result

    monkeypatch.setattr(Path, "stat", misleading_stat)

    with pytest.raises(SkillValidationError, match="size limit"):
        parse_skill(root)


def test_parse_optional_standard_fields(tmp_path):
    root = tmp_path / "safe-skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\n"
        "name: safe-skill\n"
        "description: Safe skill\n"
        "compatibility: Requires MatSimPy\n"
        "allowed-tools: Read Bash\n"
        "metadata:\n  owner: matsimpy\n"
        "---\nBody.\n"
    )

    skill = parse_skill(root)

    assert skill.compatibility == "Requires MatSimPy"
    assert skill.allowed_tools == "Read Bash"
    assert skill.metadata == {"owner": "matsimpy"}
    assert isinstance(skill.metadata, MappingProxyType)
    assert skill.root == root.resolve()

    with pytest.raises(TypeError):
        skill.metadata["owner"] = "changed"


def test_draft_migrated_skill_is_not_discoverable_or_activatable(tmp_path):
    from matsimpy.ai.skill_loader import migrate_legacy_skill

    root = tmp_path / "workspace"
    legacy = tmp_path / "draft-skill.skill.md"
    legacy.write_text(
        "---\n"
        "name: draft-skill\n"
        "description: Draft generated skill\n"
        "status: draft\n"
        "---\nSecret draft instructions.\n"
    )
    migrate_legacy_skill(legacy, root)
    library = SkillLibrary(workspace=root)

    assert library.discover() == []
    assert [(item.code, item.skill_name) for item in library.diagnostics] == [
        ("skill-not-approved", "draft-skill")
    ]
    with pytest.raises(KeyError, match="unknown skill"):
        library.activate("draft-skill")


def test_migrated_skill_without_status_retains_legacy_approved_default(tmp_path):
    root = tmp_path / "workspace"
    skill = root / "legacy-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: legacy-skill\n"
        "description: Legacy generated skill\n"
        "metadata:\n"
        "  matsimpy:\n"
        "    load_mode: manual\n"
        "---\nInstructions.\n"
    )
    library = SkillLibrary(workspace=root)

    assert [item.name for item in library.discover()] == ["legacy-skill"]
    assert library.activate("legacy-skill").body == "Instructions."
