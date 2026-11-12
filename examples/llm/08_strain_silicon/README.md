# 08 — Build and strain silicon

Tier: **pipeline**

## Request

Build diamond silicon with a=5.43 A, apply 1 percent isotropic strain, and save strained_si.cif

## Required tools

`from_prototype`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.08_strain_silicon.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
