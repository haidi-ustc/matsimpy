"""Data-returning command controller for interactive agent clients."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Callable, Mapping

from .evolution import EvolutionManager
from .session import AgentSession


@dataclass(frozen=True)
class CommandResult:
    """Structured outcome rendered by a terminal or another client."""

    kind: str
    ok: bool = True
    data: Mapping[str, Any] = field(default_factory=dict)
    display_hint: str = ""
    exit_requested: bool = False

class ReplController:
    """Dispatch slash commands without performing terminal I/O."""

    def __init__(
        self,
        session: AgentSession,
        *,
        skill_library: Any | None = None,
        evolution: EvolutionManager | None = None,
        usage_getter: Callable[[], Mapping[str, Any]] | None = None,
        trace_getter: Callable[[], Mapping[str, Any]] | None = None,
        skill_loader: Callable[[str], Any] | None = None,
    ) -> None:
        self.session = session
        self.skill_library = skill_library
        self.evolution = (
            evolution
            or getattr(session, "evolution", None)
            or EvolutionManager(session.session_store)
        )
        self.usage_getter = usage_getter or (lambda: {})
        self.trace_getter = trace_getter or self._runtime_trace
        self.skill_loader = skill_loader
        self._handlers = {
            "/help": self._help,
            "/new": self._new,
            "/sessions": self._sessions,
            "/resume": self._resume,
            "/retry": self._retry,
            "/undo": self._undo,
            "/skills": self._skills,
            "/drafts": self._drafts,
            "/approve": self._approve,
            "/reject": self._reject,
            "/rollback": self._rollback,
            "/evolve": self._evolve,
            "/trace": self._trace,
            "/usage": self._show_usage,
            "/quit": self._quit,
            "/load-skill": self._load_skill,
        }
        self._aliases = {
            "/q": "/quit",
            "/exit": "/quit",
            "/approve-skill": "/approve",
            "/reject-skill": "/reject",
        }

    def execute(self, command: str) -> CommandResult:
        """Parse and execute one slash command."""
        text = command.strip()
        if not text.startswith("/"):
            return self._error("Commands must start with '/'.")
        name, _, arg = text.partition(" ")
        name = self._aliases.get(name.casefold(), name.casefold())
        handler = self._handlers.get(name)
        if handler is None:
            return self._error(f"Unknown command: {name}")
        try:
            return handler(arg.strip())
        except (KeyError, RuntimeError, ValueError) as exc:
            return self._error(str(exc), kind=name.removeprefix("/"))

    def command_names(self) -> tuple[str, ...]:
        """Return canonical command names and supported aliases."""
        return tuple(sorted((*self._handlers, *self._aliases)))

    def complete(self, prefix: str) -> tuple[str, ...]:
        """Return command-name completions for *prefix*."""
        folded = prefix.casefold()
        return tuple(name for name in self.command_names() if name.startswith(folded))

    def _help(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/help")
        descriptions = {
            "/help": "Show this offline command reference.",
            "/new": "Start a new durable conversation.",
            "/sessions": "List saved conversations.",
            "/resume": "Resume a saved conversation: /resume <session-id>.",
            "/retry": "Retry and replace the active final turn.",
            "/undo": "Remove the final turn from active context.",
            "/skills": "Discover, search, or inspect skills: /skills [query].",
            "/load-skill": "Explicitly activate instructions: /load-skill <name>.",
            "/trace": "Show the latest trace identity and status.",
            "/usage": "Show provider usage when available.",
            "/drafts": "List legacy skill drafts.",
            "/evolve": "Review evidence: /evolve review [version-id].",
            "/approve": "Approve an evaluated skill: /approve <version-id>.",
            "/reject": "Reject a skill candidate: /reject <version-id>.",
            "/rollback": "Create an audited rollback: /rollback <version-id>.",
            "/quit": "Exit the REPL.",
        }
        commands = [
            {"command": name, "description": descriptions[name]}
            for name in self._handlers
        ]
        aliases = dict(self._aliases)
        keys = {
            "submit": "Enter",
            "newline": "Esc+Enter",
            "cancel": "Ctrl+C",
        }
        examples = [
            {"command": "/skills crystal", "purpose": "Discover crystal skills."},
            {"command": "/load-skill <name>", "purpose": "Activate a skill."},
            {
                "command": "/evolve review <version-id>",
                "purpose": "Inspect replay evidence before approval.",
            },
            {
                "command": "/approve <version-id>",
                "purpose": "Approve an evaluated workflow.",
            },
        ]
        lines = ["MatSimPy AI commands (offline help)"]
        lines.extend(f"{item['command']}: {item['description']}" for item in commands)
        lines.append(
            "Aliases: "
            + ", ".join(f"{key} -> {value}" for key, value in aliases.items())
        )
        lines.append("Keys: Enter submit; Esc+Enter newline; Ctrl+C cancel.")
        lines.append(
            "Skills: discover with /skills, activate with /load-skill, review with "
            "/evolve review, then explicitly /approve or /reject."
        )
        lines.append("Examples: " + "; ".join(item["command"] for item in examples))
        return CommandResult(
            "help",
            data={
                "commands": commands,
                "aliases": aliases,
                "keys": keys,
                "examples": examples,
            },
            display_hint="\n".join(lines),
        )

    def _new(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/new")
        conversation_id = self.session.new()
        return CommandResult(
            "new",
            data={"conversation_id": conversation_id},
            display_hint=f"Started session {conversation_id}.",
        )

    def _sessions(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/sessions")
        sessions = [_record(item) for item in self.session.session_store.list_conversations()]
        return CommandResult(
            "sessions",
            data={"sessions": sessions},
            display_hint=f"{len(sessions)} saved session(s).",
        )

    def _resume(self, arg: str) -> CommandResult:
        if not arg:
            return self._usage_result("/resume <session_id>")
        try:
            conversation_id = int(arg)
        except ValueError:
            return self._usage_result("/resume <session_id>")
        self.session.resume(conversation_id)
        return CommandResult(
            "resume",
            data={
                "conversation_id": conversation_id,
                "turns": len(self.session.turns),
            },
            display_hint=f"Resumed session {conversation_id}.",
        )

    def _retry(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/retry")
        turn = self.session.retry()
        return CommandResult(
            "retry", data={"turn": _record(turn)}, display_hint=turn.final_response
        )

    def _undo(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/undo")
        turn = self.session.undo()
        return CommandResult(
            "undo",
            data={"turn": _record(turn)},
            display_hint=f"Undid: {turn.user_request}",
        )

    def _skills(self, arg: str) -> CommandResult:
        if self.skill_library is None:
            skills: list[Any] = []
        elif arg:
            detail_getter = getattr(self.skill_library, "detail", None)
            detail = detail_getter(arg) if detail_getter is not None else None
            if detail is not None:
                return CommandResult(
                    "skill-detail",
                    data={"skill": _record(detail)},
                    display_hint=f"Skill: {arg}",
                )
            skills = self.skill_library.search(arg)
        else:
            skills = self.skill_library.discover()
        values = [_record(item) for item in skills]
        return CommandResult(
            "skills",
            data={"skills": values},
            display_hint=f"{len(values)} skill(s).",
        )

    def _drafts(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/drafts")
        drafts = self.session.session_store.list_skill_drafts("draft")
        return CommandResult(
            "drafts",
            data={"drafts": drafts},
            display_hint=f"{len(drafts)} draft(s).",
        )

    def _approve(self, arg: str) -> CommandResult:
        if not arg:
            return self._usage_result("/approve <version-id>")
        version_id = self._version_id(arg, "approve")
        if isinstance(version_id, CommandResult):
            return version_id
        approved = self.evolution.approve(version_id)
        return CommandResult(
            "approve",
            data={"version": _record(approved)},
            display_hint=f"Approved skill version: {version_id}",
        )

    def _reject(self, arg: str) -> CommandResult:
        if not arg:
            return self._usage_result("/reject <version-id>")
        version_id = self._version_id(arg, "reject")
        if isinstance(version_id, CommandResult):
            return version_id
        rejected = self.evolution.reject(version_id)
        return CommandResult(
            "reject",
            data={"version": _record(rejected)},
            display_hint=f"Rejected skill version: {version_id}",
        )

    def _version_id(self, value: str, kind: str) -> int | CommandResult:
        try:
            version_id = int(value)
            if version_id <= 0:
                raise ValueError
        except ValueError:
            return self._error(
                f"{kind.title()} requires a positive numeric version ID.", kind=kind
            )
        return version_id

    def _rollback(self, arg: str) -> CommandResult:
        if not arg:
            return self._usage_result("/rollback <version-id>")
        rollback = getattr(self.evolution, "rollback", None)
        if rollback is None:
            return self._error("Skill rollback is not available yet.", kind="rollback")
        try:
            version_id = int(arg)
            if version_id <= 0:
                raise ValueError
        except ValueError:
            return self._error(
                "Rollback requires a positive numeric version ID.", kind="rollback"
            )
        try:
            rolled_back = rollback(version_id)
        except (KeyError, ValueError) as exc:
            return self._error(str(exc), kind="rollback")
        return CommandResult(
            "rollback",
            data={"target_version_id": version_id, "version": rolled_back},
            display_hint=f"Rolled back from skill version: {version_id}",
        )

    def _evolve(self, arg: str) -> CommandResult:
        action, _, candidate = arg.partition(" ")
        if action.casefold() != "review":
            return self._usage_result("/evolve review [candidate]")
        selector: int | str | None = candidate.strip() or None
        if isinstance(selector, str) and selector.isdecimal():
            selector = int(selector)
        reviewed = self.evolution.review(selector)
        candidates = reviewed if isinstance(reviewed, list) else [reviewed]
        return CommandResult(
            "evolve-review",
            data={"candidates": [_record(item) for item in candidates]},
            display_hint=f"{len(candidates)} evolution candidate(s) ready for review.",
        )

    def _trace(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/trace")
        trace = dict(self.trace_getter())
        return CommandResult(
            "trace",
            data={"trace": trace},
            display_hint="Trace available." if trace else "No trace yet.",
        )

    def _show_usage(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/usage")
        usage = dict(self.usage_getter())
        return CommandResult(
            "usage",
            data={"usage": usage},
            display_hint="Usage available." if usage else "No usage reported.",
        )

    def _quit(self, arg: str) -> CommandResult:
        if arg:
            return self._usage_result("/quit")
        return CommandResult("quit", display_hint="Goodbye.", exit_requested=True)

    def _load_skill(self, arg: str) -> CommandResult:
        if not arg:
            return self._usage_result("/load-skill <name>")
        if self.skill_loader is None:
            return self._error("Skill loading is not configured.", kind="load-skill")
        skill = self.skill_loader(arg)
        return CommandResult(
            "load-skill",
            data={"skill": skill},
            display_hint=f"Loaded skill context: {arg}",
        )

    def _runtime_trace(self) -> Mapping[str, Any]:
        result = self.session.runtime.last_result
        if result is None:
            return {}
        return {
            "session_id": result.session_id,
            "trace_id": result.trace_id,
            "status": result.status,
            "validation_status": result.validation_status,
        }

    @staticmethod
    def _error(message: str, *, kind: str = "error") -> CommandResult:
        return CommandResult(kind, ok=False, display_hint=message)

    @classmethod
    def _usage_result(cls, usage: str) -> CommandResult:
        return cls._error(f"Usage: {usage}")


def _record(value: Any) -> Any:
    if is_dataclass(value):
        return {item.name: _record(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _record(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_record(item) for item in value]
    return value


__all__ = ["CommandResult", "ReplController"]
