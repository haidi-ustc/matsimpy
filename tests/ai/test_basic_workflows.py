"""Real cross-skill workflows through the LLM execution boundary."""

import pytest

from matsimpy import io
from matsimpy.ai.conversation import ToolCall
from matsimpy.ai.executor import FunctionExecutor
from matsimpy.ai.skill import Skill, SkillManager
from matsimpy.ai.skill_loader import discover_builtin_skills


def _executor(*skill_names):
    manager = SkillManager()
    discovered = {item["name"]: item for item in discover_builtin_skills()}
    for name in skill_names:
        item = discovered[name]
        skill = Skill(name, item["description"], item["functions"])
        manager.register(skill)
        manager.load(name)
    return FunctionExecutor(manager)


def _call(executor, name, **arguments):
    return executor.execute(ToolCall(id=name, name=name, arguments=arguments))


def test_named_prototype_can_be_saved_and_read_back(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executor = _executor("builders", "io")

    built = _call(
        executor,
        "from_prototype",
        prototype="rocksalt",
        species=["Na", "Cl"],
        lattice_constant=5.64,
    )
    saved = _call(executor, "write_structure", path="nacl.cif", structure=built, format="cif")
    reread = _call(executor, "read_structure", path="nacl.cif", format="cif")

    assert built["structure_ref"] == "structure:1"
    assert saved["saved_to"] == "nacl.cif"
    assert reread["structure_ref"] == "structure:2"
    crystal = io.read(tmp_path / "nacl.cif")
    assert len(crystal) == 2
    assert {str(species) for species in crystal.species} == {"Na", "Cl"}
    assert crystal.lattice.volume == pytest.approx(5.64 ** 3 / 4, rel=1e-5)


def test_read_structure_can_feed_a_transformation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executor = _executor("builders", "io", "transformation")
    built = _call(
        executor,
        "from_prototype",
        prototype="fcc",
        species="Cu",
        lattice_constant=3.61,
    )
    _call(executor, "write_structure", path="cu.cif", structure=built, format="cif")

    reread = _call(executor, "read_structure", path="cu.cif", format="cif")
    translated = _call(executor, "translate", structure=reread, vector=[0.1, 0.0, 0.0])

    assert reread["structure_ref"] == "structure:2"
    assert translated["structure_ref"] == "structure:3"
