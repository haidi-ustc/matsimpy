# The MatSimPy AI agent

`matsimpy.ai` (the `[ai]` extra) is an LLM agent that works through MatSimPy functions.
It has three extension points, each covered by a section below:

| You want to… | Use | Section |
|---|---|---|
| expose a Python function to the model | `@tool` | [Adding tools](#adding-tools) |
| teach the model a multi-step procedure | a Skill folder with `SKILL.md` | [Creating Skills](#creating-skills) |
| use tools of another program, or MatSimPy's tools from another client | `mcp.json`, `matsimpy-ai mcp serve` | [Configuring MCP servers](#configuring-mcp-servers) |

`examples/ai/extending.py` shows all three, offline.

```text
matsimpy/utils/tooling.py   @tool marker (no dependencies; any layer can use it)
matsimpy/ai/tools.py        Tool, ToolCatalog, ToolExecutor: schemas from signatures, validation, calls
matsimpy/ai/skills.py       SkillLibrary: discover, activate, read_resource, install, remove, drafts
matsimpy/ai/mcp.py          MCPClient (stdio, Streamable HTTP), MCPServer (stdio), mcp.json
matsimpy/ai/provider.py     ChatMessage, ToolCall, DeepSeekProvider (OpenAI-compatible)
matsimpy/ai/agent.py        Agent: loop, meta-tools, JSON sessions
matsimpy/ai/repl.py, terminal.py, cli.py, doctor.py   the matsimpy-ai command
```

## Using the agent

```bash
pip install -e .[ai]
export DEEPSEEK_API_KEY=sk-...
matsimpy-ai                                   # interactive; /help lists the commands
matsimpy-ai -c "build rocksalt NaCl with a=5.64 A and save nacl.cif"
matsimpy-ai -w ~/project -r 20261112-101500-ab12   # resume a session of that workspace
matsimpy-ai doctor [--network]                # check key, workspace, tools, skills, MCP
```

Answers are Markdown. On a terminal they are rendered (headings, tables, lists, code)
with rich. When the output is piped, or with `--raw`, the Markdown source is printed.
Tool calls are shown as `→ name {arguments}` lines on stderr; `-q` hides them. `-c`
exits with 1 when the request fails.

```python
from matsimpy.ai import Agent

with Agent(workspace="project") as agent:
    result = agent.run("Build fcc Cu with a=3.61 A and save cu.cif")
    print(result.status, result.response)
    for call in result.tool_calls:            # ToolRecord(name, arguments, ok, result)
        print(call.name, call.ok, call.result)
```

Any object with `chat(messages, tools) -> ChatResponse` can replace the default
`DeepSeekProvider` (`MATSIMPY_AI_BASE_URL` or `-b` points it at another
OpenAI-compatible endpoint).

**What the model sees.** The system prompt lists every tool *name* (grouped by
module) and every Skill's name and description. Full JSON schemas are sent only
for *loaded* tools: a few common ones plus the meta-tools `search_tools`,
`load_tools`, `activate_skill`, `read_skill_resource` and `propose_skill`. This
keeps requests small with ~80 tools while every tool stays reachable.

**Structures.** A tool that returns a structure stores it and gives the model a
summary with a `structure_ref` such as `"structure:3"`. Later calls pass that
reference (or a workspace file path) wherever a structure is expected.

**Sessions** are JSON files in `<workspace>/.matsimpy/sessions/`, holding the
messages, loaded tools, active Skills and the stored structures. `/undo`, `/retry`,
`/resume` and `/save` work on them. A turn that fails is rolled back.

**Files** are read and written inside the workspace; paths outside it are rejected.

## Adding tools

A tool is an ordinary function with type hints and a docstring. The function is the
single source of truth: name, description, JSON schema and parameter documentation
are derived from it whenever the catalog is built, so they cannot drift.

```python
from matsimpy.core import Crystal
from matsimpy.utils.tooling import tool


@tool
def density(crystal: Crystal) -> dict:
    """Mass density of a crystal.

    Args:
        crystal: The crystal.

    Returns:
        The density in g/cm^3.
    """
    return {"density_g_cm3": float(crystal.density)}
```

Where the function lives decides how it is found:

- **In MatSimPy**: put it in one of the modules of `ai.tools.DEFAULT_TOOL_MODULES`
  (`builders`, `transformation`, `io`, `symmetry`, `analysis`,
  `ai.builtin_tools`) and export it from the package. Nothing else to edit.
- **In your own module**: `matsimpy-ai -t mypackage.tools`, or
  `Agent(tool_modules=[*DEFAULT_TOOL_MODULES, "mypackage.tools"])`. `/tools reload`
  re-imports your modules during a session.
- **In a Skill**: its `tools.py` (below).
- **Directly**: `catalog = ToolCatalog.default(); catalog.add(density)`.

`@tool(name=..., description=..., paths=(...), exclude=(...))` overrides the name or
description, marks string parameters that are file paths (they are resolved inside
the workspace), and hides parameters from the model (they keep their defaults).

### How signatures become schemas

| Annotation | JSON schema | Value passed to the function |
|---|---|---|
| `int`, `float`, `bool`, `str` | `integer`, `number`, `boolean`, `string` | as given |
| `Literal["a", "b"]`, an `Enum` | `enum` | the value / enum member |
| `list[float]`, `tuple[float, float, float]` | `array` (fixed tuples get min/max items) | list / tuple |
| `dict[str, Any]` | `object` | dict |
| `Path`, or a name in `paths=` | `string` | a path inside the workspace |
| `Crystal`, `Molecule`, `Structure` | `string` (a `structure_ref` or a file) | the stored or read structure |
| `list[Crystal]` | `array` of strings | list of structures |
| `Lattice` | 3×3 `array` | `Lattice` |
| `X \| None` | the schema of `X` | `None` when omitted |
| `ToolContext` | *hidden* | workspace, per-session `state`, the executor |

- Parameters without a default are `required`; JSON-compatible defaults are shown.
- Google, NumPy and Sphinx docstrings are read: the summary becomes the description,
  each parameter's text its `description`, and "Returns" is appended.
- An optional parameter of an unsupported type is left out of the schema. A required
  one makes the function fail to load. The failure is reported in
  `ToolCatalog.skipped` and by `matsimpy-ai doctor`.
- Arguments are validated against the schema before the call. A returned structure
  is stored and summarised. `None` becomes `{"status": "ok"}`, and other values are
  converted to JSON.
- Raise `ToolError("message")` for a failure the model should read as is. Other
  exceptions are reported as `"TypeName: message"`. A failure never ends the turn:
  the model sees the error and can correct the call.

Inspect the result with `matsimpy-ai tools list [words]` and
`matsimpy-ai tools show <name>` (the exact JSON sent to the model).

## Creating Skills

A Skill is a folder in the [Agent Skills](https://agentskills.io) format: a
`SKILL.md` with YAML frontmatter and Markdown instructions, plus optional resources
and an optional `tools.py`.

```text
cubic-supercell/
├── SKILL.md         # required
├── tools.py         # optional: @tool functions, loaded on activation
└── reference.md     # optional: resources the model can read on request
```

```markdown
---
name: cubic-supercell
description: Build a near-cubic supercell with at least N atoms. Use when the user asks for a cubic or N-atom supercell.
allowed-tools: make_supercell
---

1. Call `cubic_supercell_matrix` with the crystal and the minimum number of atoms.
2. Build the supercell with `make_supercell` using that matrix.
```

| Field | Rule |
|---|---|
| `name` | required; lowercase letters, digits and hyphens, ≤ 64 characters, equal to the folder name |
| `description` | required, ≤ 1024 characters; says *what* and *when*, because it is all the model sees before activation |
| `allowed-tools` | optional, space-separated tool names the Skill uses; they are loaded on activation |
| `license`, `compatibility`, `metadata` | optional, as in the Agent Skills format |

**Progressive loading.** Discovery reads only the frontmatter. `activate_skill`
(the model, or `/skill <name>`) loads the instructions, lists the resource files and
imports `tools.py`. Its tools are named as written and tagged `skill:<name>`.
`read_skill_resource` reads one resource file, which must stay inside the folder.

**Where Skills live** (a later root shadows an earlier one with the same name):

1. packaged: `matsimpy/ai/builtin_skills/` (e.g. `vasp-inputs`)
2. user: `~/.matsimpy/ai/skills/`
3. workspace: `<workspace>/.matsimpy/skills/`

**Managing Skills:**

```bash
matsimpy-ai skills validate path/to/cubic-supercell    # frontmatter, tools.py syntax and @tool, links
matsimpy-ai skills install path/to/cubic-supercell     # or a .zip; --replace to update
matsimpy-ai skills list
matsimpy-ai skills remove cubic-supercell              # user/workspace Skills only
```

`SkillLibrary(workspace).install(...)`, `.remove(...)`, `.discover()`, `.activate(...)`
and `skills.validate(path)` do the same from Python. `tools.py` runs as normal Python
code when the Skill is activated, so install only Skills you trust. `validate` parses
it without running it.

**Drafts.** When the model has worked out a reusable procedure it can call
`propose_skill(name, description, instructions)`. That writes a *draft* under
`~/.matsimpy/ai/skills/.drafts/`, which is not discoverable. You review it with
`/drafts <name>` and then `/approve <name>` or `/reject <name>`
(`matsimpy-ai skills approve|reject`). Drafts never contain code.

## Configuring MCP servers

The agent connects to the [Model Context Protocol](https://modelcontextprotocol.io)
servers listed in `mcp.json`. Their tools join the catalog as `<server>__<tool>`.

Files read, later overriding earlier for the same server name:
`~/.matsimpy/ai/mcp.json`, then `<workspace>/mcp.json`.

```json
{
  "mcpServers": {
    "local-tool": {
      "command": "python",
      "args": ["-m", "my_server"],
      "env": {"API_TOKEN": "${MY_TOKEN}"},
      "cwd": "/path/to/server",
      "timeout": 60
    },
    "remote": {
      "type": "http",
      "url": "https://mcp.example.org/mcp",
      "headers": {"Authorization": "Bearer ${REMOTE_TOKEN}"}
    },
    "paused": {"command": "other-server", "disabled": true}
  }
}
```

- A server has exactly one of `command` (stdio: a subprocess speaking JSON-RPC over
  stdin/stdout) or `url` (Streamable HTTP: POST, JSON or SSE replies,
  `Mcp-Session-Id`).
- `${NAME}` is replaced by an environment variable, so secrets stay out of the file.
  This applies to `command`, `args`, `env`, `cwd`, `url` and `headers`. An unset
  variable is an error, except in a disabled server.
- `/mcp` and `matsimpy-ai mcp list` show the servers and their tools. `doctor` checks
  the file, and `doctor --network` also connects. A server that fails to start is
  reported, and the agent runs without it.

**MatSimPy as an MCP server.** `matsimpy-ai mcp serve -w <workspace>` serves every
MatSimPy tool over stdio. For example, in a client's configuration:

```json
{"mcpServers": {"matsimpy": {"command": "matsimpy-ai", "args": ["mcp", "serve", "-w", "/data/matsimpy"]}}}
```

Results are returned both as `structuredContent` and as JSON text. A failed call
returns `isError: true` with the message. Structure references stay valid for the
life of the server process.

**Protocol support.** The client and server implement the handshake-based protocol
versions 2024-11-05 through 2025-11-25: `initialize`, `ping`, `tools/list` (with
pagination), `tools/call` and cancellation on timeout. They do not implement
resources, prompts, sampling, OAuth or the stateless `server/discover` probe.
Clients that send the probe get "method not found" and fall back to
`initialize`, as the official SDK does. Interoperability with the official `mcp`
Python SDK is tested in both directions in `tests/ai/test_mcp.py`; those tests are
skipped when the SDK is not installed.

## Testing

```bash
pytest tests/ai -q -p no:xdist                 # offline: a scripted model replaces the LLM
pytest tests/ai/test_live_llm.py -m requires_llm   # live checks, need DEEPSEEK_API_KEY
python -m examples.llm.run_all                  # live corpus with an LLM judge, see examples/llm/README.md
```

`tests/ai/conftest.py` provides `ScriptedProvider`, which replies from a script of
answers and tool calls. Use it to test a new tool or Skill end to end through the agent
without network access.
