# 12 — Silicon symmetry

Tier: **pipeline**

## Request

Build diamond silicon with a=5.43 A and analyze its symmetry

## Required tools

`analyze_symmetry`, `from_prototype`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.12_silicon_symmetry.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
