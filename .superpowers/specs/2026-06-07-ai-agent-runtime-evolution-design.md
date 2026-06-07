# MatSimPy AI Agent Runtime And Evolution Design

Date: 2026-06-07
Status: Approved design
Scope: `matsimpy/ai/`

## Goal

Redesign the MatSimPy AI module into a Hermes-inspired agent runtime that works through both the interactive REPL and `matsimpy -c`, while supporting semi-automatic evolution. The first phase should deliver a reliable agent loop, searchable task traces, bounded memory, provider abstraction, and reviewable workflow skill drafts.

## Current Code Assessment

The current AI module is a DeepSeek-backed function-calling REPL. It already has useful pieces:

- `AIEngine` orchestrates conversation, tools, workspace, memory, and REPL commands.
- `SkillManager` progressively loads builtin skills from dynamically discovered skill modules.
- `FunctionExecutor` preserves live structure objects through `_obj_ref` serialization and auto-retry adaptation.
- `AgentMemory` persists markdown memory files under `~/.matsimpy/ai/memory/`.
- `skill_loader.py` can parse and save generated `.skill.md` files.
- `cli.py` supports interactive and single-command modes.

The main gaps are:

- The agent loop is chat-oriented, not task-oriented.
- REPL and single-shot behavior are not backed by a clear shared runtime contract.
- Memory appends every learned entry without limits, duplicate handling, replacement, or search.
- Generated skills are derived mostly from tool names and are enabled too casually.
- There is no SQLite session or trace store, so prior evidence is hard to inspect or reuse.
- Provider behavior is hard-wired to the current DeepSeek/OpenAI-compatible client.
- Validation is implicit instead of part of the turn lifecycle.

## Hermes Patterns To Adapt

Hermes is useful as a reference because it separates the agent into layers:

- One platform-agnostic agent loop used by multiple entry points.
- Stable prompt assembly with compact memory and project context.
- A provider/runtime boundary separate from agent behavior.
- Full session persistence with searchable history.
- Skills as procedural memory, not just tool schemas.
- Agent-created skills that can be curated, archived, and rolled back.
- Safety controls around risky operations and persistent changes.

MatSimPy should adapt these ideas narrowly. Phase 1 should not replicate Hermes gateways, cron jobs, subagents, terminal backends, external memory providers, or full background self-optimization.

## Architecture

Add a new `AgentRuntime` layer above the existing provider, skill manager, executor, memory, and workspace.

The runtime owns this lifecycle:

```text
user request
-> context assembly
-> task plan
-> tool loop
-> validation
-> trace persistence
-> learning proposal
```

Planned modules:

| File | Responsibility |
| --- | --- |
| `matsimpy/ai/runtime.py` | `AgentRuntime`, `TaskResult`, turn lifecycle, iteration budget |
| `matsimpy/ai/providers.py` | `ChatProvider` protocol plus DeepSeek/OpenAI-compatible implementation |
| `matsimpy/ai/session_store.py` | SQLite sessions, messages, tool calls, task traces, skill drafts, FTS search |
| `matsimpy/ai/memory.py` | Existing markdown files plus bounded add/replace/remove behavior |
| `matsimpy/ai/evolution.py` | Trace-to-draft-skill proposal generation and approval transitions |
| `matsimpy/ai/skill_loader.py` | Existing discovery plus draft/approved generated skill state |
| `matsimpy/ai/engine.py` | Compatibility wrapper around `AgentRuntime` |
| `matsimpy/ai/cli.py` | Thin entry point and command renderer |

Existing builtin skills and `FunctionExecutor` should be reused. The redesign should avoid changing MatSimPy domain APIs unless tests expose an integration bug.

## Agent Behavior

Both REPL and `matsimpy -c` call the same runtime. Single-shot mode is autonomous by default; REPL exposes the same behavior conversationally.

Each task runs a bounded loop:

1. Assemble context from system identity, compact memory, workspace, approved generated skills, and relevant session-search hints.
2. Ask the provider for the next assistant message with current tool schemas.
3. Execute tool calls through `FunctionExecutor`.
4. Append tool results and continue until a final response, validation failure, or iteration limit.
5. Validate the task before final output.
6. Persist the session and trace to SQLite.
7. Draft a workflow skill only when the trace is successful and reusable.

Validation should be lightweight and deterministic:

- If a file write tool reports success, verify the output path exists.
- If a structure is created or transformed, verify `_obj_ref`, formula, and atom count are present.
- If analysis runs, verify expected result fields exist and no tool call returned an error.
- If validation fails, the runtime gives the model one chance to repair before reporting failure.

The current silent auto-save behavior is removed. A reusable workflow becomes a disabled draft:

