# 13 — Save, store, and retrieve

Tier: **pipeline**

## Request

Build fcc aluminum with a=4.05 A, save aluminum.cif, store it with metadata project=demo, then retrieve it

## Required tools

`from_prototype`, `retrieve_structure`, `store_structure`, `write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.13_store_retrieve.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
