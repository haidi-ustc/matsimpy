"""Public Agent facade and legacy AIEngine compatibility."""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import pytest

from matsimpy.ai.conversation import ChatMessage, ChatResponse, ToolCall
from matsimpy.ai.skill import FunctionDef, Skill


class FakeProvider:
    model = "fake-agent-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(list(messages))
        return self.responses.pop(0)


def _tool_message(call: ToolCall) -> ChatMessage:
    return ChatMessage.assistant(
        "",
        tool_calls=[{
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": "{}"},
        }],
    )


def test_agent_run_returns_structured_result_and_artifacts(tmp_path):
    from matsimpy.ai import Agent, AgentResult

    call = ToolCall("build-1", "build_fcc", {})
    provider = FakeProvider([
        ChatResponse(_tool_message(call), [call], "tool_calls"),
        ChatResponse(ChatMessage.assistant("Built copper."), [], "stop"),
    ])
    agent = Agent(workspace=tmp_path, provider=provider)

    def build_fcc():
        path = Path("copper.cif")
        path.write_text("Cu")
        return {"formula": "Cu", "saved_to": str(path)}

    skill = Skill("test", "test", [FunctionDef(
        name="build_fcc",
        description="Build FCC copper",
        parameters={"type": "object", "properties": {}},
        callable=build_fcc,
    )])
    skill.keywords = ["fcc", "copper"]
    agent.skill_manager.register(skill)
    agent.skill_manager.load("test")

    result = agent.run("build fcc copper")

    assert isinstance(result, AgentResult)
    assert result.response == "Built copper."
    assert result.status == "success"
    assert result.tools == ("build_fcc",)
    assert result.artifacts == (str(tmp_path / "copper.cif"),)
    assert result.trace_id is not None
    assert result.usage == {}
    assert result.evolution_candidates == ()


def test_agent_run_restores_callers_working_directory(tmp_path):
    from matsimpy.ai import Agent

    provider = FakeProvider([
        ChatResponse(ChatMessage.assistant("Done."), [], "stop"),
    ])
    agent = Agent(workspace=tmp_path, provider=provider)
    original = Path.cwd()

    agent.run("answer")

    assert Path.cwd() == original


def test_agent_replays_complete_tool_evidence_on_follow_up(tmp_path):
    from matsimpy.ai import Agent

    build = ToolCall("build", "build_copper", {})
    save = ToolCall("save", "save_copper", {"path": "copper.cif"})
    provider = FakeProvider([
        ChatResponse(_tool_message(build), [build], "tool_calls"),
        ChatResponse(ChatMessage.assistant("Copper is ready."), [], "stop"),
        ChatResponse(_tool_message(save), [save], "tool_calls"),
        ChatResponse(ChatMessage.assistant("Saved it."), [], "stop"),
    ])
    agent = Agent(workspace=tmp_path, provider=provider)

    def save_copper(path):
        Path(path).write_text("Cu")
        return {"saved_to": path}

    skill = Skill("copper", "copper", [
        FunctionDef("build_copper", "Build copper", {"type": "object", "properties": {}}, lambda: {"formula": "Cu"}),
        FunctionDef(
            "save_copper",
            "Save copper",
            {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            save_copper,
        ),
    ])
    agent.skill_manager.register(skill)
    agent.skill_manager.load("copper")

    agent.run("build fcc copper")
    result = agent.run("save it")

    replay = provider.calls[2]
    assert [message.role for message in replay] == [
        "system", "user", "assistant", "tool", "assistant", "user"
    ]
    assert replay[2].tool_calls[0]["function"]["name"] == "build_copper"
    assert '"formula": "Cu"' in replay[3].content
    assert result.artifacts == (str(tmp_path / "copper.cif"),)


def test_import_and_agent_construction_do_not_warn_but_engine_does(tmp_path):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from matsimpy.ai import Agent, AIEngine

        Agent(
            workspace=tmp_path / "agent",
            provider=FakeProvider([ChatResponse(ChatMessage.assistant("ok"), [], "stop")]),
        )
    assert not [item for item in caught if issubclass(item.category, DeprecationWarning)]

    with pytest.warns(DeprecationWarning, match="Agent"):
        AIEngine(api_key="unused", workspace_path=tmp_path / "engine")


def test_engine_chat_delegates_to_public_agent(tmp_path, monkeypatch):
    from matsimpy.ai import AIEngine, AgentResult

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    expected = AgentResult(
        response="delegated",
        status="success",
        tools=(),
        artifacts=(),
        trace_id=7,
        usage={},
        evolution_candidates=(),
    )
    calls = []

    def run(text):
        calls.append(text)
        return expected

    monkeypatch.setattr(engine.agent, "run", run)

    assert engine.chat("hello") == "delegated"
    assert calls == ["hello"]


def test_engine_has_no_retired_duplicate_execution_methods():
    from matsimpy.ai.engine import AIEngine

    assert not hasattr(AIEngine, "_chat_loop")
    assert not hasattr(AIEngine, "_learn")
    assert not hasattr(AIEngine, "_auto_save_skill")


def test_engine_construction_does_not_leave_active_executor(tmp_path):
    from matsimpy.ai.engine import AIEngine
    from matsimpy.ai.executor import _active_executor

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        AIEngine(api_key="unused", workspace_path=tmp_path)

    assert _active_executor.get() is None


def test_repl_workspace_switch_keeps_relative_commands_in_new_workspace(
    tmp_path, monkeypatch
):
    from matsimpy.ai.engine import AIEngine

    original_cwd = Path.cwd()
    old = tmp_path / "old"
    new = tmp_path / "new"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        engine = AIEngine(api_key="unused", workspace_path=old)
    commands = iter([f"/workspace {new}", "/save conversation.json"])

    def fake_input(_prompt):
        try:
            return next(commands)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)
    try:
        engine.repl()
        assert (new / "conversation.json").exists()
    finally:
        os.chdir(original_cwd)
