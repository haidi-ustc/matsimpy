# 06 — Random SiO2 with PyXtal

Tier: **pipeline**

## Request

Generate a random SiO2 crystal in space group 1 with 1 Si and 2 O atoms, then save random_sio2.cif

## Required tools

`random_crystal`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.06_random_sio2.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
