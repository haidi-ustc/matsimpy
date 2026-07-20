"""Contracts for the executable live-LLM example corpus."""

import json
from pathlib import Path

import requests

from examples.llm import harness
from examples.llm.harness import DEFAULT_REPETITIONS, EvaluationReport, sanitize_evidence
from examples.llm.run_all import load_saved_reports, scenarios_needing_runs
from examples.llm.scenarios import SCENARIOS
from matsimpy.ai.conversation import ChatMessage, ChatResponse


class _TranscriptSession:
    def __init__(self):
        self.prompts = []

    def run(self, prompt):
        self.prompts.append(prompt)
        number = len(self.prompts)
        result = type("Result", (), {
            "tool_calls": [{"name": f"tool-{number}"}],
            "final_response": f"answer-{number}",
        })()
        return type("Turn", (), {"result": result})()


def test_multiturn_prompt_execution_uses_one_conversation_session():
    session = _TranscriptSession()

    records, outputs = harness._execute_prompts(session, ("build it", "transform it"))

    assert session.prompts == ["build it", "transform it"]
    assert records == [{"name": "tool-1"}, {"name": "tool-2"}]
    assert outputs == ["answer-1", "answer-2"]


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


def test_corpus_has_fifteen_unique_ordered_scenarios():
    assert len(SCENARIOS) == 15
    assert [scenario.id for scenario in SCENARIOS] == [f"{index:02d}" for index in range(1, 16)]
    assert len({scenario.name for scenario in SCENARIOS}) == 15


def test_scenarios_cover_single_pipeline_multiturn_and_recovery():
    assert {scenario.tier for scenario in SCENARIOS} == {
        "single", "pipeline", "multiturn", "recovery"
    }
    assert all(scenario.prompts for scenario in SCENARIOS)
    assert all(scenario.required_tools for scenario in SCENARIOS)
    assert all(scenario.validate is not None for scenario in SCENARIOS)


def test_each_scenario_has_a_folder_request_and_executable():
    root = Path(__file__).resolve().parents[2] / "examples" / "llm"
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
