"""Contracts for the executable live-LLM example corpus."""

import json
from pathlib import Path

import pytest
import requests

from examples.llm import harness
from examples.llm.harness import DEFAULT_REPETITIONS, EvaluationReport, sanitize_evidence
from examples.llm.run_all import load_saved_reports, scenarios_needing_runs
from examples.llm.scenarios import SCENARIOS
from matsimpy.ai.provider import ChatMessage, ChatResponse


class _TranscriptAgent:
    def __init__(self):
        self.prompts = []

    def run(self, prompt):
        from matsimpy.ai.agent import AgentResult, ToolRecord

        self.prompts.append(prompt)
        number = len(self.prompts)
        call = ToolRecord(f"tool-{number}", {}, number == 1, {"n": number})
        return AgentResult(f"answer-{number}", "success", (call,))


def test_multiturn_prompts_run_as_turns_of_one_agent():
    agent = _TranscriptAgent()

    records, outputs = harness._execute_prompts(agent, ("build it", "transform it"))

    assert agent.prompts == ["build it", "transform it"]
    assert records == [
        {"name": "tool-1", "arguments": {}, "result": {"n": 1}, "status": "success"},
        {"name": "tool-2", "arguments": {}, "result": {"n": 2}, "status": "failure"},
    ]
    assert outputs == ["answer-1", "answer-2"]


@pytest.mark.parametrize(("scenario_id", "script"), [
    ("03", [
        [("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})],
        [("write_structure", {"structure": "structure:1", "filename": "fcc_cu.cif"})],
        "Saved fcc_cu.cif.",
    ]),
    ("14", [
        [("from_prototype", {"prototype": "rocksalt", "species": ["Na", "Cl"], "lattice_constant": 5.64})],
        "Built NaCl.",
        [("search_tools", {"query": "supercell"})],
        [("make_supercell", {"crystal": "structure:1", "scaling_matrix": [2, 1, 1]})],
        [("write_structure", {"structure": "structure:2", "filename": "nacl_supercell.cif"})],
        "Saved.",
    ]),
    ("10", [
        [("create_molecule", {"species": ["O", "H", "H"],
                              "positions": [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]]})],
        [("write_structure", {"structure": "structure:1", "filename": "water.xyz"})],
        [("load_tools", {"names": ["analyze_bonds"]})],
        [("analyze_bonds", {"structure": "water.xyz", "cutoff": 1.2})],
        "Two O-H bonds.",
    ]),
])
def test_scenarios_run_end_to_end_with_a_scripted_model(tmp_path, monkeypatch, scripted, scenario_id, script):
    """The harness, agent, tools and validators together, without an API key."""
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "DeepSeekProvider", lambda: scripted(*script))
    scenario = harness.get_scenario(scenario_id)

    evidence = harness.execute_once(scenario, 1, judge=False)

    assert evidence["deterministic_errors"] == []
    assert evidence["deterministic_pass"] is True
    assert scenario.required_tools <= {call["name"] for call in evidence["tool_calls"]}
    folder = tmp_path / f"{scenario.id}_{scenario.slug}" / "results"
    assert json.loads((folder / "latest.json").read_text())["run"] == 1
    assert (folder / "latest.md").read_text().startswith(f"# {scenario.id}_{scenario.slug}")


def test_skill_scenario_end_to_end_with_a_scripted_model(tmp_path, monkeypatch, scripted):
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "DeepSeekProvider", lambda: scripted(
        [("from_prototype", {"prototype": "diamond", "species": "Si", "lattice_constant": 5.43}),
         ("activate_skill", {"name": "vasp-inputs"})],
        [("kpoint_mesh", {"structure": "structure:1", "kppa": 1000})],
        lambda messages: [("write_vasp_input", {
            "structure": "structure:1", "directory": "si_relax", "incar": {"IBRION": 2, "ISIF": 3},
            "kpoints": json.loads(messages[-1].content)["result"]})],
        "Wrote si_relax; add your own POTCAR.",
    ))
    evidence = harness.execute_once(harness.get_scenario("16"), 1, judge=False)
    assert evidence["deterministic_errors"] == []
    assert {item["path"] for item in evidence["artifacts"]} >= {"si_relax/INCAR", "si_relax/KPOINTS", "si_relax/POSCAR"}
    assert not any(item["path"].startswith(".") for item in evidence["artifacts"])


