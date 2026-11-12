# 14 — Multi-turn NaCl workflow

Tier: **multiturn**

## Request

1. Build rocksalt NaCl with lattice constant 5.64 A
2. Now make a 2x1x1 supercell and save it as nacl_supercell.cif

## Required tools

`from_prototype`, `make_supercell`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.14_multiturn_nacl.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
