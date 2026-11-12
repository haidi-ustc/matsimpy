# 02 — Explicit fractional crystal

Tier: **single**

## Request

Create a periodic cubic crystal with species Li and F at fractional coordinates [0,0,0] and [0.5,0.5,0.5], a=4.02 A. Do not infer or name a prototype; report only the supplied geometry.

## Required tools

`create_crystal`

## Scientific context

The low-level constructor establishes only the supplied simple-cubic lattice and coordinates. It does not establish a named prototype; these positions must not be called rocksalt.

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.02_explicit_crystal.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
