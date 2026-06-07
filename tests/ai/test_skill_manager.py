"""Tests for SkillManager dynamic keyword mapping."""
import pytest
from matsimpy.ai.skill import Skill, SkillManager, FunctionDef


def _dummy_fn():
    return None


def test_skill_has_keywords_field():
    skill = Skill("test", "A test skill", [])
    assert hasattr(skill, "keywords")
    assert skill.keywords == []


def test_skill_manager_builds_keyword_map():
    sm = SkillManager()
    fn = FunctionDef("dummy", "does nothing", {"type": "object", "properties": {}}, _dummy_fn)
    skill = Skill("builders", "Build things", [fn])
    skill.keywords = ["slab", "surface"]
    sm.register(skill)

    skill2 = Skill("analysis", "Analyze things", [fn])
    skill2.keywords = ["bond", "angle"]
    sm.register(skill2)

    # auto_load should match keywords
    loaded = sm.auto_load("create a slab surface")
    assert "builders" in loaded


def test_skill_manager_duplicate_keyword():
    sm = SkillManager()
    fn = FunctionDef("dummy", "does nothing", {"type": "object", "properties": {}}, _dummy_fn)
    skill1 = Skill("builders", "Build things", [fn])
    skill1.keywords = ["symmetry"]
    sm.register(skill1)

    skill2 = Skill("analysis", "Analyze things", [fn])
    skill2.keywords = ["symmetry"]  # duplicate
    sm.register(skill2)

    # auto_load with "symmetry" should load the last-registered skill (analysis)
    loaded = sm.auto_load("check symmetry of this crystal")
    assert "analysis" in loaded


def test_auto_load_no_keywords_loads_nothing():
    sm = SkillManager()
    fn = FunctionDef("dummy", "does nothing", {"type": "object", "properties": {}}, _dummy_fn)
    skill = Skill("core", "Core functions", [fn])
    skill.keywords = []
    sm.register(skill)
    loaded = sm.auto_load("any message here")
    assert loaded == []
