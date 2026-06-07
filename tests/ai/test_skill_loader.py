"""Tests for dynamic skill discovery — basic and edge cases."""
import os
import sys
import pytest
from matsimpy.ai.skill_loader import discover_builtin_skills, SKILLS_PKG


# ── basic discovery ────────────────────────────────────────────────

def test_discover_builtin_skills_returns_all():
    skills = discover_builtin_skills()
    names = {s["name"] for s in skills}
    assert names >= {"core", "builders", "transformation", "analysis", "io", "storage"}


def test_discover_builtin_skills_has_keywords():
    skills = discover_builtin_skills()
    for s in skills:
        assert isinstance(s["keywords"], list), f"{s['name']} missing keywords"
        assert isinstance(s["functions"], list), f"{s['name']} missing functions"
        assert len(s["functions"]) > 0, f"{s['name']} has zero functions"


def test_discover_builtin_skills_no_duplicates():
    skills = discover_builtin_skills()
    names = [s["name"] for s in skills]
    assert len(names) == len(set(names)), f"Duplicate skill names: {names}"


def test_discover_builtin_skills_core_is_first():
    skills = discover_builtin_skills()
    assert skills[0]["name"] == "core", "core skill must be first"


# ── edge cases — temp skill files ───────────────────────────────────

_EDGE_SKILLS = []


def _write_temp_skill(name, content):
    """Write a temporary skill file and track it for cleanup."""
    path = SKILLS_PKG / f"{name}.py"
    path.write_text(content)
    _EDGE_SKILLS.append(path)
    # Clear any cached module so re-import works
    mod_name = f"matsimpy.ai.skills.{name}"
    sys.modules.pop(mod_name, None)
    return path


def teardown_module():
    """Clean up all temp skill files."""
    for path in _EDGE_SKILLS:
        if path.exists():
            path.unlink()
        mod_name = f"matsimpy.ai.skills.{path.stem}"
        sys.modules.pop(mod_name, None)


def test_skill_without_skill_name_is_skipped():
    """Files without SKILL_NAME are silently skipped (utility modules)."""
    _write_temp_skill("zztmp_test_util", """
UTILITY_CONSTANT = 42
""")
    skills = discover_builtin_skills()
    names = {s["name"] for s in skills}
    assert "zztmp_test_util" not in names


def test_skill_missing_description_is_skipped():
    """Skill with SKILL_NAME but no SKILL_DESCRIPTION → warned and skipped."""
    with pytest.warns(UserWarning, match="missing SKILL_DESCRIPTION"):
        _write_temp_skill("zztmp_test_no_desc", """
SKILL_NAME = "zztmp_test_no_desc"
SKILL_KEYWORDS = ["test"]
def get_functions():
    from matsimpy.ai.skill import FunctionDef
    return [FunctionDef("x", "x", {}, lambda: None)]
""")
        skills = discover_builtin_skills()
        names = {s["name"] for s in skills}
        assert "zztmp_test_no_desc" not in names


def test_skill_missing_get_functions_is_skipped():
    """Skill with SKILL_NAME but no get_functions → warned and skipped."""
    with pytest.warns(UserWarning, match="missing callable get_functions"):
        _write_temp_skill("zztmp_test_no_fn", """
SKILL_NAME = "zztmp_test_no_fn"
SKILL_DESCRIPTION = "missing get_functions"
SKILL_KEYWORDS = []
""")
        skills = discover_builtin_skills()
        names = {s["name"] for s in skills}
        assert "zztmp_test_no_fn" not in names


def test_duplicate_skill_name_is_skipped():
    """Second skill with same SKILL_NAME → warned and skipped (first wins)."""
    # First skill
    _write_temp_skill("zztmp_test_dup1", """
SKILL_NAME = "zztmp_test_dup"
SKILL_DESCRIPTION = "first"
SKILL_KEYWORDS = []
def get_functions():
    from matsimpy.ai.skill import FunctionDef
    return [FunctionDef("f1", "first", {}, lambda: None)]
""")
    # Second skill with same SKILL_NAME
    with pytest.warns(UserWarning, match="redefined.*skipping"):
        _write_temp_skill("zztmp_test_dup2", """
SKILL_NAME = "zztmp_test_dup"
SKILL_DESCRIPTION = "second (duplicate)"
SKILL_KEYWORDS = ["dup"]
def get_functions():
    from matsimpy.ai.skill import FunctionDef
    return [FunctionDef("f2", "second", {}, lambda: None)]
""")
        skills = discover_builtin_skills()
        for s in skills:
            if s["name"] == "zztmp_test_dup":
                assert s["description"] == "first"  # first module wins
                assert s["keywords"] == []           # from first module
                return
        pytest.fail("First skill should have been discovered")


