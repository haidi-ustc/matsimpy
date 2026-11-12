# 01 — Water molecule to XYZ

Tier: **pipeline**

## Request

Create a water molecule with Cartesian positions O=(0,0,0), H=(0.96,0,0), H=(-0.24,0.93,0), then save water.xyz

## Required tools

`create_molecule`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.01_water_xyz.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
