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
