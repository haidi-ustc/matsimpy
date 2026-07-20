"""Offline end-to-end contracts for Agent, sessions, REPL, and evolution."""

from __future__ import annotations

from pathlib import Path

from matsimpy import io
from matsimpy.ai import Agent, ChatMessage, ChatResponse, FunctionDef, Skill, ToolCall
from matsimpy.ai.cli import _register_all_skills
from matsimpy.ai.repl import ReplController
from matsimpy.ai.skill import SkillManager


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


def test_skill_requires_review_then_approval_before_repl_can_use_it(tmp_path):
    agent = Agent(
        workspace=tmp_path,
        provider=ScriptedProvider([ChatResponse(ChatMessage.assistant("ok"), [], "stop")]),
    )
    trace_id = agent.run("record evidence").trace_id
    assert trace_id is not None
    tool = FunctionDef(
        "offline_step", "Offline step", {"type": "object", "properties": {}},
        lambda: {"ok": True},
        skill="seed",
    )
    agent.skill_manager.register(Skill("seed", "Seed", [tool]))
    agent.skill_manager.load("seed")
    agent.evolution.replay = lambda version, context: {"passed": True}
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
    approved = controller.execute(f"/approve {draft.id}")
    assert approved.ok
    assert "offline-flow" in {item["name"] for item in agent.skill_manager.list_skills()}
