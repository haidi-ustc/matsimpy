# 05 — Wurtzite GaN

Tier: **pipeline**

## Request

Build wurtzite GaN with lattice constants a=3.19 A and c=5.19 A, then save gan.cif

## Required tools

`from_prototype`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.05_wurtzite_gan.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
