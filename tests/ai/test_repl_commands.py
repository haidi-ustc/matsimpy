"""Tests for data-returning REPL command dispatch."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from matsimpy.ai.repl import ReplController
from matsimpy.ai.conversation import ChatMessage, ChatResponse


@dataclass
class FakeTurn:
    attempt_id: int = 11
    user_request: str = "build copper"
    final_response: str = "done"
    state: str = "succeeded"


class FakeStore:
    def list_conversations(self):
        return [{"id": 4, "source": "repl"}]

    def list_skill_drafts(self, status=None):
        return [{"name": "copper-flow", "status": status or "draft"}]


class FakeSession:
    def __init__(self):
        self.session_store = FakeStore()
        self.conversation_id = 4
        self.turns = [FakeTurn()]
        self.calls = []

    def new(self):
        self.calls.append(("new",))
        self.conversation_id = 5
        self.turns = []
        return 5

    def resume(self, conversation_id):
        self.calls.append(("resume", conversation_id))
        self.conversation_id = conversation_id
        return self

    def retry(self):
        self.calls.append(("retry",))
        return FakeTurn(attempt_id=12)

    def undo(self):
        self.calls.append(("undo",))
        return FakeTurn()


class FakeSkillLibrary:
    def discover(self):
        return [
            {"name": "crystals", "description": "Build crystals", "source": "packaged"},
            {"name": "molecules", "description": "Build molecules", "source": "user"},
        ]

    def search(self, query):
        return [item for item in self.discover() if query in item["name"]]

    def detail(self, name):
        if name == "generated-flow":
            return {
                "name": name,
                "description": "Saved workflow",
                "source": "generated",
                "mode": "auto_choice",
                "body_preview": "Use tool A then B.",
            }
        if name != "crystals":
            return None
        return {
            "name": "crystals",
            "description": "Build crystals",
            "source": "builtin",
            "loaded": True,
            "keywords": ["crystal"],
            "functions": [
                {
                    "name": "make_crystal",
                    "description": "Make one",
                    "schema": {"type": "object"},
                    "help": "Detailed help",
                }
            ],
        }


class FakeEvolution:
    def __init__(self):
        self.calls = []

    def approve(self, name):
        self.calls.append(("approve", name))
        return {"id": name, "status": "approved", "allowed_tools": ["step"]}

    def reject(self, name):
        self.calls.append(("reject", name))
        return {"id": name, "status": "rejected", "allowed_tools": ["step"]}

    def rollback(self, version_id):
        self.calls.append(("rollback", version_id))
        return {"version": version_id + 1}

    def review(self, candidate=None):
        self.calls.append(("review", candidate))
        return [{
            "version_id": 3,
            "rationale": "validated recovery",
            "source_trace_ids": [9],
            "deterministic_evidence": {"passed": True},
            "judge_evidence": None,
            "content_diff": "--- v1\n+++ draft\n",
        }]


@pytest.fixture
def controller():
    session = FakeSession()
    evolution = FakeEvolution()
    controller = ReplController(
        session,
        skill_library=FakeSkillLibrary(),
        evolution=evolution,
        usage_getter=lambda: {"prompt_tokens": 7},
        trace_getter=lambda: {"trace_id": 9, "status": "success"},
        skill_loader=lambda name: {"name": name, "loaded": True},
    )
    return controller, session, evolution


@pytest.mark.parametrize(
    ("command", "kind", "expected_call"),
    [
        ("/new", "new", ("new",)),
        ("/resume 8", "resume", ("resume", 8)),
        ("/retry", "retry", ("retry",)),
        ("/undo", "undo", ("undo",)),
        ("/approve 3", "approve", ("approve", 3)),
        ("/approve-skill 3", "approve", ("approve", 3)),
        ("/reject 3", "reject", ("reject", 3)),
        ("/rollback 7", "rollback", ("rollback", 7)),
        ("/evolve review", "evolve-review", ("review", None)),
    ],
)
def test_mutating_commands_delegate_to_services(controller, command, kind, expected_call):
    repl, session, evolution = controller

    result = repl.execute(command)

    assert result.ok is True
    assert result.kind == kind
    calls = session.calls + evolution.calls
    assert expected_call in calls


@pytest.mark.parametrize(
    ("command", "kind", "key"),
    [
        ("/sessions", "sessions", "sessions"),
        ("/skills", "skills", "skills"),
        ("/skills crystal", "skills", "skills"),
        ("/drafts", "drafts", "drafts"),
        ("/trace", "trace", "trace"),
        ("/usage", "usage", "usage"),
    ],
)
def test_inspection_commands_return_data_without_printing(
    controller, capsys, command, kind, key
):
    repl, _, _ = controller

    result = repl.execute(command)

    assert result.ok is True
    assert result.kind == kind
    assert key in result.data
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("command", "usage"),
    [
        ("/resume", "/resume <session_id>"),
        ("/resume nope", "/resume <session_id>"),
        ("/approve", "/approve <version-id>"),
        ("/approve nope", "positive numeric version ID"),
        ("/reject", "/reject <version-id>"),
        ("/rollback", "/rollback <version-id>"),
        ("/evolve", "/evolve review [candidate]"),
        ("/unknown", "Unknown command"),
        ("not-a-command", "Commands must start"),
    ],
)
def test_invalid_usage_is_structured(controller, command, usage):
    repl, _, _ = controller

    result = repl.execute(command)

    assert result.ok is False
    assert usage in result.display_hint


def test_aliases_completion_and_command_names(controller):
    repl, _, _ = controller

    assert repl.execute("/q").exit_requested is True
    assert repl.execute("/quit").exit_requested is True
    assert repl.execute("/exit").exit_requested is True
    assert repl.execute("/load-skill crystals").data["skill"]["loaded"] is True
    assert "/approve" in repl.command_names()
    assert repl.complete("/res") == ("/resume",)
    assert "/approve-skill" in repl.complete("/app")
    assert repl.execute("/reject-skill 3").ok is True


def test_help_is_structured_complete_and_offline(controller, capsys):
    repl, session, evolution = controller

    result = repl.execute("/help")

    assert result.ok is True
    assert result.kind == "help"
    assert "/help" in repl.command_names()
    assert repl.complete("/he") == ("/help",)
    assert set(result.data["aliases"]) == {
        "/q",
        "/exit",
        "/approve-skill",
        "/reject-skill",
    }
    commands = {item["command"] for item in result.data["commands"]}
    assert set(repl._handlers) <= commands
    assert result.data["keys"] == {
        "submit": "Enter",
        "newline": "Esc+Enter",
        "cancel": "Ctrl+C",
    }
    assert result.data["lifecycle"] == [
        {"stage": "discover", "command": "/skills [query]"},
        {"stage": "load", "command": "/load-skill <name>"},
        {"stage": "review", "command": "/evolve review [version-id]"},
        {"stage": "approve", "command": "/approve <version-id>"},
    ]
    assert {item["command"] for item in result.data["examples"]} >= {
        "/skills crystal",
        "/load-skill <name>",
        "/evolve review <version-id>",
        "/approve <version-id>",
    }
    assert "discover" in result.display_hint.casefold()
    assert "approve" in result.display_hint.casefold()
    assert session.calls == []
    assert evolution.calls == []
    assert capsys.readouterr().out == ""


def test_lifecycle_commands_return_complete_service_records(controller):
    repl, _, _ = controller

    approved = repl.execute("/approve 3")
    rejected = repl.execute("/reject 4")

    assert approved.data["version"] == {
        "id": 3,
        "status": "approved",
        "allowed_tools": ["step"],
    }
    assert rejected.data["version"] == {
        "id": 4,
        "status": "rejected",
        "allowed_tools": ["step"],
    }


def test_evolve_review_exposes_all_approval_evidence(controller):
    repl, _, _ = controller

    result = repl.execute("/evolve review copper-flow")

    assert result.ok is True
    candidate = result.data["candidates"][0]
    assert candidate["rationale"] == "validated recovery"
    assert candidate["source_trace_ids"] == [9]
    assert candidate["deterministic_evidence"] == {"passed": True}
    assert candidate["judge_evidence"] is None
    assert candidate["content_diff"].startswith("---")


def test_skills_exact_name_returns_detail_but_non_exact_uses_search(
    controller, capsys
):
    from matsimpy.ai.terminal import format_command_result

    repl, _, _ = controller

    exact = repl.execute("/skills crystals")
    search = repl.execute("/skills crystal")

    assert exact.data["skill"]["loaded"] is True
    assert exact.data["skill"]["functions"][0] == {
        "name": "make_crystal",
        "description": "Make one",
        "schema": {"type": "object"},
        "help": "Detailed help",
    }
    assert "skills" not in exact.data
    assert [item["name"] for item in search.data["skills"]] == ["crystals"]

    rendered = format_command_result(exact)
    assert "make_crystal: Make one" in rendered
    assert 'Schema: {"type": "object"}' in rendered
    assert "Help: Detailed help" in rendered

    generated = repl.execute("/skills generated-flow").data["skill"]
    assert generated == {
        "name": "generated-flow",
        "description": "Saved workflow",
        "source": "generated",
        "mode": "auto_choice",
        "body_preview": "Use tool A then B.",
    }


def test_real_evolution_manager_rollback_rejects_non_numeric_id(controller):
    repl, session, _ = controller
    real = ReplController(session)

    result = real.execute("/rollback copper-flow")

    assert result.kind == "rollback"
    assert result.ok is False
    assert "numeric version ID" in result.display_hint


def test_agent_controller_uses_authoritative_agent_session(tmp_path):
    from matsimpy.ai import Agent, DeepSeekProvider
    from matsimpy.ai.terminal import format_command_result

    agent = Agent(workspace=tmp_path, provider=DeepSeekProvider("unused"), source="cli")
    repl = ReplController.for_agent(agent)

    repl.execute("/new")
    conversation_id = agent.session.conversation_id
    output = format_command_result(repl.execute("/sessions"))

    assert conversation_id is not None
    assert repl.session is agent.session
    assert f"{conversation_id}: cli" in output


def test_agent_controller_uses_agent_backed_evolution_lifecycle(tmp_path, monkeypatch):
    from matsimpy.ai import Agent, DeepSeekProvider

    agent = Agent(workspace=tmp_path, provider=DeepSeekProvider("unused"))
    repl = ReplController.for_agent(agent)
    calls = []

    def approve(version_id):
        calls.append(version_id)
        return {"version_id": version_id, "status": "approved"}

    monkeypatch.setattr(agent, "approve", approve)

    result = repl.execute("/approve 7")

    assert result.ok is True
    assert result.data["version"]["status"] == "approved"
    assert calls == [7]
    assert repl.evolution is agent


def test_agent_resume_rebuilds_conversation_from_session_branch(tmp_path):
    from matsimpy.ai import Agent

    class Provider:
        model = "fake"

        def __init__(self):
            self.responses = ["first answer", "second answer"]

        def chat(self, messages, tools=None, tool_choice="auto"):
            return ChatResponse(
                ChatMessage.assistant(self.responses.pop(0)), [], "stop"
            )

    agent = Agent(workspace=tmp_path, provider=Provider())
    repl = ReplController.for_agent(agent)
    agent.run("first question")
    conversation_id = agent.session.conversation_id
    repl.execute("/new")
    agent.run("second question")

    repl.execute(f"/resume {conversation_id}")

    assert [(item.role, item.content) for item in agent.conversation_messages()] == [
        ("system", agent.runtime._initial_messages()[0].content),
        ("user", "first question"),
        ("assistant", "first answer"),
    ]


def test_agent_only_commands(tmp_path, monkeypatch):
    from matsimpy.ai import Agent, DeepSeekProvider
    from matsimpy.ai.skill import FunctionDef, Skill

    monkeypatch.chdir(tmp_path)
    agent = Agent(workspace=tmp_path / "ws", provider=DeepSeekProvider("unused"))
    agent.skill_manager.register(Skill("tools-x", "x", [FunctionDef("f", "f", {"type": "object"}, lambda: 1)]))
    repl = ReplController.for_agent(agent)

    assert "/workspace" in repl.command_names()
    assert "/workspace" not in ReplController(agent.session).command_names()
    assert repl.execute("/load tools-x").ok and "tools-x" in agent.skill_manager._active
    assert repl.execute("/unload tools-x").ok and "tools-x" not in agent.skill_manager._active
    assert repl.execute("/model no-such-model").ok is False
    assert repl.execute("/memory").data["files"]
    saved = repl.execute("/save out.json")
    assert (tmp_path / "out.json").exists() and saved.data["path"] == "out.json"
    help_text = repl.execute("/help").display_hint
    assert "/workspace" in help_text and "/save" in help_text
