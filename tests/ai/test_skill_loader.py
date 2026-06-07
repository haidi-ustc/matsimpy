"""Tests for dynamic skill discovery."""
import pytest
from matsimpy.ai.skill_loader import discover_builtin_skills


def test_discover_builtin_skills_returns_all():
    skills = discover_builtin_skills()
    names = {s["name"] for s in skills}
    # All 6 builtin skills must be discovered
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
