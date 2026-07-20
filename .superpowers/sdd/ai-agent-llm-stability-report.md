# AI agent live-LLM stability diagnosis

## Outcome

The live corpus failures have three semantic/harness causes and one independent
transport cause. The fix preserves all existing request/result artifacts and does
not persist provider credentials.

## Root-cause evidence

- Scenario 14 run 3 is an agent/harness defect. The first prompt returned
  `structure:1`. The second prompt was executed by a fresh direct
  `AgentRuntime.run()` call with no prior messages, so the model first called
  `make_supercell` without `crystal`, then guessed `nacl.cif`, then rebuilt NaCl.
  `AgentSession` already persists the full user/assistant/tool transcript and the
  runtime executor already retains the referenced object. The harness bypassed
  that coordinator.
- Scenario 11 run 3 completed deterministically. Its judge only flagged final
  commentary that supplied default LJ parameters and derived the equilibrium
  distance/physical interpretation although those facts were not in the request
  or returned tool result. This is an agent grounding issue, not a calculation
  failure.
- Scenario 13 run 3 completed every required tool successfully. The builder
  accepted `lattice_constant=4.05` as the conventional FCC parameter and returned
  the expected one-atom primitive rhombohedral cell (`a=2.8638` Angstrom). The
  judge treated the returned primitive vector length as a rejected conventional
  input because the property-level tool schema described only a generic lattice
  constant. This is an evidence-description/judge ambiguity, not a builder defect.
- Scenario 12 runs 1-3 all passed deterministic execution; all judge failures are
  `Read timed out` transport errors. The harness had reduced the provider timeout
  from its normal 120 seconds to 45 seconds and performed no retry. No scenario 12
  agent behavior is implicated by these records.

## Changes

- Execute all prompts in a live scenario through one `AgentSession`, retaining
  prior tool messages and reusable `structure_ref` values across turns.
- Direct the runtime to reuse prior structure references, avoid guessed paths or
  redundant rebuilds, and omit unrequested derived/default scientific claims.
- Describe prototype `lattice_constant` explicitly as the conventional prototype
  parameter whose returned primitive vectors may have different lengths; repeat
  this invariant in judge instructions.
- Restore the provider's normal request timeout and retry judge calls at most
  three times, only for requests timeout/connection exceptions. Parsed semantic
  judgments, including failures, are never retried or hidden.

## TDD evidence and verification

Tests were added before production changes and observed failing for the missing
session helper, absent prompt rules, ambiguous schema, and lack of transport retry.

Exact focused verification:

```text
pytest tests/ai/test_llm_examples.py tests/ai/test_runtime.py::test_runtime_prompt_forbids_invented_scientific_tool_arguments tests/ai/test_catalog.py::test_prototype_schema_matches_supported_domain_inputs tests/ai/test_agent_session.py -q
23 passed in 2.25s
```

The full live corpus was intentionally not rerun; the controller will rerun only
failed scenarios/judges.

## Review follow-up: saved semantic judgments

Review identified that the controller-level `rejudge_failures()` selector still
included every deterministic run with `judge_pass=false`. That could overwrite a
valid parsed semantic failure even though the in-call retry loop itself was
transport-only.

The selector now requires the persisted `judge.judge_error` unavailable marker in
addition to deterministic success and failed judge status. Parsed semantic
`pass=false` judgments are left byte-for-byte unchanged. Aggregate summary/latest
refresh and the returned retry count retain their existing behavior for the
records actually retried.

The regression was run RED first with one semantic failure and one unavailable
judge record: the old implementation called both and returned `2`. After the fix:

```text
pytest tests/ai/test_llm_examples.py -q
12 passed in 0.52s
```

## Live follow-up: setting-specific symmetry evidence

A targeted scenario 12 rerun exposed a separate grounding defect. The
`analyze_symmetry` result reported Wyckoff letter `b` with multiplicity `2` for
the analyzed primitive input cell, but the final response replaced it with the
prior-knowledge conventional label `8a/a`. The underlying symmetry calculation
was correct; the unsupported setting conversion occurred only in model prose.

The runtime now requires exact reproduction of returned Wyckoff letters and
multiplicities in the reported setting and forbids conversion to a conventional
setting unless a tool explicitly returns that mapping. The symmetry tool result
also includes a concise `wyckoff_setting_note` reinforcing that contract while
leaving all calculated fields unchanged.

Both new contracts were observed RED before implementation (`wyckoff` prompt
rule absent and `wyckoff_setting_note` missing). Focused verification after the
fix:

```text
pytest tests/ai/test_runtime.py::test_runtime_prompt_forbids_invented_scientific_tool_arguments tests/ai/test_agent_skills.py::test_symmetry_result_marks_wyckoff_values_as_setting_specific tests/ai/test_skill_loader.py::test_discover_builtin_skills_includes_ai_coverage_expansion tests/symmetry/test_symmetry.py -q
26 passed in 1.35s
```
