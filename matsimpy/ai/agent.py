"""The agent: an LLM loop over MatSimPy tools, skills and MCP servers.

Each turn sends the conversation and the *loaded* tools to the provider, runs
the tool calls it asks for, and repeats until it answers in text.  The model
sees the names of all tools in the system prompt and loads the schemas it needs
with meta-tools (``search_tools``, ``load_tools``); skills are listed by name
and description and loaded with ``activate_skill``.  Tools of MCP servers in
``mcp.json`` join the catalog like any other tool.

Conversations are saved as JSON in ``<workspace>/.matsimpy/sessions`` after
every turn, including the structures that tool results refer to, so a
session can be resumed later.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mcp import USER_CONFIG, MCPClient, MCPServerConfig, connect_servers, load_config
from .memory import AgentMemory
from .provider import ChatMessage, ChatProvider, DeepSeekProvider, ToolCall
from .skills import SkillError, SkillLibrary
from .tools import Tool, ToolCatalog, ToolExecutor, ToolResult
from .workspace import Workspace

__all__ = ["Agent", "AgentResult", "SYSTEM_PROMPT", "Session", "ToolRecord"]

SYSTEM_PROMPT = """You are a materials-science assistant that works through MatSimPy tools.

Rules:
1. Create, read, transform, analyze, calculate and save with tools. Never invent coordinates, \
energies, forces, symmetry or other data; get them from tools.
2. A tool that creates or changes a structure returns a structure_ref such as "structure:3". \
Pass that reference as the structure argument of later tools, also in later turns. Do not rebuild \
a structure you already have.
3. For a named prototype (fcc, bcc, hcp, diamond, zincblende, rocksalt, wurtzite, perovskite) use \
from_prototype; its lattice constant is the conventional one even when it returns a primitive cell. \
Use create_crystal only when the user gives coordinates. For a random crystal without coordinates \
use random_crystal.
4. Base the answer on tool results. Report numbers, space groups and Wyckoff letters as returned. \
Do not add claims or default values the user did not ask for.
5. If a tool fails, read the error, fix the arguments or pick another tool, and say what failed if \
you cannot recover.

