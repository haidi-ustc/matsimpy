"""Tests for data-returning REPL command dispatch."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from matsimpy.ai.repl import ReplController


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