def test_mcp_scenario_end_to_end_with_a_scripted_model(tmp_path, monkeypatch, scripted):
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "DeepSeekProvider", lambda: scripted(
        [("matsimpy__from_prototype", {"prototype": "bcc", "species": "Fe", "lattice_constant": 2.87})],
        [("matsimpy__write_structure", {"structure": "structure:1", "filename": "fe.cif"})],
        "Saved fe.cif.",
    ))
    evidence = harness.execute_once(harness.get_scenario("17"), 1, judge=False)
    assert evidence["deterministic_errors"] == []
    assert evidence["tool_calls"][0]["result"]["formula"] == "Fe"


def test_scenario_validation_catches_a_wrong_result(tmp_path, monkeypatch, scripted):
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "DeepSeekProvider", lambda: scripted(
        [("from_prototype", {"prototype": "bcc", "species": "Cu", "lattice_constant": 3.61})],
        [("from_prototype", {"prototype": "bcc", "species": "Cu", "lattice_constant": 3.61})],
        [("make_supercell", {"crystal": "structure:1", "scaling_matrix": [2, 1, 1]})],
        [("write_structure", {"structure": "structure:3", "filename": "fcc_cu.cif"})],
        "Saved.",
    ))
    evidence = harness.execute_once(harness.get_scenario("03"), 1, judge=False)
    assert evidence["deterministic_errors"] == ["expected 1 atoms, got 2"]


def test_judge_retries_transport_timeout_without_rejudging_semantic_response():
    class Provider:
        def __init__(self):
            self.calls = 0

        def chat(self, messages):
            self.calls += 1
            if self.calls == 1:
                raise requests.exceptions.ReadTimeout("transient")
            return ChatResponse(
                ChatMessage.assistant(
                    '{"pass": true, "score": 100, "unsupported_claims": [], '
                    '"analysis": "grounded"}'
                ),
                [],
                "stop",
            )

    provider = Provider()
    scenario = SCENARIOS[0]
    evidence = {
        "tool_calls": [], "artifacts": [], "deterministic_errors": [],
        "final_outputs": ["done"],
    }

    judgement = harness._judge(provider, scenario, evidence)

    assert judgement["pass"] is True
    assert provider.calls == 2


def test_rejudge_failures_retries_only_saved_transport_errors(tmp_path, monkeypatch):
    results = tmp_path / "01_water_xyz" / "results"
    results.mkdir(parents=True)
    common = {
        "scenario": "01_water_xyz",
        "model": "test",
        "requests": list(SCENARIOS[0].prompts),
        "tool_calls": [],
        "artifacts": [],
        "deterministic_errors": [],
        "deterministic_pass": True,
        "judge_pass": False,
    }
    semantic = {
        **common,
        "run": 1,
        "final_outputs": ["unsupported claim"],
        "judge": {"pass": False, "score": 40, "analysis": "semantic failure"},
    }
    transport = {
        **common,
        "run": 2,
        "final_outputs": ["grounded"],
        "judge": {
            "pass": False,
            "score": 0,
            "analysis": "judge unavailable: ReadTimeout",
            "judge_error": True,
        },
    }
    semantic_path = results / "run-1.json"
    transport_path = results / "run-2.json"
    semantic_path.write_text(json.dumps(semantic, indent=2) + "\n")
    transport_path.write_text(json.dumps(transport, indent=2) + "\n")
    calls = []

    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "DeepSeekProvider", lambda: object())

    def judge(provider, scenario, evidence):
        calls.append(evidence["run"])
        return {"pass": True, "score": 100, "analysis": "available"}

    monkeypatch.setattr(harness, "_judge", judge)

    assert harness.rejudge_failures() == 1
    assert calls == [2]
    assert json.loads(semantic_path.read_text()) == semantic
    assert json.loads(transport_path.read_text())["judge_pass"] is True


