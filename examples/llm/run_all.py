"""Run the complete live-LLM stability corpus."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from examples.llm.harness import (
    DEFAULT_REPETITIONS,
    EvaluationReport,
    refresh_markdown_records,
    rejudge_failures,
    run_scenario,
)
from examples.llm.scenarios import SCENARIOS


def _execute_scenario(identifier: str, repetitions: int, no_judge: bool):
    return run_scenario(identifier, repetitions, judge=not no_judge)


def scenarios_needing_runs(scenarios, *, root: Path | None = None, repetitions: int = DEFAULT_REPETITIONS):
    """Return scenarios without a complete, passing saved stability result."""
    root = root or Path(__file__).resolve().parent
    pending = []
    for scenario in scenarios:
        summary = root / f"{scenario.id}_{scenario.slug}" / "results" / "summary.json"
        try:
            report = EvaluationReport(**json.loads(summary.read_text()))
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            pending.append(scenario)
            continue
        if report.runs < repetitions or not report.stable or report.judge_pass_rate < 1.0:
            pending.append(scenario)
    return pending


def load_saved_reports(scenarios, *, root: Path | None = None) -> list[EvaluationReport]:
    """Load existing summaries without invoking either workflow or judge LLMs."""
    root = root or Path(__file__).resolve().parent
    reports = []
    for scenario in scenarios:
        summary = root / f"{scenario.id}_{scenario.slug}" / "results" / "summary.json"
        if not summary.exists():
            raise FileNotFoundError(summary)
        reports.append(EvaluationReport(**json.loads(summary.read_text())))
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--scenario", action="append", help="Scenario id or slug; repeat to select several")
    parser.add_argument("--workers", type=int, default=1, help="Independent scenarios to run concurrently")
    parser.add_argument("--run-all", action="store_true", help="Force all scenarios to rerun")
    parser.add_argument("--aggregate-only", action="store_true", help="Rebuild reports from saved summaries")
    parser.add_argument("--rejudge-failures", action="store_true", help="Retry judges without rerunning workflows")
    args = parser.parse_args()
    selected = SCENARIOS
    if args.scenario:
        wanted = set(args.scenario)
        selected = [
            scenario for scenario in SCENARIOS
            if scenario.id in wanted or scenario.slug in wanted or f"{scenario.id}_{scenario.slug}" in wanted
        ]
        if len(selected) != len(wanted):
            parser.error("one or more --scenario values are unknown")
    elif not args.run_all and not args.aggregate_only and not args.rejudge_failures:
        selected = scenarios_needing_runs(selected, repetitions=args.repetitions)
        print(f"incremental run: {len(selected)} scenario(s) need execution", flush=True)
    def execute(scenario):
        print(f"[{scenario.id}/15] {scenario.name}", flush=True)
        report = _execute_scenario(scenario.id, args.repetitions, args.no_judge)
        print(
            f"  deterministic={report.deterministic_pass_rate:.0%} "
            f"judge={report.judge_pass_rate:.0%} stable={report.stable}",
            flush=True,
        )
        return report

    if args.rejudge_failures:
        print(f"retried {rejudge_failures()} saved judge failures", flush=True)
        args.aggregate_only = True
    if args.aggregate_only:
        try:
            reports = load_saved_reports(SCENARIOS)
        except FileNotFoundError as exc:
            parser.error(f"missing saved summary: {exc.filename}")
        refresh_markdown_records()
    elif args.workers == 1:
        reports = [execute(scenario) for scenario in selected]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(_execute_scenario, scenario.id, args.repetitions, args.no_judge): scenario
                for scenario in selected
            }
            reports = []
            for future in as_completed(futures):
                scenario = futures[future]
                report = future.result()
                reports.append(report)
                print(
                    f"[{scenario.id}/15] deterministic={report.deterministic_pass_rate:.0%} "
                    f"judge={report.judge_pass_rate:.0%} stable={report.stable}",
                    flush=True,
                )
        reports.sort(key=lambda report: report.scenario)
    if not args.scenario and not args.run_all and not args.aggregate_only:
        reports = load_saved_reports(SCENARIOS)
    payload = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "repetitions": args.repetitions,
        "stable_scenarios": sum(report.stable for report in reports),
        "total_scenarios": len(reports),
        "reports": [asdict(report) for report in reports],
    }
    output = Path(__file__).resolve().parent / "stability-report.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0 if all(report.stable for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
