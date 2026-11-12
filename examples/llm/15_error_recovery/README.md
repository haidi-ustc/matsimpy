# 15 — Invalid prototype recovery

Tier: **recovery**

## Request

Try to build prototype unobtainium for Cu; if MatSimPy rejects it, recover by building fcc Cu with a=3.61 A and save recovered.cif

## Required tools

`from_prototype`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.15_error_recovery.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