def test_corpus_has_seventeen_unique_ordered_scenarios():
    assert len(SCENARIOS) == 17
    assert [scenario.id for scenario in SCENARIOS] == [f"{index:02d}" for index in range(1, 18)]
    assert len({scenario.name for scenario in SCENARIOS}) == 17


def test_scenarios_cover_every_tier():
    assert {scenario.tier for scenario in SCENARIOS} == {
        "single", "pipeline", "multiturn", "recovery", "skill", "mcp"
    }
    assert all(scenario.prompts for scenario in SCENARIOS)
    assert all(scenario.required_tools for scenario in SCENARIOS)
    assert all(scenario.validate is not None for scenario in SCENARIOS)


def test_each_scenario_has_a_folder_request_and_executable():
    root = Path(__file__).resolve().parents[2] / "examples" / "llm"
    if not any(root.glob("*/README.md")):
        pytest.skip("repository asset not available: examples/llm/*/README.md")
    for scenario in SCENARIOS:
        folder = root / f"{scenario.id}_{scenario.slug}"
        assert (folder / "README.md").is_file()
        assert (folder / "run.py").is_file()
        assert scenario.prompts[0] in (folder / "README.md").read_text()


def test_stability_default_is_three_runs():
    assert DEFAULT_REPETITIONS == 3


def test_evidence_sanitizer_removes_secrets_recursively():
    evidence = {
        "api_key": "secret",
        "Authorization": "Bearer secret",
        "trace": [{"arguments": {"token": "secret", "path": "safe.cif"}}],
    }
    sanitized = sanitize_evidence(evidence)
    rendered = json.dumps(sanitized)
    assert "secret" not in rendered
    assert "safe.cif" in rendered


def test_evidence_sanitizer_accepts_integer_mapping_keys():
    assert sanitize_evidence({"arguments": {0: "Cu"}}) == {"arguments": {0: "Cu"}}


def test_report_computes_strict_stability_rate():
    report = EvaluationReport.from_runs("demo", [
        {"deterministic_pass": True, "judge_pass": True},
        {"deterministic_pass": True, "judge_pass": False},
        {"deterministic_pass": False, "judge_pass": True},
    ])
    assert report.deterministic_pass_rate == 2 / 3
    assert report.judge_pass_rate == 2 / 3
    assert report.stable is False


def test_incremental_runner_skips_scenarios_with_stable_saved_summary(tmp_path):
    stable = SCENARIOS[0]
    pending = SCENARIOS[1]
    summary = tmp_path / f"{stable.id}_{stable.slug}" / "results" / "summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({
        "scenario": f"{stable.id}_{stable.slug}",
        "runs": 3,
        "deterministic_pass_rate": 1.0,
        "judge_pass_rate": 1.0,
        "stable": True,
    }))

    assert scenarios_needing_runs([stable, pending], root=tmp_path) == [pending]


def test_saved_reports_preserve_complete_aggregate_when_nothing_reruns(tmp_path):
    scenario = SCENARIOS[0]
    summary = tmp_path / f"{scenario.id}_{scenario.slug}" / "results" / "summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({
        "scenario": f"{scenario.id}_{scenario.slug}", "runs": 3,
        "deterministic_pass_rate": 1.0, "judge_pass_rate": 1.0, "stable": True,
    }))

    reports = load_saved_reports([scenario], root=tmp_path)
    assert [report.scenario for report in reports] == [f"{scenario.id}_{scenario.slug}"]
