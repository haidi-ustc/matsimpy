"""Slash commands of the interactive agent, without terminal I/O."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .mcp import MCPError
from .skills import SkillError, validate

__all__ = ["CommandResult", "ReplController"]


@dataclass(frozen=True)
class CommandResult:
    """Text to show, whether the command succeeded, and whether the REPL should exit."""

    text: str
    ok: bool = True
    exit: bool = False
    data: Any = field(default=None, compare=False)



def _turns(count: int) -> str:
    return f"{count} turn" if count == 1 else f"{count} turns"

class ReplController:
    """Run ``/commands`` against an :class:`~matsimpy.ai.agent.Agent`."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.commands: dict[str, tuple[Callable[[str], CommandResult], str]] = {
            "/help": (self._help, "Show the commands."),
            "/new": (self._new, "Start a new session."),
            "/sessions": (self._sessions, "List saved sessions."),
            "/resume": (self._resume, "Resume a saved session: /resume <id>."),
            "/undo": (self._undo, "Remove the last turn."),
            "/retry": (self._retry, "Run the last request again."),
            "/save": (self._save, "Save the session as JSON: /save [path]."),
            "/tools": (self._tools, "List loaded tools, search tools (/tools <words>) or /tools reload."),
            "/tool": (self._tool, "Show a tool's description and parameters: /tool <name>."),
            "/skills": (self._skills, "List skills; /skills install <path>, remove <name>, validate <path>."),
            "/skill": (self._skill, "Activate a skill for this session: /skill <name>."),
            "/drafts": (self._drafts, "List draft skills, or show one: /drafts [name]."),
            "/approve": (self._approve, "Approve a draft skill: /approve <name>."),
            "/reject": (self._reject, "Delete a draft skill: /reject <name>."),
            "/mcp": (self._mcp, "List MCP servers and their tools."),
            "/workspace": (self._workspace, "Show the workspace and its files."),
            "/model": (self._model, "Show or set the model: /model [name]."),
            "/usage": (self._usage, "Token usage of this session."),
            "/quit": (self._quit, "Exit."),
        }
        self.aliases = {"/exit": "/quit", "/q": "/quit", "/?": "/help"}

    def command_names(self) -> tuple[str, ...]:
        return tuple(sorted((*self.commands, *self.aliases)))

    def complete(self, prefix: str) -> tuple[str, ...]:
        return tuple(name for name in self.command_names() if name.startswith(prefix.casefold()))

    def execute(self, line: str) -> CommandResult:
        """Run one command line, e.g. ``/resume 20261112-101500-ab12``."""
        name, _, argument = line.strip().partition(" ")
        name = self.aliases.get(name.casefold(), name.casefold())
        if name not in self.commands:
            return CommandResult(f"Unknown command {name}. /help lists the commands.", ok=False)
        try:
            return self.commands[name][0](argument.strip())
        except (KeyError, ValueError, SkillError, MCPError, OSError) as exc:
            message = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
            return CommandResult(f"{name}: {message}", ok=False)

    # sessions ----------------------------------------------------------------
    def _help(self, argument: str) -> CommandResult:
        width = max(map(len, self.commands))
        lines = [f"{name.ljust(width)}  {text}" for name, (_, text) in self.commands.items()]
        return CommandResult("\n".join(lines))

    def _new(self, argument: str) -> CommandResult:
        session = self.agent.new_session()
        return CommandResult(f"New session {session.id}.")

    def _sessions(self, argument: str) -> CommandResult:
        sessions = self.agent.list_sessions()
        if not sessions:
            return CommandResult("No saved sessions.", data=sessions)
        lines = [f"{s['id']}  {_turns(s['turns'])}  {s['first_request']}" for s in sessions]
        return CommandResult("\n".join(lines), data=sessions)

    def _resume(self, argument: str) -> CommandResult:
        if not argument:
            raise ValueError("usage: /resume <id>")
        session = self.agent.resume(argument)
        return CommandResult(f"Resumed {session.id} ({_turns(len(session.turns))}).")

    def _undo(self, argument: str) -> CommandResult:
        text = self.agent.undo()
        return CommandResult(f"Removed the turn: {text[:80]}")

    def _retry(self, argument: str) -> CommandResult:
        result = self.agent.retry()
        return CommandResult(result.response, ok=result.status == "success", data=result)

    def _save(self, argument: str) -> CommandResult:
        path = self.agent.save(Path(argument).expanduser() if argument else None)
        return CommandResult(f"Saved to {path}.")

    # tools -------------------------------------------------------------------
    def _tools(self, argument: str) -> CommandResult:
        if argument == "reload":
            self.agent.catalog.refresh(reload=True)
            return CommandResult(f"Reloaded: {len(self.agent.catalog)} tools.")
        if argument:
            found = self.agent.catalog.search(argument, limit=20)
            lines = [f"{tool.name}: {tool.summary()}" for tool in found]
            return CommandResult("\n".join(lines) or "No matching tools.", data=found)
        loaded = self.agent.session.loaded_tools
        text = (f"{len(self.agent.catalog)} tools; loaded in this session: {', '.join(loaded) or 'none'}.\n"
                "/tools <words> searches, /tool <name> shows one.")
        return CommandResult(text, data=loaded)

    def _tool(self, argument: str) -> CommandResult:
        tool = self.agent.catalog.get(argument) or self.agent.meta.get(argument)
        if tool is None:
            raise KeyError(f"unknown tool {argument!r}")
        text = f"{tool.name} ({tool.source})\n\n{tool.description}\n\n{json.dumps(dict(tool.parameters), indent=2)}"
        return CommandResult(text, data=tool)

    # skills ------------------------------------------------------------------
    def _skills(self, argument: str) -> CommandResult:
        action, _, target = argument.partition(" ")
        library = self.agent.skills
        if action == "install":
            replace = target.endswith(" --replace")
            summary = library.install(target.removesuffix(" --replace").strip(), replace=replace)
            return CommandResult(f"Installed {summary.name} in {summary.path}.")
        if action == "remove":
            library.remove(target.strip())
            return CommandResult(f"Removed {target.strip()}.")
        if action == "validate":
            problems = validate(Path(target.strip()).expanduser())
            return CommandResult("Valid." if not problems else "\n".join(problems), ok=not problems)
        if action:
            raise ValueError("usage: /skills [install <path> [--replace] | remove <name> | validate <path>]")
        skills = library.discover()
        active = set(self.agent.session.active_skills)
        lines = [f"{'*' if s.name in active else ' '} {s.name} ({s.source}): {s.description}" for s in skills]
        lines += [f"! skipped {path}: {problem}" for path, problem in library.problems.items()]
        return CommandResult("\n".join(lines) or "No skills.", data=skills)

    def _skill(self, argument: str) -> CommandResult:
        if not argument:
            raise ValueError("usage: /skill <name>")
        data = self.agent.activate_skill(argument)
        self.agent.session.messages.append({
            "role": "user",
            "content": f"[I activated the skill {argument}. Its instructions:]\n\n{data['instructions']}",
        })
        tools = f" Tools: {', '.join(data['tools'])}." if data["tools"] else ""
        return CommandResult(f"Activated {argument}.{tools}")

    def _drafts(self, argument: str) -> CommandResult:
        library = self.agent.skills
        if argument:
            draft = library.draft(argument)
            return CommandResult(f"{draft.name}: {draft.description}\n\n{draft.instructions}", data=draft)
        drafts = library.drafts()
        lines = [f"{d.name}: {d.description}" for d in drafts]
        return CommandResult("\n".join(lines) or "No drafts.", data=drafts)

    def _approve(self, argument: str) -> CommandResult:
        summary = self.agent.skills.approve(argument)
        return CommandResult(f"Approved {summary.name}; it is now available.")

    def _reject(self, argument: str) -> CommandResult:
        self.agent.skills.reject(argument)
        return CommandResult(f"Deleted draft {argument}.")

    # environment -------------------------------------------------------------
    def _mcp(self, argument: str) -> CommandResult:
        lines = []
        for client in self.agent.mcp_clients:
            tools = [t.name for t in self.agent.catalog.values() if t.source == f"mcp:{client.name}"]
            lines.append(f"{client.name} ({client.config.transport}, protocol {client.protocol_version}): "
                         f"{', '.join(tools) or 'no tools'}")
        lines += [f"{name}: unavailable ({error})" for name, error in self.agent.mcp_errors.items()]
        return CommandResult("\n".join(lines) or "No MCP servers configured (mcp.json).")

    def _workspace(self, argument: str) -> CommandResult:
        path = self.agent.workspace.path
        files = sorted(p.name for p in path.iterdir() if p.is_file())
        return CommandResult(f"{path}\n" + ("\n".join(f"  {name}" for name in files) or "  (no files)"))

    def _model(self, argument: str) -> CommandResult:
        if argument:
            self.agent.provider.model = argument
        return CommandResult(f"Model: {self.agent.provider.model}")

    def _usage(self, argument: str) -> CommandResult:
        usage = self.agent.session.usage
        text = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in usage.items())
        return CommandResult(text or "No usage yet.", data=dict(usage))

    def _quit(self, argument: str) -> CommandResult:
        return CommandResult("Goodbye.", exit=True)
