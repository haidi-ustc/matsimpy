"""Shared execution, validation, judging, and reporting for LLM examples."""

from __future__ import annotations

import json
import os
import re
import requests
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from matsimpy import io
from matsimpy.ai.conversation import ChatMessage
from matsimpy.ai.memory import AgentMemory
from matsimpy.ai.provider import DeepSeekProvider
from matsimpy.ai.runtime import AgentRuntime
from matsimpy.ai.session import AgentSession
from matsimpy.ai.session_store import SessionStore
from matsimpy.ai.skill import Skill, SkillManager
from matsimpy.ai.skill_loader import discover_builtin_skills

from .scenarios import Scenario, get_scenario


DEFAULT_REPETITIONS = 3
ROOT = Path(__file__).resolve().parent
SECRET_KEYS = {"api_key", "authorization", "token", "password", "secret"}


def sanitize_evidence(value: Any):
    """Recursively redact credential-bearing fields before persistence/judging."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if isinstance(key, str) and key.casefold() in SECRET_KEYS
            else sanitize_evidence(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_evidence(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_evidence(item) for item in value]
    return value


@dataclass(frozen=True)
class EvaluationReport:
    scenario: str
    runs: int
    deterministic_pass_rate: float
    judge_pass_rate: float
    stable: bool

    @classmethod
    def from_runs(cls, scenario: str, runs: list[dict]) -> "EvaluationReport":
        count = len(runs)
        deterministic = sum(bool(run.get("deterministic_pass")) for run in runs)
        judged = sum(bool(run.get("judge_pass")) for run in runs)
        return cls(
            scenario=scenario,
            runs=count,
            deterministic_pass_rate=deterministic / count if count else 0.0,
            judge_pass_rate=judged / count if count else 0.0,
            stable=count > 0 and deterministic == count,
        )


def _manager() -> SkillManager:
    manager = SkillManager()
    for item in discover_builtin_skills():
        skill = Skill(item["name"], item["description"], item["functions"])
        skill.keywords = item["keywords"]
        manager.register(skill)
    manager.load("core")
    return manager


def _artifact_inventory(workspace: Path) -> list[dict]:
    structures = {".cif", ".xyz", ".vasp", ".poscar", ".json", ".pdb", ".xsf", ".mol"}
    inventory = []
    for path in sorted(workspace.iterdir()):
        if not path.is_file() or path.name in {"state.db"}:
            continue
        item = {"path": path.name, "bytes": path.stat().st_size}
        if path.suffix.casefold() in structures:
            try:
                structure = io.read(path)
                item.update(formula=structure.formula, num_atoms=len(structure), type=type(structure).__name__)
            except Exception as exc:
                item["read_error"] = f"{type(exc).__name__}: {exc}"
        inventory.append(item)
    return inventory


def _judge(provider: DeepSeekProvider, scenario: Scenario, evidence: dict) -> dict:
    payload = sanitize_evidence({
        "request": list(scenario.prompts),
        "scientific_context": scenario.scientific_context,
        "required_tools": sorted(scenario.required_tools),
        "tool_calls": evidence["tool_calls"],
        "artifacts": evidence["artifacts"],
        "deterministic_errors": evidence["deterministic_errors"],
        "final_outputs": evidence["final_outputs"],
    })
    messages = [
        ChatMessage.system(
            "You are a strict materials-workflow auditor. Judge only supplied evidence. "
            "A named prototype builder's lattice_constant is the conventional prototype "
            "parameter even when its returned cell is primitive. Return JSON with pass "
            "(boolean), score (0-100), unsupported_claims (array), and analysis (string). "
            "Deterministic errors always require pass=false."
        ),
        ChatMessage.user(json.dumps(payload, default=str)),
    ]
    for attempt in range(3):
        try:
            response = provider.chat(messages)
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt == 2:
                raise
    raw = response.message.content.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        parsed = json.loads(match.group(0) if match else raw)
    except json.JSONDecodeError:
        parsed = {"pass": False, "score": 0, "unsupported_claims": [], "analysis": raw, "parse_error": True}
    parsed["raw"] = raw
    return parsed


def _execute_prompts(session: AgentSession, prompts: tuple[str, ...]) -> tuple[list[dict], list[str]]:
    """Execute scenario prompts on one active conversation branch."""
    records: list[dict] = []
    final_outputs: list[str] = []
    for prompt in prompts:
        turn = session.run(prompt)
        assert turn.result is not None
        records.extend(turn.result.tool_calls)
        final_outputs.append(turn.result.final_response)
    return records, final_outputs


def execute_once(scenario: Scenario, run_number: int, *, judge: bool = True) -> dict:
    """Execute one isolated scenario run and persist its complete sanitized evidence."""
    scenario_dir = ROOT / f"{scenario.id}_{scenario.slug}"
    workspace = scenario_dir / "results" / "workspaces" / f"run-{run_number}"
    workspace.mkdir(parents=True, exist_ok=True)
    for child in workspace.iterdir():
        if child.is_file():
            child.unlink()

    provider = DeepSeekProvider()
    store = SessionStore(workspace / "state.db")
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=_manager(),
        session_store=store,
        memory=AgentMemory(workspace / "memory"),
        workspace_path=workspace,
        source="llm-example",
    )
    session = AgentSession(lambda: runtime, store)
    records, final_outputs = _execute_prompts(session, scenario.prompts)

    evidence = {
        "scenario": f"{scenario.id}_{scenario.slug}",
        "run": run_number,
        "model": provider.model,
        "requests": list(scenario.prompts),
        "tool_calls": records,
        "final_outputs": final_outputs,
        "artifacts": _artifact_inventory(workspace),
    }
    used = {call["name"] for call in records}
    errors = []
    missing = scenario.required_tools - used
    if missing:
        errors.append(f"missing required tools: {sorted(missing)}")
    failed = [call for call in records if call.get("status") == "failure"]
    if failed and scenario.tier != "recovery":
        errors.append(f"failed tool calls: {[call['name'] for call in failed]}")
    errors.extend(scenario.validate({**evidence, "deterministic_errors": errors}))
    evidence["deterministic_errors"] = errors
    evidence["deterministic_pass"] = not errors
    if judge:
        try:
            judgement = _judge(provider, scenario, evidence)
        except Exception as exc:
            judgement = {
                "pass": False,
                "score": 0,
                "unsupported_claims": [],
                "analysis": f"judge unavailable: {type(exc).__name__}: {exc}",
                "judge_error": True,
            }
    else:
        judgement = {"pass": not errors, "score": 100 if not errors else 0, "analysis": "judge disabled"}
    evidence["judge"] = judgement
    evidence["judge_pass"] = bool(judgement.get("pass")) and not errors

    sanitized = sanitize_evidence(evidence)
    results_dir = scenario_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"run-{run_number}.json").write_text(json.dumps(sanitized, indent=2, default=str) + "\n")
    (results_dir / "latest.json").write_text(json.dumps(sanitized, indent=2, default=str) + "\n")
    (results_dir / "latest.md").write_text(_evidence_markdown(sanitized))
    return sanitized


def _evidence_markdown(evidence: dict) -> str:
    tools = "\n".join(
        f"- `{call['name']}` — {call.get('status', 'unknown')} — args: "
        f"`{json.dumps(call.get('arguments', {}), sort_keys=True, default=str)}`"
        for call in evidence.get("tool_calls", [])
    ) or "- None"
    artifacts = "\n".join(
        f"- `{item['path']}` ({item.get('bytes', 0)} bytes, "
        f"formula={item.get('formula', 'n/a')}, atoms={item.get('num_atoms', 'n/a')})"
        for item in evidence.get("artifacts", [])
    ) or "- None"
    outputs = "\n\n".join(evidence.get("final_outputs", []))
    judge = evidence.get("judge", {})
    requests = "\n".join(f"- {prompt}" for prompt in evidence.get("requests", []))
    return (
        f"# {evidence['scenario']} — run {evidence['run']}\n\n## Requests\n\n{requests}\n\n"
        f"## Tool trace\n\n{tools}\n\n## Artifacts\n\n{artifacts}\n\n"
        f"## Final assistant output\n\n{outputs}\n\n## Deterministic validation\n\n"
        f"- Pass: {evidence.get('deterministic_pass')}\n"
        f"- Errors: {evidence.get('deterministic_errors', [])}\n\n## LLM judge\n\n"
        f"- Pass: {evidence.get('judge_pass')}\n- Score: {judge.get('score', 'n/a')}\n"
        f"- Analysis: {judge.get('analysis', '')}\n"
    )


def refresh_markdown_records() -> None:
    """Regenerate human-readable evidence from saved sanitized JSON records."""
    for path in ROOT.glob("[0-9][0-9]_*/results/latest.json"):
        path.with_suffix(".md").write_text(_evidence_markdown(json.loads(path.read_text())))


def rejudge_failures() -> int:
    """Retry only saved deterministic passes whose independent judge failed."""
    provider = DeepSeekProvider()
    retried = 0
    for scenario_dir in sorted(ROOT.glob("[0-9][0-9]_*")):
        try:
            scenario = get_scenario(scenario_dir.name)
        except KeyError:
            continue
        result_paths = sorted((scenario_dir / "results").glob("run-*.json"))
        for path in result_paths:
            evidence = json.loads(path.read_text())
            if not evidence.get("deterministic_pass") or evidence.get("judge_pass"):
                continue
            judgement = _judge(provider, scenario, evidence)
            evidence["judge"] = judgement
            evidence["judge_pass"] = bool(judgement.get("pass"))
            path.write_text(json.dumps(sanitize_evidence(evidence), indent=2, default=str) + "\n")
            retried += 1
        if result_paths:
            runs = [json.loads(path.read_text()) for path in result_paths]
            report = EvaluationReport.from_runs(scenario_dir.name, runs)
            results_dir = scenario_dir / "results"
            (results_dir / "summary.json").write_text(json.dumps(asdict(report), indent=2) + "\n")
            latest = runs[-1]
            (results_dir / "latest.json").write_text(json.dumps(latest, indent=2, default=str) + "\n")
            (results_dir / "latest.md").write_text(_evidence_markdown(latest))
    return retried


def run_scenario(identifier: str, repetitions: int = DEFAULT_REPETITIONS, *, judge: bool = True) -> EvaluationReport:
    scenario = get_scenario(identifier)
    runs = [execute_once(scenario, number, judge=judge) for number in range(1, repetitions + 1)]
    report = EvaluationReport.from_runs(f"{scenario.id}_{scenario.slug}", runs)
    results_dir = ROOT / f"{scenario.id}_{scenario.slug}" / "results"
    (results_dir / "summary.json").write_text(json.dumps(asdict(report), indent=2) + "\n")
    return report


__all__ = [
    "DEFAULT_REPETITIONS", "EvaluationReport", "execute_once", "refresh_markdown_records",
    "rejudge_failures", "run_scenario", "sanitize_evidence",
]
