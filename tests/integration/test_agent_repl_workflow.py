"""Offline end-to-end contracts for Agent, sessions, REPL, and evolution."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from threading import Event, Thread

import pytest

from matsimpy import io
from matsimpy.ai import (
    Agent,
    AgentMemory,
    ChatMessage,
    ChatResponse,
    FunctionDef,
    Skill,
    ToolCall,
)
from matsimpy.ai.cli import _register_all_skills
from matsimpy.ai.doctor import Doctor, render_diagnostics
from matsimpy.ai.engine import AIEngine
from matsimpy.ai.repl import ReplController
from matsimpy.ai.skill import SkillManager
from matsimpy.ai.terminal import PromptToolkitTerminal


ROOT = Path(__file__).resolve().parents[2]


class ScriptedProvider:
    model = "offline-script"

    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None, tool_choice="auto"):
        return self.responses.pop(0)


def _tool(name, arguments):
    call = ToolCall(name, name, arguments)
    message = ChatMessage.assistant(
        "",
        tool_calls=[{
            "id": name,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        }],
    )
    return ChatResponse(message, [call], "tool_calls")


def _manager():
    manager = SkillManager()
    _register_all_skills(manager)
    for skill in manager.list_skills():
        manager.load(skill["name"])
    return manager


def _write_standard_skill(root, name, description, body, allowed_tools=""):
    skill = root / name
    skill.mkdir(parents=True)
    restriction = f"allowed-tools: {allowed_tools}\n" if allowed_tools else ""
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n{restriction}---\n{body}\n",
        encoding="utf-8",
    )


def test_documentation_exposes_executable_agent_entry_points_and_lifecycle():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/user_guide/ai_agent.rst").read_text(encoding="utf-8")

    for text in (readme, guide):
        assert "from matsimpy.ai import Agent" in text
        assert "matsimpy-ai doctor" in text
        assert "SKILL.md" in text
        assert "workspace > user > packaged" in text
        assert "/evolve review" in text
        assert "/approve <version-id>" in text
        assert "/rollback <version-id>" in text


def test_create_transform_analyze_and_save_without_network(tmp_path):
    provider = ScriptedProvider([
        _tool(
            "create_molecule",
            {
                "species": ["H", "H"],
                "positions": [[0, 0, 0], [0.7, 0, 0]],
            },
        ),
        _tool("write_structure", {"path": "h2-input.xyz"}),
        _tool("read_structure", {"path": "h2-input.xyz"}),
        _tool(
            "translate",
            {"structure": {"structure_ref": "structure:2"}, "vector": [1, 0, 0]},
        ),
        _tool("write_structure", {"path": "h2.xyz"}),
        _tool("analyze_bonds", {"path": "h2.xyz", "cutoff": 1.0}),
        ChatResponse(
            ChatMessage.assistant("Created, read, transformed, analyzed, and saved H2."),
            [],
            "stop",
        ),
    ])
    agent = Agent(workspace=tmp_path, provider=provider, skill_manager=_manager())

    result = agent.run("Create H2, translate it, analyze it, and save it.")

    assert result.status == "success"
    assert result.tools == (
        "create_molecule",
        "write_structure",
        "read_structure",
        "translate",
        "write_structure",
        "analyze_bonds",
    )
    assert result.artifacts == (
        str(tmp_path / "h2-input.xyz"),
        str(tmp_path / "h2.xyz"),
    )
    assert io.read(tmp_path / "h2.xyz").formula == "H2"


def test_restart_resume_and_retry_replace_failed_turn(tmp_path):
    first = Agent(
        workspace=tmp_path,
        provider=ScriptedProvider(
            [ChatResponse(ChatMessage.assistant("failed"), [], "error")]
        ),
    )
    failed = first.session.run("retry me")
    conversation_id = failed.conversation_id
    first.session.session_store.close()

    restarted = Agent(
        workspace=tmp_path,
        provider=ScriptedProvider(
            [ChatResponse(ChatMessage.assistant("recovered"), [], "stop")]
        ),
    )
    controller = ReplController(restarted.session, evolution=restarted)

    assert controller.execute(f"/resume {conversation_id}").ok
    retried = controller.execute("/retry")
    assert retried.ok
    assert restarted.session.turns[-1].final_response == "recovered"
    assert restarted.session.turns[-1].parent_attempt_id == failed.attempt_id


def test_engine_repl_discovers_precedence_and_activates_standard_skill(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("HOME", str(home))
    _write_standard_skill(
        home / ".matsimpy/ai/skills",
        "shared-flow",
        "User flow",
        "USER INSTRUCTIONS",
    )
    _write_standard_skill(
        workspace / ".matsimpy/skills",
        "shared-flow",
        "Workspace flow",
        "WORKSPACE INSTRUCTIONS",
        "create_molecule unavailable_tool",
    )
    engine = AIEngine(api_key="unused", workspace_path=str(workspace))
    _register_all_skills(engine.skill_manager)

    listed = engine.repl_controller.execute("/skills shared-flow")
    loaded = engine.repl_controller.execute("/load-skill shared-flow")

    assert listed.ok
    assert listed.data["skill"]["source"] == "workspace"
    assert listed.data["skill"]["description"] == "Workspace flow"
    assert listed.data["skill"]["allowed_tools"] == ["create_molecule"]
    assert loaded.ok
    assert loaded.data["skill"] == {"name": "shared-flow", "loaded": True}
    assert engine.agent.session.context_messages[-1].content.endswith(
        "WORKSPACE INSTRUCTIONS"
    )


def test_public_workspace_switch_rebinds_standard_skill_roots(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_standard_skill(
        first / ".matsimpy/skills",
        "shared-flow",
        "First workspace flow",
        "FIRST WORKSPACE INSTRUCTIONS",
    )
    _write_standard_skill(
        first / ".matsimpy/skills",
        "first-only",
        "First only",
        "FIRST ONLY",
    )
    _write_standard_skill(
        second / ".matsimpy/skills",
        "shared-flow",
        "Second workspace flow",
        "SECOND WORKSPACE INSTRUCTIONS",
    )
    _write_standard_skill(
        second / ".matsimpy/skills",
        "second-only",
        "Second only",
        "SECOND ONLY",
    )
    engine = AIEngine(api_key="unused", workspace_path=str(first))
    _register_all_skills(engine.skill_manager)
    assert engine.repl_controller.execute("/skills first-only").ok

    engine.agent.switch_workspace(second)
    listed = engine.repl_controller.execute("/skills")
    loaded = engine.repl_controller.execute("/load-skill shared-flow")

    names = {item["name"] for item in listed.data["skills"]}
    assert "first-only" not in names
    assert "second-only" in names
    assert loaded.ok
    assert engine.agent.session.context_messages[-1].content.endswith(
        "SECOND WORKSPACE INSTRUCTIONS"
    )


def test_interactive_completion_skips_legacy_and_invalid_user_skill_directories(
    tmp_path, monkeypatch
):
    pytest.importorskip("prompt_toolkit")
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("HOME", str(home))
    legacy = home / ".matsimpy/ai/skills/generated"
    legacy.mkdir(parents=True)
    (legacy / "legacy.skill.md").write_text("legacy")
    invalid = home / ".matsimpy/ai/skills/invalid-skill"
    invalid.mkdir()
    (invalid / "SKILL.md").write_text("not frontmatter")
    _write_standard_skill(
        workspace / ".matsimpy/skills",
        "valid-flow",
        "Valid flow",
        "VALID INSTRUCTIONS",
    )
    monkeypatch.setattr(
        "matsimpy.ai.provider.DeepSeekProvider.chat",
        lambda self, messages, tools=None, tool_choice="auto": ChatResponse(
            ChatMessage.assistant("submitted"), [], "stop"
        ),
    )
    engine = AIEngine(api_key="unused", workspace_path=str(workspace))
    _register_all_skills(engine.skill_manager)
    rendered = []
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(
            engine.repl_controller,
            history_path=tmp_path / "history",
            input=pipe,
            output=DummyOutput(),
            output_writer=rendered.append,
        )
        assert terminal.completion_candidates("valid") == ("valid-flow",)
        pipe.send_text("normal prompt\r/quit\r")
        terminal.run()

    assert "submitted" in rendered
    listed = engine.repl_controller.execute("/skills")
    assert listed.ok
    assert "valid-flow" in {item["name"] for item in listed.data["skills"]}
    diagnostics = engine.agent.skill_library.diagnostics
    assert {(item.code, item.skill_name) for item in diagnostics} == {
        ("legacy-generated-root", "generated"),
        ("invalid-skill", "invalid-skill"),
    }


def test_prompt_toolkit_plain_enter_submits_to_real_controller(tmp_path, monkeypatch):
    pytest.importorskip("prompt_toolkit")
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    called = Event()

    def respond(self, messages, tools=None, tool_choice="auto"):
        called.set()
        return ChatResponse(ChatMessage.assistant("submitted"), [], "stop")

    monkeypatch.setattr("matsimpy.ai.provider.DeepSeekProvider.chat", respond)
    engine = AIEngine(api_key="unused", workspace_path=str(tmp_path / "workspace"))
    _register_all_skills(engine.skill_manager)
    rendered = []
    submitted_by_enter = Event()
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(
            engine.repl_controller,
            history_path=tmp_path / "history",
            input=pipe,
            output=DummyOutput(),
            output_writer=rendered.append,
        )
        def feed_input():
            pipe.send_text("ordinary prompt\r")
            if called.wait(1):
                submitted_by_enter.set()
            pipe.send_text("\x03/quit\r\x1b\r")

        worker = Thread(target=feed_input, daemon=True)
        worker.start()
        terminal.run()
        worker.join(timeout=2)

    assert not worker.is_alive()
    assert submitted_by_enter.is_set(), "ordinary Enter did not submit the prompt"
    assert "submitted" in rendered


def test_skill_requires_review_then_approval_before_repl_can_use_it(tmp_path):
    call = ToolCall("offline", "offline_step", {})
    agent = Agent(
        workspace=tmp_path,
        provider=ScriptedProvider(
            [
                ChatResponse(
                    ChatMessage.assistant(
                        "",
                        tool_calls=[{
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": {}},
                        }],
                    ),
                    [call],
                    "tool_calls",
                ),
                ChatResponse(ChatMessage.assistant("ok"), [], "stop"),
            ]
        ),
    )
    tool = FunctionDef(
        "offline_step", "Offline step", {"type": "object", "properties": {}},
        lambda: {"ok": True},
        skill="seed",
    )
    agent.skill_manager.register(Skill("seed", "Seed", [tool]))
    agent.skill_manager.load("seed")
    trace_id = agent.run("record evidence").trace_id
    assert trace_id is not None
    draft = agent.evolution.draft_skill(
        "offline-flow",
        "Offline flow",
        "Run `offline_step`.",
        ["offline_step"],
        [trace_id],
    )
    controller = ReplController(agent.session, evolution=agent)

    assert "offline-flow" not in agent.skill_manager.active_skills
    review = controller.execute(f"/evolve review {draft.id}")
    assert review.data["candidates"][0]["approvable"] is True
    assert review.data["candidates"][0]["deterministic_evidence"] == {
        "passed": True,
        "source_trace_ids": [trace_id],
        "replayed_tools": ["offline_step"],
    }
    approved = controller.execute(f"/approve {draft.id}")
    assert approved.ok
    assert "offline-flow" in {item["name"] for item in agent.skill_manager.list_skills()}


def test_credentials_are_absent_from_runtime_doctor_and_evolution_state(
    tmp_path, monkeypatch
):
    sentinel = "TASK13_CREDENTIAL_SENTINEL_74b91f36"
    home = tmp_path / "isolated-home"
    workspace = home / "workspace"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DEEPSEEK_API_KEY", sentinel)
    call = ToolCall("safe", "safe_step", {})
    provider = ScriptedProvider([
        ChatResponse(
            ChatMessage.assistant(
                "",
                tool_calls=[{
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": {}},
                }],
            ),
            [call],
            "tool_calls",
        ),
        ChatResponse(ChatMessage.assistant("complete"), [], "stop"),
    ])
    provider.api_key = sentinel
    agent = Agent(
        workspace=workspace,
        provider=provider,
        memory=AgentMemory(home / ".matsimpy/ai/memory"),
    )
    definition = FunctionDef(
        "safe_step",
        "Safe offline step",
        {"type": "object", "properties": {}},
        lambda: {"safe": True},
        skill="safe",
    )
    agent.skill_manager.register(Skill("safe", "Safe", [definition]))
    agent.skill_manager.load("safe")
    trace_id = agent.run("execute safe workflow").trace_id
    assert trace_id is not None
    draft = agent.evolution.draft_skill(
        "safe-flow", "Safe flow", "Run `safe_step`.", ["safe_step"], [trace_id]
    )
    reviewed = agent.review_evolution(draft.id)
    agent.approve_skill(reviewed["version_id"])
    rendered = render_diagnostics(
        Doctor(
            workspace=workspace,
            state_dir=workspace,
            database=workspace / "ai-state.db",
            environ=os.environ,
        ).run()
    )

    assert sentinel not in rendered
    for path in home.rglob("*"):
        if path.is_file() and path.suffix not in {".db", ".sqlite", ".sqlite3"}:
            assert sentinel.encode() not in path.read_bytes(), path
    database = workspace / "ai-state.db"
    with sqlite3.connect(database) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        ]
        for table in tables:
            for row in connection.execute(f'SELECT * FROM "{table}"'):
                for value in row:
                    if isinstance(value, str):
                        assert sentinel not in value, (table, value)
                    elif isinstance(value, bytes):
                        assert sentinel.encode() not in value, table
