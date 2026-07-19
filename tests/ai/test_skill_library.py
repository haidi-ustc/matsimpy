"""Tests for progressive discovery and activation of Agent Skills."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from matsimpy.ai.agent_skills import MAX_SKILL_BYTES, SkillLibrary, SkillValidationError


def _write_skill(
    root: Path,
    name: str,
    *,
    description: str,
    body: str,
    allowed_tools: str | None = None,
) -> Path:
    skill = root / name
    skill.mkdir(parents=True)
    tools = f"allowed-tools: {allowed_tools}\n" if allowed_tools else ""
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n{tools}---\n{body}\n",
        encoding="utf-8",
    )
    return skill


@pytest.fixture
def skill_roots(tmp_path):
    roots = SimpleNamespace(
        pkg=tmp_path / "packaged",
        user=tmp_path / "user",
        workspace=tmp_path / "workspace",
    )
    for root in vars(roots).values():
        root.mkdir()
    _write_skill(
        roots.pkg,
        "build-rocksalt",
        description="Packaged summary",
        body="Packaged full instructions.",
    )
    _write_skill(
        roots.user,
        "build-rocksalt",
        description="User summary",
        body="User full instructions.",
    )
    _write_skill(
        roots.workspace,
        "build-rocksalt",
        description="Build a rocksalt crystal",
        body="Call from_prototype to build it.",
    )
    return roots


def test_workspace_skill_overrides_user_skill_with_diagnostic(skill_roots):
    library = SkillLibrary(
        packaged=skill_roots.pkg,
        user=skill_roots.user,
        workspace=skill_roots.workspace,
    )

    summaries = library.discover()

    chosen = next(item for item in summaries if item.name == "build-rocksalt")
    assert chosen.source == "workspace"
    assert library.diagnostics[0].code == "skill-shadowed"
    assert "full instructions" not in chosen.description


def test_activation_loads_body_but_not_references(skill_roots):
    library = SkillLibrary(
        packaged=skill_roots.pkg,
        user=skill_roots.user,
        workspace=skill_roots.workspace,
    )

    active = library.activate("build-rocksalt")

    assert "from_prototype" in active.body
    assert library.loaded_resources == []


def test_activation_checks_the_single_full_manifest_it_returns(
    skill_roots, monkeypatch
):
    from matsimpy.ai import agent_skills

    library = SkillLibrary(workspace=skill_roots.workspace)
    library.discover()
    real_parse = agent_skills.parse_skill
    parse_calls = []

    def parse_once(path):
        parse_calls.append(path)
        return real_parse(path)

    def stale_summary_read(path):
        raise AssertionError("activation must not perform a separate status read")

    monkeypatch.setattr(agent_skills, "parse_skill", parse_once)
    monkeypatch.setattr(agent_skills, "_parse_skill_summary", stale_summary_read)

    active = library.activate("build-rocksalt")

    assert active is library.activated["build-rocksalt"]
    assert len(parse_calls) == 1


def test_search_uses_summary_metadata_without_activating(skill_roots):
    library = SkillLibrary(
        packaged=skill_roots.pkg,
        user=skill_roots.user,
        workspace=skill_roots.workspace,
    )

    assert [item.name for item in library.search("ROCKSALT crystal")] == [
        "build-rocksalt"
    ]
    assert library.activated == {}


def test_same_level_duplicate_names_are_rejected(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    original = _write_skill(
        packaged,
        "duplicated",
        description="A duplicate",
        body="Instructions.",
    )
    (packaged / "alias").symlink_to(original, target_is_directory=True)

    with pytest.raises(SkillValidationError, match="duplicate.*packaged"):
        SkillLibrary(packaged=packaged).discover()


def test_resource_reads_are_explicit_and_contained(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    skill = _write_skill(
        packaged,
        "documented",
        description="A documented skill",
        body="Read references explicitly.",
    )
    references = skill / "references"
    references.mkdir()
    (references / "guide.md").write_text("Trusted only after reading.", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    library = SkillLibrary(packaged=packaged)

    library.discover()
    assert library.loaded_resources == []
    assert library.read_resource("documented", "references/guide.md") == (
        "Trusted only after reading."
    )
    assert library.loaded_resources == [("documented", "references/guide.md")]
    with pytest.raises(ValueError, match="outside skill root"):
        library.read_resource("documented", "../secret.txt")


def test_resource_read_rechecks_approval_after_discovery(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    skill = _write_skill(
        packaged,
        "documented",
        description="A documented skill",
        body="Read references explicitly.",
    )
    resource = skill / "guide.md"
    resource.write_text("Draft-only details.", encoding="utf-8")
    library = SkillLibrary(packaged=packaged)
    library.discover()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: documented\n"
        "description: A documented skill\n"
        "metadata:\n"
        "  matsimpy:\n"
        "    status: draft\n"
        "---\nRead references explicitly.\n",
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match="unknown skill"):
        library.read_resource("documented", "guide.md")

    assert library.loaded_resources == []


def test_resource_symlink_cannot_escape_skill_root(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    skill = _write_skill(
        packaged,
        "documented",
        description="A documented skill",
        body="Read references explicitly.",
    )
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    (skill / "escaped.txt").symlink_to(secret)
    library = SkillLibrary(packaged=packaged)

    with pytest.raises(ValueError, match="outside skill root"):
        library.read_resource("documented", "escaped.txt")


def test_allowed_tools_only_restrict_known_capabilities(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    _write_skill(
        packaged,
        "restricted",
        description="Restrict available capabilities",
        body="Do not execute this text.",
        allowed_tools="Read InventedTool",
    )
    library = SkillLibrary(packaged=packaged, available_tools={"Read": object()})

    summary = library.discover()[0]

    assert summary.allowed_tools == ("Read",)
    assert set(library.available_tools) == {"Read"}
    assert any(item.code == "unknown-allowed-tool" for item in library.diagnostics)


def test_allowed_tools_default_to_no_capabilities(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    _write_skill(
        packaged,
        "restricted",
        description="Cannot add capabilities",
        body="Instructions.",
        allowed_tools="Read Bash",
    )
    library = SkillLibrary(packaged=packaged)

    summary = library.discover()[0]

    assert summary.allowed_tools == ()
    assert [item.code for item in library.diagnostics] == [
        "unknown-allowed-tool",
        "unknown-allowed-tool",
    ]
    assert "Read" not in library.available_tools
    assert "Bash" not in library.available_tools


@pytest.mark.parametrize(
    ("body", "activation_error"),
    [
        (b"x" * MAX_SKILL_BYTES, "size limit"),
        (b"invalid: \xff", "valid UTF-8"),
    ],
    ids=["oversized-body", "invalid-utf8-body"],
)
def test_discovery_reads_only_frontmatter(body, activation_error, tmp_path):
    packaged = tmp_path / "packaged"
    skill = packaged / "metadata-only"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_bytes(
        b"---\nname: metadata-only\ndescription: Safe summary\n---\n" + body
    )
    library = SkillLibrary(packaged=packaged)

    assert library.discover()[0].description == "Safe summary"

    with pytest.raises(SkillValidationError, match=activation_error):
        library.activate("metadata-only")
