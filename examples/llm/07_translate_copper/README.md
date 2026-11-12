# 07 — Build and translate copper

Tier: **pipeline**

## Request

Build fcc Cu with a=3.61 A, translate it by [0.1,0,0] A, and save translated.cif

## Required tools

`from_prototype`, `translate`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.07_translate_copper.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
