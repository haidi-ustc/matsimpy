# Extending the AI agent

`extending.py` runs offline (no API key) and shows the three extension points:

| Folder / file | What it shows |
|---|---|
| `extending.py` | a custom `@tool`, installing and activating a Skill, MatSimPy's MCP server and client, and one agent turn with a stand-in model |
| `skills/cubic-supercell/` | a complete Skill: `SKILL.md` (frontmatter + instructions) and `tools.py` (its own `@tool` functions) |
| `mcp.json` | an MCP configuration with a stdio server and a disabled HTTP server; `${NAME}` reads an environment variable |

```bash
python -m examples.ai.extending
matsimpy-ai skills validate examples/ai/skills/cubic-supercell
matsimpy-ai skills install examples/ai/skills/cubic-supercell     # into ~/.matsimpy/ai/skills
cp examples/ai/mcp.json <workspace>/mcp.json                       # or ~/.matsimpy/ai/mcp.json
```

See [docs/ai.md](../../docs/ai.md) for the full reference.
