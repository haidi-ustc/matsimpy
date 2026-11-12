# 03 — FCC copper to CIF

Tier: **pipeline**

## Request

Build fcc copper with lattice constant 3.61 A and save fcc_cu.cif

## Required tools

`from_prototype`, `write_structure`

## Scientific context

The builder uses 3.61 A as the conventional FCC prototype parameter and returns a one-atom primitive rhombohedral cell with vector length 3.61/sqrt(2).

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.03_fcc_copper.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
