"""Live DeepSeek evaluations of LLM tool selection and execution."""

import os

import pytest

from matsimpy import io
from matsimpy.ai.memory import AgentMemory
from matsimpy.ai.provider import DeepSeekProvider
from matsimpy.ai.runtime import AgentRuntime
from matsimpy.ai.session_store import SessionStore
from matsimpy.ai.skill import Skill, SkillManager
from matsimpy.ai.skill_loader import discover_builtin_skills


pytestmark = [
    pytest.mark.requires_llm,
    pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="DEEPSEEK_API_KEY is required for live LLM evaluations",
    ),
]


@pytest.fixture
def live_runtime(tmp_path):
    manager = SkillManager()
    for item in discover_builtin_skills():
        skill = Skill(item["name"], item["description"], item["functions"])
        skill.keywords = item["keywords"]
        manager.register(skill)
    manager.load("core")
    return AgentRuntime(
        provider=DeepSeekProvider(),
        skill_manager=manager,
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="live-test",
    )


@pytest.mark.parametrize("prompt", [
    "Build rocksalt NaCl with lattice constant 5.64 angstrom and save it as nacl.cif",
    "make a racksalt sodium chloride crystal, a=5.64 A, then write it to nacl.cif",
])
def test_live_rocksalt_uses_prototype_and_writes_valid_cif(live_runtime, prompt):
    result = live_runtime.run(prompt)
    trace = [(call["name"], call["arguments"], call["result"]) for call in result.tool_calls]

    assert result.status == "success", {"response": result.final_response, "trace": trace}
    build = next(call for call in result.tool_calls if call["name"] == "from_prototype")
    assert build["arguments"]["prototype"] == "rocksalt", trace
    assert build["result"]["structure_ref"].startswith("structure:"), trace
    write = next(call for call in result.tool_calls if call["name"] == "write_structure")
    crystal = io.read(live_runtime.workspace.path / write["result"]["saved_to"])
    assert len(crystal) == 2
    assert {str(species) for species in crystal.species} == {"Na", "Cl"}
    assert crystal.lattice.volume == pytest.approx(5.64 ** 3 / 4, rel=1e-5)


@pytest.mark.parametrize(("prompt", "required_tools"), [
    (
        "Create a water molecule with Cartesian positions O=(0,0,0), "
        "H=(0.96,0,0), H=(-0.24,0.93,0), then save water.xyz",
        {"create_molecule", "write_structure"},
    ),
    (
        "Build fcc copper with a=3.61 A, translate it by [0.1,0,0] angstrom, "
        "and save translated_cu.cif",
        {"from_prototype", "translate", "write_structure"},
    ),
    (
        "Create an argon dimer at Cartesian coordinates [0,0,0] and [4,0,0], "
        "then calculate its Lennard-Jones energy",
        {"create_molecule", "calculate_lennard_jones"},
    ),
])
def test_live_basic_module_workflows_use_expected_tools(live_runtime, prompt, required_tools):
    result = live_runtime.run(prompt)
    trace = [(call["name"], call["arguments"], call["result"]) for call in result.tool_calls]

    assert result.status == "success", {"response": result.final_response, "trace": trace}
    assert required_tools <= {call["name"] for call in result.tool_calls}, trace


def test_live_file_analysis_uses_real_artifact(live_runtime):
    path = live_runtime.workspace.path / "water.xyz"
    path.write_text("3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n")

    result = live_runtime.run("Analyze the bonds in water.xyz with a 1.2 angstrom cutoff")
    trace = [(call["name"], call["arguments"], call["result"]) for call in result.tool_calls]

    assert result.status == "success", {"response": result.final_response, "trace": trace}
    analysis = next(call for call in result.tool_calls if call["name"] == "analyze_bonds")
    assert analysis["result"]["num_bonds"] == 2
