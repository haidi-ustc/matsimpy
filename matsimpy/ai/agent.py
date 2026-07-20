"""Simple public Python facade for the MatSimPy agent runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .conversation import ChatMessage
from .memory import AgentMemory
from .provider import DeepSeekProvider
from .providers import ChatProvider
from .runtime import AgentRuntime, RUNTIME_SYSTEM_PROMPT, TaskResult
from .session import AgentSession
from .session_store import SessionStore, SkillVersion
from .skill import SkillManager
from .evolution import EvolutionManager
from .workspace import Workspace


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
        evolution: EvolutionManager | None = None,
    ) -> None:
        self.skill_manager = skill_manager or SkillManager()
        self.memory = memory or AgentMemory()
        self.provider = provider or DeepSeekProvider()
        self.system_prompt = system_prompt
        self.verbose_hook = verbose_hook
        self.source = source
        self._evolution = evolution
        self._workspace_path = Workspace(workspace).path
        self._create_session()

    def _create_session(self) -> None:
        store = self._evolution.store if self._evolution is not None else SessionStore(
            self._workspace_path / "ai-state.db" if self._workspace_path else None
        )
        runtime = AgentRuntime(
            provider=self.provider,
            skill_manager=self.skill_manager,
            session_store=store,
            memory=self.memory,
            workspace_path=self._workspace_path,
            source=self.source,
            system_prompt=self.system_prompt,
            verbose_hook=self.verbose_hook,
        )
        manager = self._evolution or EvolutionManager(
            store,
            user_skill_root=runtime.workspace.path / "skills",
            available_tools=self._tool_definitions(),
            replay=self._replay_trace_evidence,
        )
        self._evolution = manager
        self.session = AgentSession(lambda: runtime, store, evolution=manager)

    @property
    def evolution(self) -> EvolutionManager:
        assert self._evolution is not None
        definitions = self._tool_definitions()
        self._evolution.set_tool_catalog(definitions)
        return self._evolution

    @property
    def runtime(self) -> AgentRuntime:
        return self.session.runtime

    @property
    def workspace(self):
        return self.runtime.workspace

    def run(
        self,
        text: str,
    ) -> AgentResult:
        """Run one turn and return normalized runtime evidence."""
        turn = self.session.run(text)
        result = turn.result
        assert result is not None
        return self._normalize(result)

    def add_context(self, message: ChatMessage) -> None:
        """Add explicit context to subsequent conversation turns."""
        self.session.add_context(message)

    def conversation_messages(self) -> list[ChatMessage]:
        """Rebuild the public conversation view from the active session branch."""
        return [*self.runtime._initial_messages(), *self.session.active_messages()]

    def switch_workspace(self, workspace: str | Path) -> None:
        """Move future tasks and durable state to another workspace."""
        self.provider = self.runtime.provider
        self.skill_manager = self.runtime.skill_manager
        self.session.session_store.close()
        self._evolution = None
        self._workspace_path = Path(workspace).expanduser().resolve()
        self._create_session()

    def review_evolution(
        self, candidate: int | str | None = None
    ) -> Mapping[str, Any] | list[Mapping[str, Any]]:
        """Evaluate one candidate, or list all candidates awaiting review."""
        self.session.evolution = self.evolution
        return self.session.review_evolution(candidate)

    def approve_skill(self, version_id: int) -> Mapping[str, Any]:
        """Approve an evaluated version and make it discoverable."""
        definitions = self._tool_definitions()
        version = self.evolution.approve(version_id)
        assert version is not None
        self._register_approved_skill(version, definitions)
        return self._version_record(version)

    def reject_skill(self, version_id: int) -> Mapping[str, Any]:
        version = self.evolution.reject(version_id)
        assert version is not None
        return self._version_record(version)

    def rollback_skill(self, version_id: int) -> Mapping[str, Any]:
        definitions = self._tool_definitions()
        version = self.evolution.rollback(version_id)
        self._register_approved_skill(version, definitions)
        return self._version_record(version)

    # Data-only lifecycle protocol used by ReplController.  The explicit
    # ``*_skill`` names remain the preferred public Python API.
    def review(self, candidate: int | str | None = None):
        return self.review_evolution(candidate)

    def approve(self, version_id: int) -> Mapping[str, Any]:
        return self.approve_skill(version_id)

    def reject(self, version_id: int) -> Mapping[str, Any]:
        return self.reject_skill(version_id)

    def rollback(self, version_id: int) -> Mapping[str, Any]:
        return self.rollback_skill(version_id)

    def _tool_definitions(self) -> dict[str, Any]:
        return self.skill_manager.function_definitions()

    def _replay_trace_evidence(self, version: SkillVersion, context) -> Mapping[str, Any]:
        placeholders = ",".join("?" for _ in version.source_trace_ids)
        rows = self.runtime.session_store.conn.execute(
            f"SELECT id, session_id, validation_status FROM task_traces "
            f"WHERE id IN ({placeholders}) ORDER BY id",
            version.source_trace_ids,
        ).fetchall()
        traces_valid = len(rows) == len(version.source_trace_ids) and all(
            row["validation_status"] == "success" for row in rows
        )
        results = []
        for row in rows:
            calls = self.runtime.session_store.conn.execute(
                "SELECT tool_name, arguments_json FROM tool_calls "
                "WHERE session_id = ? AND status = 'success' ORDER BY id",
                (row["session_id"],),
            ).fetchall()
            for call in calls:
                if call["tool_name"] not in version.allowed_tools:
                    continue
                arguments = json.loads(call["arguments_json"] or "{}")
                outcome = context.execute(call["tool_name"], arguments)
                results.append({"tool": call["tool_name"], "result": outcome})
        passed = traces_valid and bool(results) and all(
            "error" not in item["result"] for item in results
        )
        return {
            "passed": passed,
            "source_trace_ids": list(version.source_trace_ids),
            "replayed_tools": [item["tool"] for item in results],
        }

    def _register_approved_skill(
        self,
        version: SkillVersion,
        definitions: Mapping[str, Any] | None = None,
    ) -> None:
        from .skill import Skill

        definitions = definitions or self._tool_definitions()
        missing = [name for name in version.allowed_tools if name not in definitions]
        if missing:
            raise RuntimeError(
                "approved skill has unresolved live tools: " + ", ".join(missing)
            )
        functions = [definitions[name] for name in version.allowed_tools]
        skill = Skill(version.name, version.description, functions)
        skill.keywords = [version.name]
        self.skill_manager.register(skill)

    @staticmethod
    def _version_record(version: SkillVersion) -> Mapping[str, Any]:
        return {
            "id": version.id,
            "version_id": version.id,
            "name": version.name,
            "version": version.version,
            "description": version.description,
            "body": version.body,
            "allowed_tools": list(version.allowed_tools),
            "source_trace_ids": list(version.source_trace_ids),
            "content_hash": version.content_hash,
            "parent_version_id": version.parent_version_id,
            "rollback_of_version_id": version.rollback_of_version_id,
            "diff": version.diff,
            "status": version.status,
            "deterministic_pass": version.deterministic_pass,
            "deterministic_result": (
                dict(version.deterministic_result)
                if version.deterministic_result is not None
                else None
            ),
            "judge_result": (
                dict(version.judge_result) if version.judge_result is not None else None
            ),
            "evaluated_hash": version.evaluated_hash,
            "approvable": version.approvable,
            "created_at": version.created_at,
            "evaluated_at": version.evaluated_at,
            "approved_at": version.approved_at,
        }

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
