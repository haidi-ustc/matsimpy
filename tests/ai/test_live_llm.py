"""Live DeepSeek checks of tool selection and execution (skipped without DEEPSEEK_API_KEY).

The broader, repeated evaluation with an LLM judge is ``examples/llm``.
"""

import os

import pytest

from examples.llm.harness import build_agent
from matsimpy import io

pytestmark = [
    pytest.mark.requires_llm,
    pytest.mark.skipif(not os.getenv("DEEPSEEK_API_KEY"), reason="DEEPSEEK_API_KEY is required"),
]


@pytest.fixture
def agent(tmp_path):
    with build_agent(tmp_path) as agent:
        yield agent


def _trace(result):
    return {"response": result.response, "trace": [(c.name, c.arguments, c.result) for c in result.tool_calls]}


@pytest.mark.parametrize("prompt", [
    "Build rocksalt NaCl with lattice constant 5.64 angstrom and save it as nacl.cif",
    "make a racksalt sodium chloride crystal, a=5.64 A, then write it to nacl.cif",
])
def test_live_rocksalt_uses_prototype_and_writes_valid_cif(agent, prompt):
    result = agent.run(prompt)
    assert result.status == "success", _trace(result)
    build = next(call for call in result.tool_calls if call.name == "from_prototype")
    assert build.arguments["prototype"] == "rocksalt", _trace(result)
    assert build.result["structure_ref"].startswith("structure:")
    write = next(call for call in result.tool_calls if call.name == "write_structure")
    crystal = io.read(agent.workspace.path / write.arguments["filename"])
    assert len(crystal) == 2
    assert {str(species) for species in crystal.species} == {"Na", "Cl"}
    assert crystal.lattice.volume == pytest.approx(5.64 ** 3 / 4, rel=1e-5)


@pytest.mark.parametrize(("prompt", "required_tools"), [
    ("Create a water molecule with Cartesian positions O=(0,0,0), H=(0.96,0,0), H=(-0.24,0.93,0), "
     "then save water.xyz", {"create_molecule", "write_structure"}),
    ("Build fcc copper with a=3.61 A, translate it by [0.1,0,0] angstrom, and save translated_cu.cif",
     {"from_prototype", "translate", "write_structure"}),
    ("Create an argon dimer at Cartesian coordinates [0,0,0] and [4,0,0], then calculate its "
     "Lennard-Jones energy", {"create_molecule", "calculate_lennard_jones"}),
])
def test_live_workflows_use_expected_tools(agent, prompt, required_tools):
    result = agent.run(prompt)
    assert result.status == "success", _trace(result)
    assert required_tools <= {call.name for call in result.tool_calls}, _trace(result)


def test_live_file_analysis_uses_real_artifact(agent):
    (agent.workspace.path / "water.xyz").write_text("3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n")
    result = agent.run("Analyze the bonds in water.xyz with a 1.2 angstrom cutoff")
    assert result.status == "success", _trace(result)
    analysis = next(call for call in result.tool_calls if call.name == "analyze_bonds")
    assert analysis.result["num_bonds"] == 2


def test_live_skill_activation(agent):
    result = agent.run("Prepare VASP static-run inputs for fcc Al with a=4.05 A in the directory al_static")
    assert result.status == "success", _trace(result)
    names = [call.name for call in result.tool_calls]
    assert "activate_skill" in names and "write_vasp_input" in names, _trace(result)
    assert (agent.workspace.path / "al_static" / "INCAR").is_file()
    assert not (agent.workspace.path / "al_static" / "POTCAR").exists()
