"""Durable conversation coordinator shared by REPL and Python clients."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from .conversation import ChatMessage
from .runtime import AgentRuntime, TaskResult
from .session_store import AttemptRecord, SessionStore


@dataclass(frozen=True)
class SessionTurn:
    """One active conversational turn backed by an immutable audit attempt."""

    conversation_id: int
    attempt_id: int
    parent_attempt_id: int | None
    state: str
    user_request: str
    final_response: str
    result: TaskResult | None = None


class AgentSession:
    """Coordinate active context, durable attempts, and runtime execution."""

    def __init__(
        self,
        runtime_factory: Callable[[], AgentRuntime],
        session_store: SessionStore,
    ) -> None:
        self._runtime_factory = runtime_factory
        self.session_store = session_store
        self.runtime = runtime_factory()
        # One coordinator owns one audit boundary.  Runtime traces and attempt
        # links must share a database for their foreign key to remain valid.
        self.runtime.session_store = session_store
        self.conversation_id: int | None = None
        self.turns: list[SessionTurn] = []
        self._replacement_parent_id: int | None = None

    def new(self) -> int:
        """Start a new durable conversation and clear active context."""
        conversation = self.session_store.create_conversation(
            source=self.runtime.source,
            workspace=str(self.runtime.workspace.path),
            model=getattr(self.runtime.provider, "model", "unknown"),
            provider=type(self.runtime.provider).__name__,
        )
        self.conversation_id = conversation.id
        self.turns = []
        self._replacement_parent_id = None
        return conversation.id

    def resume(self, conversation_id: int) -> AgentSession:
        """Resume a persisted conversation, reconstructing its active branch."""
        _conversation, attempts = self.session_store.load_conversation(conversation_id)
        self.conversation_id = conversation_id
        self.turns = self._active_branch(attempts)
        self._replacement_parent_id = None
        return self

    def run(self, text: str) -> SessionTurn:
        """Execute and append one conversational turn."""
        parent_id = self._replacement_parent_id
        self._replacement_parent_id = None
        return self._run(
            text,
            parent_attempt_id=parent_id,
            replace_parent=False,
        )

    def retry(self) -> SessionTurn:
        """Retry the active final turn and replace it in active context."""
        if not self.turns:
            raise RuntimeError("no active turn to retry")
        parent = self.turns[-1]
        return self._run(
            parent.user_request,
            parent_attempt_id=parent.attempt_id,
            replace_parent=True,
        )

    def undo(self) -> SessionTurn:
        """Remove the final turn from active context without deleting audit data."""
        if not self.turns:
            raise RuntimeError("no active turn to undo")
        turn = self.turns.pop()
        self._replacement_parent_id = turn.attempt_id
        return turn

    def _run(
        self,
        text: str,
        parent_attempt_id: int | None,
        replace_parent: bool,
    ) -> SessionTurn:
        if self.conversation_id is None:
            self.new()
        assert self.conversation_id is not None
        attempt = self.session_store.start_attempt(
            self.conversation_id,
            text,
            parent_attempt_id=parent_attempt_id,
        )
        context_turns = self.turns[:-1] if replace_parent else self.turns
        context = self._messages_for(context_turns)
        try:
            result = self.runtime.run(text, extra_messages=context)
        except (KeyboardInterrupt, asyncio.CancelledError) as exc:
            self.session_store.mark_attempt_interrupted(
                attempt.id, error=f"{type(exc).__name__}: execution interrupted"
            )
            raise

        state = "succeeded" if result.status == "success" else "failed"
        finished = self.session_store.finish_attempt(
            attempt.id,
            state,
            final_response=result.final_response,
            trace_id=result.trace_id,
            error=None if state == "succeeded" else result.final_response,
        )
        turn = self._turn_from_attempt(finished, result)
        if replace_parent:
            self.turns[-1] = turn
        else:
            self.turns.append(turn)
        return turn

    @staticmethod
    def _messages_for(turns: list[SessionTurn]) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        for turn in turns:
            messages.append(ChatMessage.user(turn.user_request))
            messages.append(ChatMessage.assistant(turn.final_response))
        return messages

    @classmethod
    def _active_branch(cls, attempts: list[AttemptRecord]) -> list[SessionTurn]:
        active: list[SessionTurn] = []
        active_indices: dict[int, int] = {}
        for attempt in attempts:
            if attempt.state not in {"succeeded", "failed"}:
                continue
            turn = cls._turn_from_attempt(attempt)
            parent_index = active_indices.get(attempt.parent_attempt_id or -1)
            if parent_index is not None:
                old = active[parent_index]
                active[parent_index] = turn
                active_indices.pop(old.attempt_id, None)
                active_indices[attempt.id] = parent_index
            else:
                active_indices[attempt.id] = len(active)
                active.append(turn)
        return active

    @staticmethod
    def _turn_from_attempt(
        attempt: AttemptRecord, result: TaskResult | None = None
    ) -> SessionTurn:
        return SessionTurn(
            conversation_id=attempt.conversation_id,
            attempt_id=attempt.id,
            parent_attempt_id=attempt.parent_attempt_id,
            state=attempt.state,
            user_request=attempt.user_request,
            final_response=attempt.final_response or "",
            result=result,
        )


__all__ = ["AgentSession", "SessionTurn"]
