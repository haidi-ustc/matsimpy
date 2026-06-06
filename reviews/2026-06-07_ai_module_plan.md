# AI Module Redesign — Implementation Plan

> **Goal:** Replace current AI module with LLM function-calling system: SkillManager + DeepSeekProvider + interactive REPL.

**Architecture:** 8 new files. Progressive skill loading. DeepSeek API provider. Function calling via OpenAI-compatible tool use.

**Tech Stack:** Python 3.10+, requests (or httpx), DeepSeek API

---

### Task 1: conversation.py — Data classes

**Create:** `matsimpy/ai/conversation.py`

```python
from dataclasses import dataclass, field

@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class ChatResponse:
    message: ChatMessage
    tool_calls: list   # list[ToolCall]
    finish_reason: str  # "stop" | "tool_calls" | "length"
```

### Task 2: skill.py — FunctionDef, Skill, SkillManager

**Create:** `matsimpy/ai/skill.py`

- `FunctionDef(name, description, parameters, callable, skill, help_text)` with `to_openai_tool()`
- `Skill(name, description, functions, loaded, token_estimate)`
- `SkillManager` with `load()`, `unload()`, `get_tools()`, `auto_load()`, `find_function()`
- `auto_load` uses keyword-to-skill mapping: {"slab": "builders", "translate": "transformation", "bond": "analysis", ...}

### Task 3: provider.py — DeepSeekProvider

**Create:** `matsimpy/ai/provider.py`

- OpenAI-compatible client using `requests.post`
- `chat(messages, tools, tool_choice)` → `ChatResponse`
- Parses `response.choices[0].message.tool_calls` into `ToolCall` list
- Handles `DEEPSEEK_API_KEY` env var

### Task 4: executor.py — FunctionExecutor

**Create:** `matsimpy/ai/executor.py`

- Takes `SkillManager` reference
- `execute(tool_call)` → validates, calls, serializes
- `_validate_params(fn_def, args)` → validates required params, basic type checks
- `_serialize_result(result)` → Crystal/Molecule → dict summary

### Task 5: engine.py — AIEngine

**Create:** `matsimpy/ai/engine.py`

- Orchestrates `provider + skill_manager + executor + conversation`
- `chat(user_message)` → message → tool calls loop → final response
- `repl()` → interactive loop with `/commands`

### Task 6: skills/*.py — 6 skill definition files

**Create:** `matsimpy/ai/skills/core.py`, `builders.py`, `transformation.py`, `analysis.py`, `io.py`, `storage.py`

Each file builds `FunctionDef` list from existing matsimpy APIs. Core skill auto-loaded. Builder/transform skills use existing `BuilderSpec`/`TransformationSpec` registries for parameter schemas.

### Task 7: cli.py — REPL entry point

**Create:** `matsimpy/ai/cli.py`

- `main()` → `AIEngine().repl()`
- Handles `/commands`: skills, load, unload, help, system, history, clear, save, quit

### Task 8: Delete old AI module, update __init__.py

**Remove:** `interfaces/`, `operations/`, `models/`, `utils/`, `base.py`
**Keep then overwrite:** `__init__.py` with new exports
