# 16 — VASP inputs through a Skill

Tier: **skill**

## Request

Prepare VASP relaxation inputs for diamond silicon with a=5.43 A in the directory si_relax, using a k-point density of 1000 per reciprocal atom

## Required tools

`activate_skill`, `from_prototype`, `kpoint_mesh`, `write_vasp_input`

## Scientific context

kpoint_mesh is only available after activating the packaged vasp-inputs skill. No POTCAR is written; the user must supply licensed POTCARs.

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.16_vasp_skill.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