def test_skill_without_keywords_defaults_to_empty():
    """Skill without SKILL_KEYWORDS → defaults to empty list."""
    _write_temp_skill("zztmp_test_nokw", """
SKILL_NAME = "zztmp_test_nokw"
SKILL_DESCRIPTION = "no keywords"
def get_functions():
    from matsimpy.ai.skill import FunctionDef
    return [FunctionDef("nokw", "no keywords", {}, lambda: None)]
""")
    skills = discover_builtin_skills()
    for s in skills:
        if s["name"] == "zztmp_test_nokw":
            assert s["keywords"] == []
            return
    pytest.fail("Skill without keywords should be discovered")


def test_discover_returns_valid_skill():
    """A completely valid temp skill should be discovered with all fields."""
    _write_temp_skill("zztmp_test_valid", """
SKILL_NAME = "zztmp_test_valid"
SKILL_DESCRIPTION = "A valid temp test skill"
SKILL_KEYWORDS = ["temp", "test", "edge"]
def get_functions():
    from matsimpy.ai.skill import FunctionDef
    return [
        FunctionDef("temp_fn1", "first function", {"type": "object", "properties": {}}, lambda: 1),
        FunctionDef("temp_fn2", "second function", {"type": "object", "properties": {}}, lambda: 2),
    ]
""")
    skills = discover_builtin_skills()
    for s in skills:
        if s["name"] == "zztmp_test_valid":
            assert s["description"] == "A valid temp test skill"
            assert s["keywords"] == ["temp", "test", "edge"]
            assert len(s["functions"]) == 2
            return
    pytest.fail("Valid temp skill should be discovered")


def test_generated_skill_status_filter(tmp_path, monkeypatch):
    from matsimpy.ai import skill_loader

    generated = tmp_path / "generated"
    generated.mkdir()
    monkeypatch.setattr(skill_loader, "SKILLS_DIR", generated)

    skill_loader.save_skill_md(
        name="approved-skill",
        description="Approved skill",
        tools=[{"function": "from_prototype"}],
        trigger_keywords=["approved"],
        body="# Approved\n",
        load_mode="auto_choice",
    )
    skill_loader.save_skill_md(
        name="draft-skill",
        description="Draft skill",
        tools=[{"function": "from_prototype"}],
        trigger_keywords=["draft"],
        body="# Draft\n",
        load_mode="manual",
        status="draft",
    )

    approved = skill_loader.list_generated_skills(status="approved")
    drafts = skill_loader.list_generated_skills(status="draft")

    assert [s["name"] for s in approved] == ["approved-skill"]
    assert [s["name"] for s in drafts] == ["draft-skill"]


def test_generated_skill_missing_status_defaults_to_approved(tmp_path, monkeypatch):
    from matsimpy.ai import skill_loader

    generated = tmp_path / "generated"
    generated.mkdir()
    monkeypatch.setattr(skill_loader, "SKILLS_DIR", generated)

    legacy_skill = generated / "legacy.skill.md"
    legacy_skill.write_text(
        "---\n"
        "name: legacy\n"
        "description: Legacy generated skill\n"
        "tools: []\n"
        "---\n\n"
        "# Legacy\n"
    )

    approved = skill_loader.list_generated_skills(status="approved")

    assert [s["name"] for s in approved] == ["legacy"]


def test_generated_skill_status_none_returns_all(tmp_path, monkeypatch):
    from matsimpy.ai import skill_loader

    generated = tmp_path / "generated"
    generated.mkdir()
    monkeypatch.setattr(skill_loader, "SKILLS_DIR", generated)

    skill_loader.save_skill_md(
        name="approved-skill",
        description="Approved skill",
        tools=[],
        trigger_keywords=[],
    )
    skill_loader.save_skill_md(
        name="draft-skill",
        description="Draft skill",
        tools=[],
        trigger_keywords=[],
        status="draft",
    )

    skills = skill_loader.list_generated_skills(status=None)

    assert [s["name"] for s in skills] == ["approved-skill", "draft-skill"]