```text
Draft skill created: vacancy-substitution-workflow.
Use /approve-skill vacancy-substitution-workflow to enable it.
```

## Memory And Session Persistence

Use three persistence layers.

### Compact Memory Files

Keep markdown files under `~/.matsimpy/ai/memory/`:

- `user.md`: durable user preferences and communication style.
- `memory.md`: project, environment, workflow, and tool lessons.
- `soul.md`: assistant identity and style.
- `agent.md`: capabilities, loaded skill defaults, and known limitations.

Add operations:

- `add(target, content)`
- `replace(target, old_text, content)`
- `remove(target, old_text)`
- `summary()`

Memory writes must enforce character limits, reject exact duplicates, and reject obvious prompt-injection or credential-exfiltration patterns. Memory should store stable facts, not raw logs or one-off temporary paths.

### SQLite Session Store

Add SQLite storage under `~/.matsimpy/ai/state.db`.

Minimum tables:

- `sessions`: id, source, workspace, model, provider, started/ended timestamps, status.
- `messages`: session id, role, content, tool calls, tool call id, timestamp.
- `tool_calls`: session id, tool name, arguments JSON, result JSON, status, timestamp.
- `task_traces`: session id, user request, plan summary, validation status, final response.
- `skill_drafts`: name, status, source session, trigger keywords, body, metadata JSON, timestamps.
- FTS table over message content, tool names, and trace summaries.

Search is keyword/FTS based in phase 1. No embeddings or external memory provider are added.

### Workflow Skill Drafts

`evolution.py` creates a draft when a successful trace has a reusable pattern, usually two or more meaningful tool calls. Drafts include:

- Name and description.
- Trigger keywords.
- Source session id.
- Tool sequence and important arguments.
- Expected inputs and outputs.
- Validation evidence.
- Failure notes or assumptions.
- Markdown body with procedure and verification steps.

Draft lifecycle:

```text
draft -> approved -> active
draft -> rejected -> archived
approved -> archived
```

Approved generated skills are discoverable and loadable. Draft and rejected skills are visible through commands but do not participate in auto-load.

## CLI And REPL Commands

Keep existing commands where possible and add:

- `/plan`: show the current or last task plan.
- `/trace`: show the last persisted trace summary.
- `/sessions`: list/search recent sessions.
- `/drafts`: list draft workflow skills.
- `/approve-skill <name>`: enable a draft skill.
- `/reject-skill <name>`: archive or reject a draft.
- `/memory add|replace|remove|show`: manage compact memory.

`matsimpy -c "..."` should print:

- Loaded skills.
- Tool calls and validation status.
- Final answer.
- Draft skill notification if created.

## Provider Boundary

Define a small provider protocol:

```python
class ChatProvider(Protocol):
    model: str

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> ChatResponse:
        ...
```

Keep one implementation in phase 1: the current DeepSeek/OpenAI-compatible provider. Do not add OpenAI, Anthropic, Ollama, provider fallback, or model routing yet. The point of the protocol is to decouple runtime design from provider-specific HTTP details.

## Safety

Phase 1 safety rules:

- Generated skills require explicit approval before activation.
- Drafts are stored separately from active generated skills.
- File writes default to the configured workspace.
- Prevent accidental overwrites unless explicitly requested or supported by the tool.
- Do not add arbitrary shell or Python execution tools.
- Memory writes are size-limited and scanned before persistence.
- SQLite persistence must not store API keys or environment variables.

## Testing Plan

Add focused tests:

- Provider protocol compatibility and DeepSeek/OpenAI-compatible response parsing.
- `AgentRuntime` loop using a fake provider that emits deterministic tool calls.
- Runtime validation for created structures, file outputs, analysis results, and failed tool calls.
- SQLite session persistence, trace persistence, and FTS search.
- Memory add/replace/remove, character limits, duplicate prevention, and injection rejection.
- Skill draft generation, approval, rejection, and discovery state.
- Single-shot integration with fake provider: create structure, save file, validate output, persist trace, draft skill after success.
- Regression tests for current `FunctionExecutor` object reference round-tripping and auto-retry adaptation.

## Non-Goals

Phase 1 will not implement:

- Messaging gateways.
- Cron/scheduled automations.
- Subagent delegation.
- Terminal or browser automation.
- External memory providers.
- Embedding/vector search.
- Background skill curator.
- Automatic skill patching without user approval.
- Multiple providers or fallback provider chains.
- Model training, reinforcement learning, DSPy, or GEPA-style optimization.

## Stop Condition

Implementation is complete when REPL and `matsimpy -c` both use the same runtime, successful tasks persist searchable traces, compact memory is bounded and manageable, successful reusable workflows create disabled draft skills, approved skills become loadable, and all targeted AI tests pass.
