"""Integration tests for durable conversational agent coordination."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from matsimpy.ai.conversation import ChatMessage, ChatResponse
from matsimpy.ai.runtime import AgentRuntime
from matsimpy.ai.session import AgentSession
from matsimpy.ai.session_store import SessionStore
from matsimpy.ai.skill import SkillManager
from matsimpy.ai.workspace import Workspace


class RecordingProvider:
    model = "fake-session-model"

    def __init__(self, responses: list[str | BaseException]):
        self.responses = list(responses)
        self.calls: list[list[ChatMessage]] = []

    def chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(list(messages))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return ChatResponse(ChatMessage.assistant(response), [], "stop")


def runtime_factory(provider, workspace):
    def create():
        return AgentRuntime(
            provider=provider,
            skill_manager=SkillManager({}),
            session_store=SessionStore(workspace / "runtime.db"),
            workspace_path=workspace,
            source="test",
        )

    return create


def test_run_and_restart_resume_restore_active_context(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
    first_provider = RecordingProvider(["first answer", "second answer"])
    session = AgentSession(runtime_factory(first_provider, tmp_path), store)

    first = session.run("first question")
    second = session.run("second question")

    assert first.conversation_id == second.conversation_id
    assert [turn.user_request for turn in session.turns] == [
        "first question",
        "second question",
    ]

    resumed_provider = RecordingProvider(["third answer"])
    resumed = AgentSession(runtime_factory(resumed_provider, tmp_path), store)
    resumed.resume(first.conversation_id)
    third = resumed.run("third question")

    context = resumed_provider.calls[0]
    assert [(message.role, message.content) for message in context[1:]] == [
        ("user", "first question"),
        ("assistant", "first answer"),
        ("user", "second question"),
        ("assistant", "second answer"),
        ("user", "third question"),
    ]
    assert third.final_response == "third answer"


def test_retry_links_audit_attempt_and_replaces_active_turn(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
    provider = RecordingProvider(["bad answer", "better answer"])
    session = AgentSession(runtime_factory(provider, tmp_path), store)
    original = session.run("calculate")

    retried = session.retry()

    _, attempts = store.load_conversation(original.conversation_id)
    assert len(attempts) == 2
    assert attempts[1].parent_attempt_id == attempts[0].id
    assert [turn.attempt_id for turn in session.turns] == [retried.attempt_id]
    assert retried.final_response == "better answer"


def test_undo_changes_context_without_deleting_audit_rows(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
    provider = RecordingProvider(["one", "two", "after undo"])
    session = AgentSession(runtime_factory(provider, tmp_path), store)
    session.run("first")
    session.run("second")

    undone = session.undo()
    replacement = session.run("replacement")

    assert undone.user_request == "second"
    assert [(message.role, message.content) for message in provider.calls[-1][1:]] == [
        ("user", "first"),
        ("assistant", "one"),
        ("user", "replacement"),
    ]
    _, attempts = store.load_conversation(session.conversation_id)
    assert [attempt.user_request for attempt in attempts] == [
        "first",
        "second",
        "replacement",
    ]
    assert attempts[-1].parent_attempt_id == undone.attempt_id

    restarted = AgentSession(
        runtime_factory(RecordingProvider([]), tmp_path), store
    ).resume(session.conversation_id)
    assert [turn.attempt_id for turn in restarted.turns] == [
        attempts[0].id,
        replacement.attempt_id,
    ]


def test_sessions_restore_cwd_and_keep_workspaces_isolated(tmp_path):
    original_cwd = Path.cwd()
    one = tmp_path / "one"
    two = tmp_path / "two"
    provider_one = RecordingProvider(["one"])
    provider_two = RecordingProvider(["two"])
    session_one = AgentSession(
        runtime_factory(provider_one, one), SessionStore(tmp_path / "one.db")
    )
    session_two = AgentSession(
        runtime_factory(provider_two, two), SessionStore(tmp_path / "two.db")
    )

    session_one.run("first")
    assert Path.cwd() == original_cwd
    session_two.run("second")

    assert Path.cwd() == original_cwd
    assert session_one.runtime.workspace.path == one.resolve()
    assert session_two.runtime.workspace.path == two.resolve()


def test_workspace_contexts_restore_the_immediate_callers_directory(tmp_path):
    original_cwd = Path.cwd()
    outer = Workspace(tmp_path / "outer")
    inner = Workspace(tmp_path / "inner")

    with outer.activate():
        assert Path.cwd() == outer.path
        with inner.activate():
            assert Path.cwd() == inner.path
        assert Path.cwd() == outer.path

    assert Path.cwd() == original_cwd


@pytest.mark.parametrize("cancellation", [KeyboardInterrupt(), asyncio.CancelledError()])
def test_cancellation_is_persisted_as_interrupted_and_reraised(tmp_path, cancellation):
    store = SessionStore(tmp_path / "sessions.db")
    provider = RecordingProvider([cancellation])
    session = AgentSession(runtime_factory(provider, tmp_path), store)

    with pytest.raises(type(cancellation)):
        session.run("interrupt me")

    _, attempts = store.load_conversation(session.conversation_id)
    assert attempts[0].state == "interrupted"
    assert "Runtime error" not in (attempts[0].error or "")
    runtime_status = store.conn.execute(
        "SELECT status FROM sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    assert runtime_status == "interrupted"
    assert Path.cwd() == Path(os.getcwd())
