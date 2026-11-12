# 10 — Read and analyze water bonds

Tier: **single**

## Request

Create water with O at [0,0,0] and H at [0.96,0,0] and [-0.24,0.93,0], save water.xyz, then analyze its bonds with cutoff 1.2 A

## Required tools

`analyze_bonds`, `create_molecule`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.10_water_bonds.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
