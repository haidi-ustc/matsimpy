# 09 — Supercell vacancy pipeline

Tier: **pipeline**

## Request

Build fcc Cu with a=3.61 A, make a 2x2x2 supercell, create one vacancy at site 0, and save cu_vacancy.cif

## Required tools

`create_vacancy`, `from_prototype`, `make_supercell`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.09_supercell_vacancy.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
