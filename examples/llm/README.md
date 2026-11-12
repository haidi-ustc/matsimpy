# Live LLM integration tests

Seventeen scenarios run the real agent against a real model (DeepSeek) and check the
results twice: **deterministically** (required tools were called, files exist with the
right number of atoms, tool results have the right values) and with an **LLM judge**
that compares the final answer with the tool evidence.

| Tier | Scenarios | Exercises |
|---|---|---|
| single, pipeline | 01–13 | tool choice and chaining of structure references |
| multiturn | 14 | a session spanning two user turns |
| recovery | 15 | a failing call followed by recovery |
| skill | 16 | activating the packaged `vasp-inputs` Skill and using its `kpoint_mesh` tool |
| mcp | 17 | tools served by MatSimPy's own MCP server (`matsimpy__*`) |

Each run uses a fresh workspace, packaged Skills only, no user MCP configuration and no
memory (`harness.build_agent`).

```bash
export DEEPSEEK_API_KEY=...
python -m examples.llm.run_all                    # scenarios without a stable saved result
python -m examples.llm.run_all --scenario 16 --repetitions 1 --no-judge
python -m examples.llm.run_all --run-all          # everything, 3 repetitions each
python -m examples.llm.run_all --aggregate-only   # rebuild the report from saved results
```

Evidence goes to `NN_slug/results/` and `stability-report.json` (both ignored by git).
Offline tests of the harness with a scripted model are in `tests/ai/test_llm_examples.py`.
