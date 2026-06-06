# AI Module Redesign — Design Spec

Date: 2026-06-07
Status: Design approved

## Architecture

```
matsimpy/ai/
├── __init__.py          # re-exports: AIEngine, Skill, FunctionDef, etc.
├── engine.py            # AIEngine — main entry, orchestrates chat + tools
├── provider.py          # DeepSeekProvider — OpenAI-compatible API client
├── skill.py             # Skill, FunctionDef, SkillManager — progressive loading
├── executor.py          # FunctionExecutor — validate params, call functions
├── conversation.py      # ChatMessage, ToolCall, ChatResponse dataclasses
├── cli.py               # Interactive REPL with /commands
├── skills/              # One file per skill domain
│   ├── core.py          # Crystal, Molecule, Structure APIs
│   ├── builders.py      # from_prototype, create_vacancy, generate_slab, etc.
│   ├── transformation.py # translate, rotate, apply_strain, substitute, etc.
│   ├── analysis.py      # BondAnalyzer, StructureAnalyzer, TopologyAnalyzer
│   ├── io.py            # read, write, format conversion
│   └── storage.py       # DataStorage API
```

## Key Components

### FunctionDef
- `name`, `description`, `parameters` (JSON Schema), `callable`, `skill`, `help_text`
- `to_openai_tool()` → `{"type": "function", "function": {...}}`
- Constructed from existing `TransformationSpec`/`BuilderSpec` parameter_schema where available
- `help_text` lazy-loaded from function `__doc__`

### Skill + SkillManager
- Each skill: `name`, `description`, `list[FunctionDef]`, `loaded`, `token_estimate`
- `SkillManager.load(name)`, `.unload(name)`, `.get_tools()`, `.auto_load(message)`
- `auto_load` uses keyword heuristics to load relevant skills from user message
- Core skill always loaded (~10 functions, minimal tokens)

### DeepSeekProvider
- OpenAI-compatible: `POST https://api.deepseek.com/v1/chat/completions`
- `chat(messages, tools, tool_choice="auto")` → `ChatResponse`
- `ChatResponse` has `message: ChatMessage` + `tool_calls: list[ToolCall]`
- Environment variable: `DEEPSEEK_API_KEY`

### FunctionExecutor
- Validates `ToolCall.arguments` against `FunctionDef.parameters` (JSON Schema validation)
- Calls `FunctionDef.callable(**args)`, catches exceptions
- Serializes results (Crystal→dict with formula, atoms, lattice)
- Respects max call depth (prevent infinite tool loops)

### AIEngine + REPL
- Orchestrates: provider → skill_manager → executor → conversation
- `chat(user_message)` → one turn with tool call loop
- `repl()` → interactive loop with `/commands`

### REPL Commands
| `/skills` | List skills + load status |
| `/load <name>` | Load skill (progressive) |
| `/unload <name>` | Free context space |
| `/help [fn]` | Show FunctionDef help |
| `/system <text>` | Set custom system prompt |
| `/history` | Show recent messages |
| `/clear` | Reset conversation |
| `/save <path>` | Save conversation JSON |
| `/quit` | Exit |

### Skill Definitions
- Built from existing `TransformationSpec` (parameter_schema already accurate) and `BuilderSpec`
- Core skill: domain model ops (create Crystal/Molecule, add/remove/substitute atoms)
- Builder skill: all registered `BuilderSpec` functions
- Transformation skill: all registered `TransformationSpec` functions
- Analysis skill: BondAnalyzer, StructureAnalyzer, TopologyAnalyzer
- IO skill: read, write
- Storage skill: DataStorage store/retrieve/query

## Provider
- DeepSeek API (`api.deepseek.com`)
- Model: `deepseek-chat`
- Supports OpenAI-compatible function calling / tool use

## Non-Goals
- No MCP protocol
- No model training/fine-tuning
- No streaming (v1)
- No multi-turn autonomous agents (v1)
