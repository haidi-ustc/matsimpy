"""Public Agent facade."""

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


def test_skill_manager_exposes_live_function_catalog():
    from matsimpy.ai.skill import SkillManager

    definition = FunctionDef(
        "step", "step", {"type": "object", "properties": {}}, lambda: None
    )
    manager = SkillManager({"workflow": Skill("workflow", "workflow", [definition])})

    assert manager.function_definitions() == {"step": definition}
    assert manager.function_definitions(active_only=True) == {}
    manager.load("workflow")
    assert manager.function_definitions(active_only=True) == {"step": definition}


def test_agent_evolution_candidate_requires_review_before_activation(tmp_path):
    from matsimpy.ai import Agent

    calls = [ToolCall(str(index), f"step_{index}", {}) for index in range(1, 4)]
    responses = []
    for call in calls:
        responses.append(ChatResponse(_tool_message(call), [call], "tool_calls"))
    responses.append(
        ChatResponse(ChatMessage.assistant("Workflow complete."), [], "stop")
    )
    agent = Agent(workspace=tmp_path, provider=FakeProvider(responses))
    skill = Skill(
        "workflow",
        "Three step workflow",
        [
            FunctionDef(
                call.name,
                call.name,
                {"type": "object", "properties": {}},
                lambda: {"ok": True},
            )
            for call in calls
        ],
    )
    skill.keywords = ["workflow"]
    agent.skill_manager.register(skill)
    agent.skill_manager.load(skill.name)

    result = agent.run("run this reusable workflow")

    assert len(result.evolution_candidates) == 1
    assert result.evolution_candidates[0]["status"] == "draft"
    assert not (tmp_path / "skills").exists()

    review = agent.review_evolution(result.evolution_candidates[0]["name"])
    assert review["rationale"] == "nontrivial validated workflow"
    assert review["source_trace_ids"] == [result.trace_id]
    assert review["deterministic_evidence"]["passed"] is True
    assert review["judge_evidence"] is None
    assert "content_diff" in review
    assert review["status"] == "evaluated"

    approved = agent.approve_skill(review["version_id"])
    assert approved["status"] == "approved"
    assert "run-this-reusable-workflow" in {
        item["name"] for item in agent.skill_manager.list_skills()
    }


def test_agent_skill_revision_remains_inactive_until_separate_approval(tmp_path):
    from matsimpy.ai import Agent

    agent = Agent(
        workspace=tmp_path,
        provider=FakeProvider([ChatResponse(ChatMessage.assistant("ok"), [], "stop")]),
    )
    trace_id = agent.run("answer").trace_id
    assert trace_id is not None
    agent.skill_manager.register(
        Skill(
            "workflow",
            "workflow",
            [
                FunctionDef(
                    "step",
                    "step",
                    {"type": "object", "properties": {}},
                    lambda: {"ok": True},
                )
            ],
        )
    )
    agent.skill_manager.load("workflow")
    agent.evolution.replay = lambda version, context: {"passed": True}
    first = agent.evolution.draft_skill(
        "revision-flow", "Revision flow", "Run `step`.", ["step"], [trace_id]
    )
    evaluated = agent.evolution.evaluate(first.id)
    approved = agent.approve_skill(evaluated.id)

    revision = agent.evolution.draft_revision(
        approved["version_id"], body="Run `step` twice.", source_trace_ids=[trace_id]
    )

    assert revision.status == "draft"
    assert (
        agent.evolution.store.get_active_skill_version("revision-flow").id
        == approved["version_id"]
    )


def test_agent_approval_rejects_catalog_change_before_materialization(tmp_path):
    from matsimpy.ai import Agent, SkillEvolutionError

    agent = Agent(
        workspace=tmp_path,
        provider=FakeProvider([ChatResponse(ChatMessage.assistant("ok"), [], "stop")]),
    )
    trace_id = agent.run("answer").trace_id
    definition = FunctionDef(
        "step", "step", {"type": "object", "properties": {}}, lambda: {"ok": True}
    )
    skill = Skill("workflow", "workflow", [definition])
    agent.skill_manager.register(skill)
    agent.skill_manager.load("workflow")
    agent.evolution.replay = lambda version, context: {"passed": True}
    draft = agent.evolution.draft_skill(
        "catalog-race", "Catalog race", "Run `step`.", ["step"], [trace_id]
    )
    reviewed = agent.review_evolution(draft.id)
    agent.skill_manager._skills["workflow"].functions.clear()

    with pytest.raises(SkillEvolutionError, match="current live FunctionDef"):
        agent.approve_skill(reviewed["version_id"])

    assert not (tmp_path / "skills" / "catalog-race" / "SKILL.md").exists()
    assert agent.evolution.store.get_skill_version(draft.id).status == "evaluated"


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


def test_import_and_agent_construction_do_not_warn(tmp_path):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from matsimpy.ai import Agent

        Agent(
            workspace=tmp_path / "agent",
            provider=FakeProvider([ChatResponse(ChatMessage.assistant("ok"), [], "stop")]),
        )
    assert not [item for item in caught if issubclass(item.category, DeprecationWarning)]


def test_aiengine_was_removed():
    import matsimpy.ai as ai

    assert not hasattr(ai, "AIEngine")
    with pytest.raises(ImportError):
        import matsimpy.ai.engine  # noqa: F401


def test_agent_construction_does_not_leave_active_executor(tmp_path):
    from matsimpy.ai import Agent, DeepSeekProvider
    from matsimpy.ai.executor import _active_executor

    Agent(workspace=tmp_path, provider=DeepSeekProvider("unused"))

    assert _active_executor.get() is None


def test_repl_workspace_switch_keeps_relative_commands_in_new_workspace(tmp_path):
    from matsimpy.ai import Agent, DeepSeekProvider, PlainTerminal, ReplController

    original_cwd = Path.cwd()
    old = tmp_path / "old"
    new = tmp_path / "new"
    agent = Agent(workspace=old, provider=DeepSeekProvider("unused"))
    commands = iter([f"/workspace {new}", "/save conversation.json"])

    def fake_input(_prompt):
        try:
            return next(commands)
        except StopIteration:
            raise EOFError

    controller = ReplController.for_agent(agent)
    try:
        agent.workspace.enter()
        PlainTerminal(controller, input_reader=fake_input, output_writer=lambda _: None).run()
        assert (new / "conversation.json").exists()
        assert controller.session is agent.session  # rebound to the new workspace's store
    finally:
        os.chdir(original_cwd)
