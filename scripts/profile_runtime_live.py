"""Comprehensive runtime profiling across diverse MatSimPy workflows.

Runs N distinct examples exercising different skills, tools, and code paths.
Collects per-phase timing for every turn. Each example has a time limit.
No hardcoded tool names — uses the real SkillManager.

Usage: conda run -n pmg python scripts/profile_runtime_live.py
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

from matsimpy.ai.engine import AIEngine


# ── Instrumentation ────────────────────────────────────────────────────────

class TimingCollector:
    def __init__(self):
        self.records: dict[str, list[tuple[int, int, float]]] = {}
        self.example_names: list[str] = []
        self._current_example = -1
        self._current_turn = -1

    def begin_example(self, name: str) -> None:
        self._current_example += 1
        self._current_turn = -1
        self.example_names.append(name)

    def begin_turn(self) -> None:
        self._current_turn += 1

    def add(self, phase: str, elapsed_s: float) -> None:
        self.records.setdefault(phase, []).append(
            (self._current_example, self._current_turn, elapsed_s)
        )


COLLECTOR = TimingCollector()


def wrap_method(obj, method_name: str, phase_name: str):
    original = getattr(obj, method_name)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            COLLECTOR.add(phase_name, time.perf_counter() - t0)
    setattr(obj, method_name, wrapper)


def instrument(engine: AIEngine, max_retries: int = 2) -> None:
    """Wrap runtime methods to collect timing. LLM calls retry up to max_retries times."""
    rt = engine.runtime
    wrap_method(rt.session_store, "start_session",       "db.start_session")
    wrap_method(rt.session_store, "end_session",          "db.end_session")
    wrap_method(rt.session_store, "add_messages_batch",   "db.add_messages_batch")
    wrap_method(rt.session_store, "add_tool_calls_batch", "db.add_tool_calls_batch")
    wrap_method(rt, "_compact_memory_context",            "memory.compact")
    wrap_method(rt, "_try_draft_skill_from_trace",        "evolution.draft")
    wrap_method(rt.skill_manager, "auto_load",            "skill.auto_load")

    original_chat = rt.provider.chat
    def timed_chat(*args, **kwargs):
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                t0 = time.perf_counter()
                result = original_chat(*args, **kwargs)
                COLLECTOR.add("provider.chat (LLM API)", time.perf_counter() - t0)
                if attempt > 0:
                    print(f"     (LLM call succeeded on retry {attempt})", flush=True)
                return result
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"     LLM attempt {attempt+1} failed ({exc}), retrying in {wait}s...", flush=True)
                    time.sleep(wait)
        raise last_exc
    rt.provider.chat = timed_chat

    original_run = rt.run
    def timed_run(*args, **kwargs):
        COLLECTOR.begin_turn()
        t0 = time.perf_counter()
        result = original_run(*args, **kwargs)
        COLLECTOR.add("runtime.run (total)", time.perf_counter() - t0)
        return result
    rt.run = timed_run


# ── Examples — diverse skills / code paths ──────────────────────────────────

EXAMPLES = [
    ("fcc-Cu-create-save",
     ["create an fcc Cu crystal with lattice constant 3.615", "save it as cu.vasp"]),

    ("random-SiO2-save-CIF",
     ["build a random SiO2 crystal", "save to sio2.cif"]),

    ("bcc-Fe-supercell",
     ["create a bcc Fe crystal", "make a 2x2x2 supercell of it", "save to fe_sc.vasp"]),

    ("NaCl-substitute",
     ["build a rocksalt NaCl crystal", "substitute all Na with K", "save to kcl.vasp"]),

    ("H2O-molecule-XYZ",
     ["build a water molecule", "save to h2o.xyz"]),

    ("fcc-Al-strain",
     ["create fcc Al with lattice constant 4.05", "apply 5 percent tensile strain along x", "save to al_strained.vasp"]),

    ("hcp-Mg",
     ["create an hcp Mg crystal with a=3.21 and c=5.21", "save to mg.vasp"]),

    ("diamond-slab",
     ["create a diamond carbon structure", "save to diamond.vasp"]),

    ("CsCl-save-CIF",
     ["build a CsCl structure", "save to cscl.cif"]),

    ("multi-format-NaCl",
     ["build a rocksalt NaCl crystal", "save it as nacl.vasp", "also save as nacl.cif"]),
]


# ── Reporting ───────────────────────────────────────────────────────────────

def report():
    print()
    print("=" * 80)
    print(f"COMPREHENSIVE REAL LLM PROFILING — {len(COLLECTOR.example_names)} examples")
    print("=" * 80)

    categories = [
        ("LLM API",        lambda p: "provider.chat" in p),
        ("Database",       lambda p: p.startswith("db.")),
        ("Memory",         lambda p: "memory" in p),
        ("Evolution",      lambda p: "evolution" in p),
        ("Skill",          lambda p: "skill" in p),
    ]

    all_total = sum(elapsed for _, _, elapsed in COLLECTOR.records.get("runtime.run (total)", []))
    if all_total == 0:
        all_total = 1

    print(f"\n{'Phase':<35} {'Calls':>6} {'Total (s)':>10} {'Avg (ms)':>10} {'Min (ms)':>10} {'Max (ms)':>10} {'%':>8}")
    print("-" * 80)

    for cat_name, cat_pred in categories:
        cat_total = 0.0
        for phase, times in sorted(COLLECTOR.records.items()):
            if cat_pred(phase):
                vals = [elapsed for _, _, elapsed in times]
                total_s = sum(vals)
                cat_total += total_s
                avg_ms = statistics.mean(vals) * 1000
                min_ms = min(vals) * 1000 if vals else 0
                max_ms = max(vals) * 1000 if vals else 0
                pct = total_s / all_total * 100
                print(f"  {phase:<33} {len(vals):>6} {total_s:>10.3f} {avg_ms:>10.2f} {min_ms:>10.2f} {max_ms:>10.2f} {pct:>7.1f}%")
        if cat_total > 0:
            cat_pct = cat_total / all_total * 100
            print(f"  {'├─ ' + cat_name + ' subtotal':<33} {'':>6} {cat_total:>10.3f} {'':>10} {'':>10} {'':>10} {cat_pct:>7.1f}%")
        print()

    print("-" * 80)
    print(f"  {'TOTAL (all examples)':<33} {'':>6} {all_total:>10.3f} {'':>10} {'':>10} {'':>10} {'100.0%':>7}")
    print()

    print("=" * 80)
    print("PER-EXAMPLE BREAKDOWN")
    print("=" * 80)
    print(f"{'#':>3} {'Example':<35} {'Turns':>6} {'Total (s)':>10} {'LLM (s)':>10} {'Ours (ms)':>10} {'Status':>10}")
    print("-" * 80)
    for ex_idx, name in enumerate(COLLECTOR.example_names):
        ex_llm = sum(elapsed for phase, times in COLLECTOR.records.items()
                     for ei, _, elapsed in times
                     if "provider.chat" in phase and ei == ex_idx)
        ex_our = sum(elapsed for phase, times in COLLECTOR.records.items()
                     for ei, _, elapsed in times
                     if "provider.chat" not in phase and "runtime.run" not in phase
                     and ei == ex_idx)
        ex_total = sum(elapsed for phase, times in COLLECTOR.records.items()
                      for ei, _, elapsed in times
                      if "runtime.run" in phase and ei == ex_idx)
        has_data = ex_total > 0
        n_turns = 0
        for phase, times in COLLECTOR.records.items():
            for ei, ti, _ in times:
                if ei == ex_idx:
                    n_turns = max(n_turns, ti + 1)
        status = "✓" if has_data else "TIMEOUT/SKIP"
        print(f"{ex_idx:>3} {name:<35} {n_turns:>6} {ex_total:>10.1f} {ex_llm:>10.1f} {ex_our*1000:>10.2f} {status:>10}")


def main():
    MAX_RETRIES = 2
    engine = AIEngine()
    instrument(engine, max_retries=MAX_RETRIES)

    for name, prompts in EXAMPLES:
        print(f"\n▶ {name}  ({len(prompts)} turns, max_retries={MAX_RETRIES})", flush=True)
        COLLECTOR.begin_example(name)

        for prompt in prompts:
            print(f"  [{name}] user: {prompt[:80]}...", flush=True)
            try:
                result = engine.chat(prompt)
                display = result.replace("\n", " ")[:120]
                print(f"  [{name}]  → {display}", flush=True)
            except Exception as exc:
                print(f"  [{name}]  ✗ FAILED after {MAX_RETRIES} retries: {exc}", flush=True)

        engine.conversation = engine.conversation[:1]

    report()


if __name__ == "__main__":
    main()
