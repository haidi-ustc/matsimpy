"""Simple public Python facade for the MatSimPy agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .conversation import ChatMessage
from .memory import AgentMemory
from .provider import DeepSeekProvider
from .providers import ChatProvider
from .runtime import AgentRuntime, RUNTIME_SYSTEM_PROMPT, TaskResult
from .session import AgentSession
from .session_store import SessionStore
from .skill import SkillManager


@dataclass(frozen=True)
class AgentResult:
    """Stable, structured result returned by :meth:`Agent.run`."""

    response: str
    status: str
    tools: tuple[str, ...]
    artifacts: tuple[str, ...]
    trace_id: int | None
    usage: Mapping[str, Any]
    evolution_candidates: tuple[Mapping[str, Any], ...]


class Agent:
    """Run stateful MatSimPy tasks from Python with one small interface."""

    def __init__(
        self,
        workspace: str | Path | None = None,
        provider: ChatProvider | None = None,
        *,
        skill_manager: SkillManager | None = None,
        memory: AgentMemory | None = None,
        system_prompt: str = RUNTIME_SYSTEM_PROMPT,
        verbose_hook: Callable[[str], None] | None = None,
        source: str = "python",
    ) -> None:
        self.skill_manager = skill_manager or SkillManager()
        self.memory = memory or AgentMemory()
        self.provider = provider or DeepSeekProvider()
        self.system_prompt = system_prompt
        self.verbose_hook = verbose_hook
        self.source = source
        self.extra_messages: list[ChatMessage] | None = None
        self._workspace_path = Path(workspace).expanduser().resolve() if workspace else None
        self._create_session()

    def _create_session(self) -> None:
        runtime = AgentRuntime(
            provider=self.provider,
            skill_manager=self.skill_manager,
            session_store=SessionStore(
                self._workspace_path / "ai-state.db" if self._workspace_path else None
            ),
            memory=self.memory,
            workspace_path=self._workspace_path,
            source=self.source,
            system_prompt=self.system_prompt,
            verbose_hook=self.verbose_hook,
        )
        store = runtime.session_store
        self.session = AgentSession(lambda: runtime, store)

    @property
    def runtime(self) -> AgentRuntime:
        return self.session.runtime

    @property
    def workspace(self):
        return self.runtime.workspace

    def run(
        self,
        text: str,
        *,
        extra_messages: list[ChatMessage] | None = None,
    ) -> AgentResult:
        """Run one turn and return normalized runtime evidence."""
        context = extra_messages if extra_messages is not None else self.extra_messages
        self.extra_messages = None
        turn = self.session.run(text, extra_messages=context)
        result = turn.result
        assert result is not None
        return self._normalize(result)

    def switch_workspace(self, workspace: str | Path) -> None:
        """Move future tasks and durable state to another workspace."""
        self.provider = self.runtime.provider
        self.skill_manager = self.runtime.skill_manager
        self.session.session_store.close()
        self._workspace_path = Path(workspace).expanduser().resolve()
        self._create_session()

    def _normalize(self, result: TaskResult) -> AgentResult:
        candidates = (result.draft_skill,) if result.draft_skill else ()
        return AgentResult(
            response=result.final_response,
            status=result.status,
            tools=tuple(record["name"] for record in result.tool_calls),
            artifacts=self._artifacts(result.tool_calls),
            trace_id=result.trace_id,
            usage={},
            evolution_candidates=candidates,
        )

    def _artifacts(self, tool_calls: list[dict]) -> tuple[str, ...]:
        found: list[str] = []
        for record in tool_calls:
            value = record.get("result")
            if not isinstance(value, dict):
                continue
            for key in ("saved_to", "path", "output_path", "filename"):
                candidate = value.get(key)
                if not isinstance(candidate, str):
                    continue
                path = self.workspace.resolve(candidate).resolve()
                if path.exists():
                    rendered = str(path)
                    if rendered not in found:
                        found.append(rendered)
        return tuple(found)


__all__ = ["Agent", "AgentResult"]
