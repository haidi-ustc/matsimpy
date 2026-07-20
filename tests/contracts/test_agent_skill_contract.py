"""Registry-wide contracts for packaged and standard Agent Skills."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from matsimpy.ai.agent_skills import SkillLibrary
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skill_loader import SKILLS_PKG, discover_builtin_skills


@pytest.fixture(scope="module")
def packaged_skills():
    skills = discover_builtin_skills()
    assert skills, "the installed distribution must contain Agent tool skills"
    return skills


def test_every_packaged_skill_has_stable_identity_and_contained_module(packaged_skills):
    names = [skill["name"] for skill in packaged_skills]

    assert names[0] == "core"
    assert len(names) == len(set(names))
    for skill in packaged_skills:
        module = importlib.import_module(f"matsimpy.ai.skills.{skill['name']}")
        assert Path(module.__file__).resolve().is_relative_to(SKILLS_PKG.resolve())
        assert module.SKILL_NAME == skill["name"]
        assert module.SKILL_DESCRIPTION == skill["description"]


def test_every_packaged_tool_references_its_skill_and_a_live_callable(packaged_skills):
    tool_names: list[str] = []

    for skill in packaged_skills:
        assert skill["functions"]
        for function in skill["functions"]:
            assert isinstance(function, FunctionDef)
            assert function.skill == skill["name"]
            assert callable(function.callable)
            assert function.parameters.get("type") == "object"
            tool_names.append(function.name)

    assert len(tool_names) == len(set(tool_names))


def test_standard_skill_references_are_contained_and_tools_are_intersected(tmp_path):
    root = tmp_path / "packaged"
    skill = root / "inspect-crystal"
    references = skill / "references"
    references.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: inspect-crystal\n"
        "description: Inspect a saved crystal\n"
        "allowed-tools: read_structure unknown_tool analyze_structure\n"
        "---\n"
        "Read references/workflow.md before execution.\n",
        encoding="utf-8",
    )
    (references / "workflow.md").write_text("Analyze the loaded structure.\n")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    (references / "escape.txt").symlink_to(outside)

    library = SkillLibrary(
        packaged=root,
        available_tools={"read_structure": object(), "analyze_structure": object()},
    )
    summary = library.discover()[0]

    assert summary.source == "packaged"
    assert summary.allowed_tools == ("read_structure", "analyze_structure")
    assert library.activate(summary.name).root == skill.resolve()
    assert library.read_resource(summary.name, "references/workflow.md").startswith(
        "Analyze"
    )
    with pytest.raises(ValueError, match="outside skill root"):
        library.read_resource(summary.name, "references/escape.txt")
    assert [(item.code, item.skill_name) for item in library.diagnostics] == [
        ("unknown-allowed-tool", "inspect-crystal")
    ]