Only some tools are loaded. All tool names are listed below; call search_tools or load_tools to \
load the ones you need before calling them. Skills hold instructions for specific tasks: call \
activate_skill when one matches the request."""

DEFAULT_PRELOAD = ("read_structure", "write_structure", "from_prototype", "create_crystal",
                   "create_molecule", "list_workspace_files")


@dataclass(frozen=True)
class ToolRecord:
    """One tool call of a turn."""

    name: str
    arguments: Mapping[str, Any]
    ok: bool
    result: Mapping[str, Any]


@dataclass(frozen=True)
class AgentResult:
    """The outcome of :meth:`Agent.run`."""

    response: str
    status: str
    """``success``, ``truncated`` (the reply hit the length limit), ``max_steps`` or ``error``."""
    tool_calls: tuple[ToolRecord, ...] = ()
    usage: Mapping[str, int] = field(default_factory=dict)

    @property
    def tools(self) -> tuple[str, ...]:
        return tuple(record.name for record in self.tool_calls)


@dataclass
class Session:
    """A saved conversation."""

    id: str
    created: str
    messages: list[dict] = field(default_factory=list)
    turns: list[int] = field(default_factory=list)
    """Index in ``messages`` where each user turn starts."""
    loaded_tools: list[str] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    objects: dict[str, dict] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)

    @classmethod
    def new(cls) -> Session:
        now = datetime.now(timezone.utc)
        return cls(id=f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}", created=now.isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {"version": 1, **{k: getattr(self, k) for k in (
            "id", "created", "messages", "turns", "loaded_tools", "active_skills", "objects", "usage")}}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Session:
        if data.get("version") != 1:
            raise ValueError(f"unsupported session version {data.get('version')!r}")
        return cls(**{k: data[k] for k in ("id", "created", "messages", "turns", "loaded_tools",
                                            "active_skills", "objects", "usage") if k in data})


class Agent:
    """Run tasks with an LLM and MatSimPy tools.

    Args:
        provider: The LLM; defaults to :class:`DeepSeekProvider` (needs ``DEEPSEEK_API_KEY``).
        workspace: Directory for files and sessions (default ``~/.matsimpy/ai/workspace``).
        catalog: Tools; defaults to :meth:`ToolCatalog.default` with ``tool_modules``.
        tool_modules: Extra modules whose ``@tool`` functions are added to the default catalog.
        skills: Skill library; defaults to packaged, user and workspace skills.
        mcp_servers: MCP servers to connect to.  Defaults to those in ``~/.matsimpy/ai/mcp.json``
            and ``<workspace>/mcp.json``; pass ``{}`` for none.
        memory: Memory files whose content goes into the system prompt (``None``: none).
        system_prompt: Replaces :data:`SYSTEM_PROMPT`.
        preload_tools: Tools loaded at the start of every session.
        max_steps: Most model calls in one turn.
        on_event: Called with ``(event, data)`` for ``tool_call``, ``tool_result`` and ``warning``.
        confine_paths: Reject tool file paths outside the workspace.
    """

    def __init__(
        self,
        provider: ChatProvider | None = None,
        *,
        workspace: str | Path | None = None,
        catalog: ToolCatalog | None = None,
        tool_modules: Iterable[str] = (),
        skills: SkillLibrary | None = None,
        mcp_servers: Mapping[str, MCPServerConfig] | None = None,
        memory: AgentMemory | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        preload_tools: Iterable[str] = DEFAULT_PRELOAD,
        max_steps: int = 20,
        on_event: Callable[[str, dict], None] | None = None,
        confine_paths: bool = True,
    ) -> None:
        self.provider = provider or DeepSeekProvider()
        self.workspace = Workspace(workspace)
        self.catalog = catalog if catalog is not None else ToolCatalog.default(tool_modules)
        self.executor = ToolExecutor(self.catalog, self.workspace, confine_paths=confine_paths)
        self.skills = skills if skills is not None else SkillLibrary(self.workspace.path)
        self.memory = memory
        self.system_prompt = system_prompt
        self.preload_tools = tuple(preload_tools)
        self.max_steps = max_steps
        self.on_event = on_event or (lambda event, data: None)
        self.meta = ToolCatalog([Tool.from_function(f, source="agent") for f in (
            self.search_tools, self.load_tools, self.activate_skill, self.read_skill_resource, self.propose_skill)])
        self._meta_executor = ToolExecutor(self.meta, self.workspace)

        if mcp_servers is None:
            mcp_servers = load_config([USER_CONFIG, self.workspace.path / "mcp.json"])
        self.mcp_clients: list[MCPClient] = []
        self.mcp_errors: dict[str, str] = {}
        self.connect_mcp(mcp_servers)
        self.session = self._new_session()

    # lifecycle ---------------------------------------------------------------
    def __enter__(self) -> Agent:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def close(self) -> None:
        """Disconnect from MCP servers."""
        for client in self.mcp_clients:
            self.catalog.remove_source(f"mcp:{client.name}")
            client.close()
        self.mcp_clients = []

    def connect_mcp(self, servers: Mapping[str, MCPServerConfig]) -> None:
        """Connect to MCP servers and add their tools to the catalog."""
        clients, errors = connect_servers(servers)
        self.mcp_errors.update(errors)
        for name, error in errors.items():
            self.on_event("warning", {"message": f"MCP server {name!r} unavailable: {error}"})
        for client in clients:
            try:
                self.catalog.extend(client.tools())
            except Exception as exc:
                self.mcp_errors[client.name] = str(exc)
                client.close()
                continue
            self.mcp_clients.append(client)

    @property
    def sessions_dir(self) -> Path:
        return self.workspace.path / ".matsimpy" / "sessions"

    def _new_session(self) -> Session:
        session = Session.new()
        session.loaded_tools = [name for name in self.preload_tools if name in self.catalog]
        return session

    def new_session(self) -> Session:
        """Start a new conversation (structures of the old one stay in the old session file)."""
        self.executor.objects.clear()
        self.session = self._new_session()
        return self.session

    def save(self, path: str | Path | None = None) -> Path:
        """Write the session as JSON (by default to the sessions directory)."""
        self.session.objects = self.executor.export_objects()
        path = Path(path) if path else self.sessions_dir / f"{self.session.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.session.to_dict(), indent=1, default=str), encoding="utf-8")
        tmp.replace(path)
        return path

    def list_sessions(self) -> list[dict]:
        """Saved sessions, newest first: id, created, turns and the first request."""
        items = []
        for path in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            first = next((m["content"] for m in data.get("messages", []) if m.get("role") == "user"), "")
            items.append({"id": data.get("id", path.stem), "created": data.get("created"),
                          "turns": len(data.get("turns", [])), "first_request": first[:80]})
        return items

    def resume(self, session_id: str) -> Session:
        """Continue a saved session: its messages, structures, loaded tools and active skills."""
        path = self.sessions_dir / f"{session_id}.json"
        if not path.is_file():
            raise KeyError(f"no saved session {session_id!r}")
        session = Session.from_dict(json.loads(path.read_text(encoding="utf-8")))
        self.executor.objects.clear()
        self.executor.import_objects(session.objects)
        self.session = session
        for name in list(session.active_skills):
            try:
                self._load_skill_tools(name)
            except SkillError as exc:
                self.on_event("warning", {"message": f"skill {name!r} not restored: {exc}"})
        return session

    # turns -------------------------------------------------------------------
    def run(self, text: str) -> AgentResult:
        """Run one user turn and save the session."""
        session = self.session
        start = len(session.messages)
        session.turns.append(start)
        session.messages.append(ChatMessage.user(text).to_dict())
        records: list[ToolRecord] = []
        usage: dict[str, int] = {}
        try:
            result = self._loop(records, usage)
        except BaseException:
            del session.messages[start:]  # never keep a half-finished turn
            session.turns.pop()
            raise
        if result.status == "error":
            del session.messages[start:]
            session.turns.pop()
        for key, value in usage.items():
            session.usage[key] = session.usage.get(key, 0) + value
        self.save()
        return result

    def _loop(self, records: list[ToolRecord], usage: dict[str, int]) -> AgentResult:
        session = self.session
        for _ in range(self.max_steps):
            try:
                response = self.provider.chat(self._messages(), self._tool_schemas())
            except Exception as exc:
                return AgentResult(f"Provider error: {type(exc).__name__}: {exc}", "error", tuple(records), usage)
            for key, value in response.usage.items():
                usage[key] = usage.get(key, 0) + value
            session.messages.append(response.message.to_dict())
            if not response.tool_calls:
                status = "truncated" if response.finish_reason == "length" else "success"
                return AgentResult(response.message.content, status, tuple(records), usage)
            for call in response.tool_calls:
                record = self._call(call)
                records.append(record)
                session.messages.append(ChatMessage.tool(json.dumps(record.result, ensure_ascii=False),
                                                         call.id).to_dict())
        return AgentResult("Stopped: the step limit was reached before an answer.", "max_steps",
                           tuple(records), usage)

    def _call(self, call: ToolCall) -> ToolRecord:
        self.on_event("tool_call", {"name": call.name, "arguments": call.arguments})
        if call.name in self.meta:
            result = self._meta_executor.call(call.name, call.arguments)
        else:
            result: ToolResult = self.executor.call(call.name, call.arguments)
            if call.name in self.catalog and call.name not in self.session.loaded_tools:
                self.session.loaded_tools.append(call.name)
        self.on_event("tool_result", {"name": call.name, "ok": result.ok, "result": result.content()})
        return ToolRecord(call.name, dict(call.arguments), result.ok, result.content())

    def undo(self) -> str:
        """Remove the last turn; returns its request."""
        if not self.session.turns:
            raise ValueError("nothing to undo")
        start = self.session.turns.pop()
        text = self.session.messages[start]["content"]
        del self.session.messages[start:]
        self.save()
        return text

    def retry(self) -> AgentResult:
        """Run the last request again, replacing its turn."""
        return self.run(self.undo())

    # prompt and tools --------------------------------------------------------
    def _messages(self) -> list[ChatMessage]:
        return [ChatMessage.system(self.system_text()), *map(ChatMessage.from_dict, self.session.messages)]

    def system_text(self) -> str:
        """The system prompt: rules, tool names by module, skills, and memory."""
        groups: dict[str, list[str]] = {}
        for tool in self.catalog.values():
            group = tool.source.removeprefix("matsimpy.").split(".")[0] if tool.source.startswith(
                "matsimpy.") else tool.source
            groups.setdefault(group or "other", []).append(tool.name)
        tools = "\n".join(f"- {group}: {', '.join(sorted(names))}" for group, names in sorted(groups.items()))
        parts = [self.system_prompt, f"Tools:\n{tools}",
                 f"Loaded tools: {', '.join(self.session.loaded_tools) or 'none'}"]
        skills = self.skills.discover()
        if skills:
            parts.append("Skills:\n" + "\n".join(f"- {s.name}: {s.description}" for s in skills))
        parts.append(f"Workspace: {self.workspace.path}")
        if self.memory is not None:
            memory = self._memory_text()
            if memory:
                parts.append(f"Memory:\n{memory}")
        return "\n\n".join(parts)

    def _memory_text(self, limit: int = 2400) -> str:
        chunks = [self.memory.get_soul_prompt().strip()]
        for name in ("user", "memory"):
            lines = [line for line in self.memory.read(name).splitlines() if line.strip()]
            if lines:
                chunks.append(f"{name}.md:\n" + "\n".join(lines[-24:]))
        return "\n\n".join(chunk for chunk in chunks if chunk)[-limit:]

    def _tool_schemas(self) -> list[dict]:
        schemas = [tool.openai_schema() for tool in self.meta.values()]
        schemas += [self.catalog[name].openai_schema() for name in self.session.loaded_tools if name in self.catalog]
        return schemas

    # meta-tools (their docstrings are what the model reads) -------------------
    def search_tools(self, query: str, limit: int = 8) -> list[dict]:
        """Find tools by keywords and load them so they can be called next.

        Args:
            query: Keywords, e.g. "supercell" or "slab surface adsorbate".
            limit: Most tools to return.
        """
        found = self.catalog.search(query, limit=limit)
        for tool in found:
            if tool.name not in self.session.loaded_tools:
                self.session.loaded_tools.append(tool.name)
        return [{"name": tool.name, "description": tool.summary()} for tool in found]

    def load_tools(self, names: list[str]) -> dict:
        """Load tools by exact name so they can be called next.

        Args:
            names: Tool names from the tool list.
        """
        loaded, unknown = [], []
        for name in names:
            if name in self.catalog:
                loaded.append(name)
                if name not in self.session.loaded_tools:
                    self.session.loaded_tools.append(name)
            else:
                unknown.append(name)
        return {"loaded": loaded, "unknown": unknown}

    def activate_skill(self, name: str) -> dict:
        """Load a skill's instructions (and its tools).  Follow the instructions it returns.

        Args:
            name: Skill name from the skill list.
        """
        skill = self._load_skill_tools(name)
        if name not in self.session.active_skills:
            self.session.active_skills.append(name)
        return {"name": skill.name, "instructions": skill.instructions, "resources": list(skill.resources),
                "tools": [tool.name for tool in skill.tools]}

    def _load_skill_tools(self, name: str):
        skill = self.skills.activate(name)
        self.catalog.remove_source(f"skill:{name}")
        self.catalog.extend(skill.tools)
        for tool_name in (*(tool.name for tool in skill.tools), *skill.allowed_tools):
            if tool_name in self.catalog and tool_name not in self.session.loaded_tools:
                self.session.loaded_tools.append(tool_name)
        return skill

    def read_skill_resource(self, skill: str, path: str) -> str:
        """Read a file of a skill, e.g. a reference its instructions mention.

        Args:
            skill: Skill name.
            path: File path inside the skill, as listed in its resources.
        """
        return self.skills.read_resource(skill, path)

    def propose_skill(self, name: str, description: str, instructions: str) -> dict:
        """Save reusable instructions as a draft skill.  The user must approve it before it can be used.

        Args:
            name: Lowercase name with hyphens, e.g. "relaxed-slab-workflow".
            description: When the skill should be used (one or two sentences).
            instructions: Markdown instructions: the steps and the tools to use.
        """
        draft = self.skills.create_draft(name, description, instructions)
        return {"draft": draft.name, "status": "awaiting user approval (/approve " + draft.name + ")"}

    # convenience -------------------------------------------------------------
    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolResult:
        """Run a tool directly, without the model (same executor and structures as the agent)."""
        executor = self._meta_executor if name in self.meta else self.executor
        return executor.call(name, arguments)
