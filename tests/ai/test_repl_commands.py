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

    def reject(self, name):
        self.calls.append(("reject", name))

    def rollback(self, name):
        self.calls.append(("rollback", name))


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
        ("/approve copper-flow", "approve", ("approve", "copper-flow")),
        ("/approve-skill copper-flow", "approve", ("approve", "copper-flow")),
        ("/reject copper-flow", "reject", ("reject", "copper-flow")),
        ("/rollback copper-flow", "rollback", ("rollback", "copper-flow")),
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
        ("/approve", "/approve <name>"),
        ("/reject", "/reject <name>"),
        ("/rollback", "/rollback <name>"),
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
    assert repl.execute("/reject-skill copper-flow").ok is True


def test_skills_exact_name_returns_detail_but_non_exact_uses_search(
    controller, capsys
):
    from matsimpy.ai.engine import AIEngine

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

    AIEngine._render_command_result(exact)
    rendered = capsys.readouterr().out
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


def test_real_evolution_manager_rollback_is_structured_unavailable(controller):
    repl, session, _ = controller
    real = ReplController(session)

    result = real.execute("/rollback copper-flow")

    assert result.kind == "rollback"
    assert result.ok is False
    assert "not available" in result.display_hint


def test_engine_commands_use_authoritative_agent_session(tmp_path, capsys):
    from matsimpy.ai.engine import AIEngine

    engine = AIEngine(api_key="unused", workspace_path=tmp_path)

    engine._handle_command("/new")
    conversation_id = engine.agent.session.conversation_id
    engine._handle_command("/sessions")
    output = capsys.readouterr().out

    assert conversation_id is not None
    assert engine.repl_controller.session is engine.agent.session
    assert f"Started session {conversation_id}." in output
    assert f"{conversation_id}: engine" in output


def test_engine_resume_rebuilds_compatibility_conversation_from_session_branch(
    tmp_path, capsys
):
    from matsimpy.ai.engine import AIEngine

    class Provider:
        model = "fake"

        def __init__(self):
            self.responses = ["first answer", "second answer"]

        def chat(self, messages, tools=None, tool_choice="auto"):
            return ChatResponse(
                ChatMessage.assistant(self.responses.pop(0)), [], "stop"
            )

    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.agent.provider = engine.runtime.provider = Provider()
    engine.chat("first question")
    conversation_id = engine.agent.session.conversation_id
    engine._handle_command("/new")
    engine.chat("second question")

    engine._handle_command(f"/resume {conversation_id}")

    assert [(item.role, item.content) for item in engine.conversation] == [
        ("system", engine.runtime._initial_messages()[0].content),
        ("user", "first question"),
        ("assistant", "first answer"),
    ]
    capsys.readouterr()
