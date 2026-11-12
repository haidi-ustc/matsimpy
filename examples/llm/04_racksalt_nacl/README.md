# 04 — Misspelled rocksalt NaCl

Tier: **pipeline**

## Request

Build racksalt sodium chloride with lattice constant 5.64 A and save nacl.cif

## Required tools

`from_prototype`, `write_structure`

## Scientific context

The builder uses 5.64 A as the conventional rocksalt prototype parameter and returns a two-atom primitive rhombohedral cell with vector length 5.64/sqrt(2) and 60 degree angles.

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.04_racksalt_nacl.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
