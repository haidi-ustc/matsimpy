# 17 — BCC iron through an MCP server

Tier: **mcp** · connects MatSimPy's own MCP server as `matsimpy`

## Request

Using only the tools of the matsimpy MCP server (names starting with matsimpy__), build bcc iron with a=2.87 A and save it as fe.cif

## Required tools

`matsimpy__from_prototype`, `matsimpy__write_structure`

## Run

```bash
DEEPSEEK_API_KEY=... python -m examples.llm.17_mcp_iron.run
```

Evidence is written to `results/` (ignored by git): `run-N.json`, `latest.md` and `summary.json`.
