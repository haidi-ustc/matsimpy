# 11 — Argon dimer Lennard-Jones

Tier: **pipeline**

## Request

Create an argon dimer at Cartesian coordinates [0,0,0] and [4,0,0], then calculate Lennard-Jones energy and forces

## Required tools

`calculate_lennard_jones`, `create_molecule`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.11_argon_lj.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
