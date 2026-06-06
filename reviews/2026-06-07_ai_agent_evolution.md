# AI Agent Evolution — Design Spec

Date: 2026-06-07
Status: Design approved

## 1. Workspace

```
~/.matsimpy/ai/
├── workspace/          # default pwd — all file ops
├── memory/             # agent memory files
├── skills/
│   ├── builtin/        # built-in skills
│   └── generated/      # auto-saved skills (.skill.md)
└── history/            # saved conversations
```

CLI: `matsimpy --workspace /path/to/project` (typer). Default: `~/.matsimpy/ai/workspace`.

## 2. Agent Evolution Files (`~/.matsimpy/ai/memory/`)

| File | Purpose | Updated |
|---|---|---|
| `user.md` | User preferences, project context, conventions | User edits or agent infers |
| `agent.md` | Agent capabilities, loaded skills, defaults | Auto on `/save-agent` |
| `soul.md` | Personality, tone, verbosity, response style | User-configured |
| `memory.md` | Learned facts, corrections, patterns | Auto each turn |

`soul.md` loaded into system prompt at startup. `memory.md` appended with key learnings.

## 3. Learn from Success/Failure

After each chat turn, LLM reflects and appends insight to `memory.md`:
- Success: what pattern worked, what defaults were good
- Failure: what went wrong, what the correction was
- Pattern: "user regularly asks for FCC Cu at 3.61 → default to this"

## 4. Auto-Save Skills — Claude-Compatible

Generated skills saved as `.skill.md` with YAML frontmatter:

```markdown
---
name: supercell-vacancy-substitution
description: Create supercell with vacancy and Ni substitution
category: ai-generated
version: 1.0.0
load_mode: auto_choice      # auto_load | auto_choice | manual
trigger_keywords: [dope, supercell, vacancy, substitute]
tools:
  - function: make_supercell
    args_template: {scaling_matrix: [2, 2, 2]}
  - function: create_vacancy
    args_template: {indices: 0}
  - function: substitute
    args_template: {indices: 0, new_species: Ni}
created_at: 2026-06-07T12:00:00
usage_count: 0
---

# Supercell Vacancy Substitution
...
```

Three loading modes:
- `auto_load` — loads on keyword match (current behavior)
- `auto_choice` — LLM sees in "available skills" list, decides whether to call `/load`
- `manual` — user must `/load <name>` explicitly

SkillManager scans `~/.matsimpy/ai/skills/generated/` at startup for `.skill.md` files.
