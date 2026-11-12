"""Model Context Protocol: use tools of MCP servers, and serve MatSimPy's tools.

Client
    :class:`MCPClient` connects to one server over stdio (a subprocess) or
    Streamable HTTP, performs the ``initialize`` handshake, lists the server's
    tools and calls them.  :func:`load_config` reads ``mcp.json`` files in the
    common ``{"mcpServers": {...}}`` format; :meth:`MCPClient.tools` turns the
    server's tools into :class:`~matsimpy.ai.tools.Tool` objects named
    ``<server>__<tool>``.

Server
    :class:`MCPServer` exposes a :class:`~matsimpy.ai.tools.ToolCatalog` over
    stdio (``matsimpy-ai mcp serve``), so any MCP client can call MatSimPy.

Only what tools need is implemented: the handshake (protocol versions
2024-11-05 to 2025-11-25), ``ping``, ``tools/list`` and ``tools/call``.
A client probing for the stateless 2026-07-28 protocol (``server/discover``)
gets "method not found", which tells it to fall back to the handshake.
OAuth is not implemented; give HTTP credentials as headers in ``mcp.json``.
"""

from __future__ import annotations

import contextlib
import dataclasses
import itertools
import json
import logging
import os
import re
import subprocess
import sys
import threading
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from .tools import Tool, ToolCatalog, ToolError, ToolExecutor

__all__ = [
    "MCPClient",
    "MCPError",
    "MCPServer",
    "MCPServerConfig",
    "PROTOCOL_VERSION",
    "SUPPORTED_VERSIONS",
    "connect_servers",
    "load_config",
]

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
USER_CONFIG = Path.home() / ".matsimpy" / "ai" / "mcp.json"

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603
REQUEST_TIMEOUT = -32001


class MCPError(Exception):
    """A JSON-RPC error from an MCP peer, or a transport failure."""

    def __init__(self, message: str, code: int = INTERNAL_ERROR, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


def _version() -> str:
    from .. import __version__

    return __version__


# --------------------------------------------------------------------------- configuration


@dataclass(frozen=True)
class MCPServerConfig:
    """One server of an ``mcp.json`` file: a ``command`` (stdio) or a ``url`` (Streamable HTTP)."""

    name: str
    command: str | None = None
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    cwd: str | None = None
    url: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    timeout: float = 60.0
    enabled: bool = True

    def __post_init__(self) -> None:
        if bool(self.command) == bool(self.url):
            raise ValueError(f"MCP server {self.name!r}: give exactly one of 'command' or 'url'")
        if self.timeout <= 0:
            raise ValueError(f"MCP server {self.name!r}: 'timeout' must be positive")

    @property
    def transport(self) -> str:
        return "stdio" if self.command else "http"

    @classmethod
    def from_dict(cls, name: str, data: Mapping[str, Any]) -> MCPServerConfig:
        known = {"command", "args", "env", "cwd", "url", "headers", "timeout", "enabled", "type", "disabled"}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"MCP server {name!r}: unknown keys {sorted(unknown)}")
        if data.get("type") not in (None, "stdio", "http", "streamable-http", "streamableHttp"):
            raise ValueError(f"MCP server {name!r}: unsupported type {data['type']!r} (stdio or http)")
        args = data.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ValueError(f"MCP server {name!r}: 'args' must be a list of strings")
        for key in ("env", "headers"):
            value = data.get(key, {})
            if not isinstance(value, dict) or not all(isinstance(v, str) for v in value.values()):
                raise ValueError(f"MCP server {name!r}: {key!r} must map names to strings")
        enabled = bool(data.get("enabled", not data.get("disabled", False)))
        # ${NAME} is expanded only for enabled servers, so a disabled one may name unset variables
        expand = _expand if enabled else (lambda value: value)
        return cls(
            name=name,
            command=expand(data["command"]) if data.get("command") else None,
            args=tuple(expand(a) for a in args),
            env={k: expand(v) for k, v in data.get("env", {}).items()},
            cwd=expand(data["cwd"]) if data.get("cwd") else None,
            url=expand(data["url"]) if data.get("url") else None,
            headers={k: expand(v) for k, v in data.get("headers", {}).items()},
            timeout=float(data.get("timeout", 60.0)),
            enabled=enabled,
        )


def _expand(value: str) -> str:
    """Replace ``${NAME}`` with the environment variable (secrets stay out of the file)."""
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise ValueError(f"environment variable {name} is not set")
        return os.environ[name]

    return re.sub(r"\$\{(\w+)\}", replace, value)


def load_config(paths: Iterable[str | Path] = ()) -> dict[str, MCPServerConfig]:
    """Servers from ``mcp.json`` files; a later file overrides a server of the same name.

    Missing files are skipped.  The format is ``{"mcpServers": {"name": {"command": ...,
    "args": [...], "env": {...}}}}`` for stdio, or ``{"url": ..., "headers": {...}}`` for HTTP.
    """
    servers: dict[str, MCPServerConfig] = {}
    for path in paths:
        path = Path(path).expanduser()
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON: {exc}") from None
        entries = data.get("mcpServers") if isinstance(data, dict) else None
        if not isinstance(entries, dict):
            raise ValueError(f"{path}: expected an object with 'mcpServers'")
        for name, entry in entries.items():
            if not isinstance(entry, dict):
                raise ValueError(f"{path}: server {name!r} must be an object")
            try:
                servers[name] = MCPServerConfig.from_dict(name, entry)
            except ValueError as exc:
                raise ValueError(f"{path}: {exc}") from None
    return servers


# --------------------------------------------------------------------------- transports


class _StdioTransport:
    """Newline-delimited JSON-RPC over a subprocess's stdin and stdout."""

    def __init__(self, config: MCPServerConfig, on_message) -> None:
        env = {**os.environ, **config.env}
        try:
            self.process = subprocess.Popen(
                [config.command, *config.args],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=config.cwd, env=env, text=True, encoding="utf-8", bufsize=1,
            )
        except OSError as exc:
            raise MCPError(f"cannot start MCP server {config.name!r}: {exc}") from exc
        self.name = config.name
        self._lock = threading.Lock()
        self.stderr: list[str] = []
        self.closed = threading.Event()
        threading.Thread(target=self._read, args=(on_message,), daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read(self, on_message) -> None:
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                on_message(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("MCP server %s wrote a non-JSON line: %.200s", self.name, line)
        self.closed.set()
        on_message(None)

    def _read_stderr(self) -> None:
        for line in self.process.stderr:
            self.stderr = (self.stderr + [line.rstrip()])[-50:]

    def send(self, message: dict) -> None:
        text = json.dumps(message, separators=(",", ":"))
        with self._lock:
            if self.process.poll() is not None:
                raise MCPError(f"MCP server {self.name!r} exited ({self.process.returncode})")
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=2)
            except Exception:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()


class _HttpTransport:
    """Streamable HTTP: every message is a POST; replies come as JSON or as an SSE stream."""

    def __init__(self, config: MCPServerConfig, on_message) -> None:
        import requests

        self.url = config.url
        self.timeout = config.timeout
        self.session = requests.Session()
        self.session.headers.update(config.headers)
        self.session_id: str | None = None
        self.protocol_version: str | None = None
        self.on_message = on_message
        self.closed = threading.Event()

    def send(self, message: dict) -> None:
        import requests

        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        try:
            response = self.session.post(self.url, json=message, headers=headers, stream=True, timeout=self.timeout)
        except requests.RequestException as exc:
            raise MCPError(f"HTTP request to {self.url} failed: {exc}") from exc
        with response:
            if response.status_code == 404 and self.session_id:
                raise MCPError("the MCP server ended the session (HTTP 404)")
            if response.status_code >= 400:
                raise MCPError(f"HTTP {response.status_code} from {self.url}: {response.text[:300]}")
            if "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]
            if response.status_code == 202 or "id" not in message or "method" not in message:
                return  # notifications and our replies to server requests get no reply
            kind = response.headers.get("Content-Type", "").split(";")[0].strip()
            if kind == "text/event-stream":
                for data in _sse_data(response.iter_lines(decode_unicode=True)):
                    self.on_message(json.loads(data))
            elif kind == "application/json":
                body = response.json()
                for item in body if isinstance(body, list) else [body]:
                    self.on_message(item)
            else:
                raise MCPError(f"unexpected Content-Type {kind!r} from {self.url}")

    def close(self) -> None:
        if self.session_id:
            try:
                self.session.delete(self.url, headers={"Mcp-Session-Id": self.session_id}, timeout=5)
            except Exception:
                pass
        self.session.close()


def _sse_data(lines: Iterable[str]) -> Iterator[str]:
    """The ``data`` of each server-sent event."""
    data: list[str] = []
    for line in lines:
        if line is None:
            continue
        if line == "":
            if data:
                yield "\n".join(data)
            data = []
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    if data:
        yield "\n".join(data)


# --------------------------------------------------------------------------- client


class MCPClient:
    """A connection to one MCP server.  Use as a context manager, or call :meth:`connect` and :meth:`close`."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._ids = itertools.count(1)
        self._pending: dict[int, tuple[threading.Event, list]] = {}
        self._lock = threading.Lock()
        self._transport: _StdioTransport | _HttpTransport | None = None
        self.protocol_version: str | None = None
        self.server_info: dict = {}
        self.instructions: str | None = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def connected(self) -> bool:
        return self._transport is not None and not self._transport.closed.is_set()

    def __enter__(self) -> MCPClient:
        return self.connect()

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def connect(self) -> MCPClient:
        """Start the transport and perform the ``initialize`` handshake."""
        if self._transport is not None:
            return self
        transport_cls = _StdioTransport if self.config.transport == "stdio" else _HttpTransport
        self._transport = transport_cls(self.config, self._on_message)
        try:
            result = self.request("initialize", {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "matsimpy", "version": _version()},
            })
            version = result.get("protocolVersion")
            if version not in SUPPORTED_VERSIONS:
                raise MCPError(f"MCP server {self.name!r} speaks protocol {version!r}; "
                               f"supported: {', '.join(SUPPORTED_VERSIONS)}")
            self.protocol_version = version
            self.server_info = result.get("serverInfo") or {}
            self.instructions = result.get("instructions")
            if isinstance(self._transport, _HttpTransport):
                self._transport.protocol_version = version
            self.notify("notifications/initialized")
        except BaseException:
            self.close()
            raise
        return self

    def close(self) -> None:
        transport, self._transport = self._transport, None
        if transport is not None:
            transport.close()
        with self._lock:
            for event, slot in self._pending.values():
                slot.append({"error": {"code": INTERNAL_ERROR, "message": "connection closed"}})
                event.set()
            self._pending.clear()

    # JSON-RPC ----------------------------------------------------------------
    def request(self, method: str, params: Mapping[str, Any] | None = None, timeout: float | None = None) -> dict:
        """Send a request and wait for its result."""
        if self._transport is None:
            raise MCPError(f"MCP server {self.name!r} is not connected")
        request_id = next(self._ids)
        event, slot = threading.Event(), []
        with self._lock:
            self._pending[request_id] = (event, slot)
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = dict(params)
        try:
            self._transport.send(message)
            if not event.wait(timeout or self.config.timeout):
                self._cancel(request_id, "timeout")
                raise MCPError(f"MCP server {self.name!r}: {method} timed out after "
                               f"{timeout or self.config.timeout:g} s", REQUEST_TIMEOUT)
        finally:
            with self._lock:
                self._pending.pop(request_id, None)
        reply = slot[0]
        if "error" in reply:
            error = reply["error"] or {}
            detail = ""
            if isinstance(self._transport, _StdioTransport) and error.get("message") == "connection closed":
                detail = "; stderr: " + " | ".join(self._transport.stderr[-5:])
            raise MCPError(f"{method}: {error.get('message', 'error')}{detail}", error.get("code", INTERNAL_ERROR),
                           error.get("data"))
        result = reply.get("result")
        return result if isinstance(result, dict) else {}

    def notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = dict(params)
        self._transport.send(message)

    def _cancel(self, request_id: int, reason: str) -> None:
        try:
            self.notify("notifications/cancelled", {"requestId": request_id, "reason": reason})
        except MCPError:
            pass

    def _on_message(self, message: dict | None) -> None:
        if message is None:  # stdout closed: fail every waiting request
            with self._lock:
                for event, slot in self._pending.values():
                    slot.append({"error": {"code": INTERNAL_ERROR, "message": "connection closed"}})
                    event.set()
            return
        if "method" in message:
            if "id" in message:  # a request from the server
                self._answer_server_request(message)
            return  # notifications (logging, progress, list_changed) are not used
        with self._lock:
            pending = self._pending.get(message.get("id"))
        if pending is not None:
            pending[1].append(message)
            pending[0].set()

    def _answer_server_request(self, message: dict) -> None:
        reply: dict[str, Any] = {"jsonrpc": "2.0", "id": message["id"]}
        if message["method"] == "ping":
            reply["result"] = {}
        else:
            reply["error"] = {"code": METHOD_NOT_FOUND, "message": f"client does not support {message['method']}"}
        threading.Thread(target=self._send_quietly, args=(reply,), daemon=True).start()

    def _send_quietly(self, message: dict) -> None:
        try:
            if self._transport is not None:
                self._transport.send(message)
        except MCPError:
            pass

    # tools -------------------------------------------------------------------
    def list_tools(self) -> list[dict]:
        """The server's tool definitions (all pages)."""
        tools: list[dict] = []
        cursor = None
        while True:
            result = self.request("tools/list", {"cursor": cursor} if cursor else None)
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict:
        """The raw ``tools/call`` result (``content``, ``structuredContent``, ``isError``)."""
        return self.request("tools/call", {"name": name, "arguments": dict(arguments or {})})

    def tools(self) -> list[Tool]:
        """The server's tools as :class:`Tool` objects named ``<server>__<tool>``."""
        prefix = re.sub(r"[^A-Za-z0-9_-]", "_", self.name)
        converted = []
        for definition in self.list_tools():
            remote = definition["name"]
            local = f"{prefix}__{re.sub(r'[^A-Za-z0-9_-]', '_', remote)}"[:64]
            schema = dict(definition.get("inputSchema") or {})
            schema.setdefault("type", "object")
            schema.setdefault("properties", {})
            description = definition.get("description") or definition.get("title") or f"{remote} ({self.name})"
            converted.append(Tool(
                name=local,
                description=f"{description}\n\n(MCP server {self.name})",
                parameters=schema,
                function=_RemoteTool(self, remote),
                source=f"mcp:{self.name}",
                help=description,
            ))
        return converted


@dataclass(frozen=True)
class _RemoteTool:
    """Calls one tool of an MCP server and returns its result as JSON data."""

    client: MCPClient
    remote_name: str

    def __call__(self, **arguments: Any) -> Any:
        result = self.client.call_tool(self.remote_name, arguments)
        text = _content_text(result.get("content") or [])
        if result.get("isError"):
            raise ToolError(text or f"{self.remote_name} failed")
        if result.get("structuredContent") is not None:
            return result["structuredContent"]
        return {"content": text}


def _content_text(content: list[dict]) -> str:
    parts = []
    for block in content:
        kind = block.get("type")
        if kind == "text":
            parts.append(block.get("text", ""))
        elif kind == "resource" and "text" in (block.get("resource") or {}):
            parts.append(block["resource"]["text"])
        elif kind == "resource_link":
            parts.append(f"[resource {block.get('uri')}]")
        else:
            parts.append(f"[{kind} content]")
    return "\n".join(parts)


def connect_servers(configs: Mapping[str, MCPServerConfig]) -> tuple[list[MCPClient], dict[str, str]]:
    """Connect to every enabled server.  Returns the clients and the errors of servers that failed."""
    clients, errors = [], {}
    for name, config in configs.items():
        if not config.enabled:
            continue
        if config.name != name:  # the mapping key names the server, as in mcp.json
            config = dataclasses.replace(config, name=name)
        client = MCPClient(config)
        try:
            client.connect()
        except Exception as exc:
            errors[name] = str(exc)
            continue
        clients.append(client)
    return clients, errors


# --------------------------------------------------------------------------- server


class MCPServer:
    """Serve a tool catalog to MCP clients over stdio.

    Structures returned by one call can be passed to the next as
    ``structure:N`` references, for as long as the server runs.
    """

    def __init__(self, catalog: ToolCatalog, workspace: str | Path | None = None, *,
                 name: str = "matsimpy", instructions: str | None = None) -> None:
        self.catalog = catalog
        self.executor = ToolExecutor(catalog, workspace or Path.cwd())
        self.name = name
        self.instructions = instructions or (
            "MatSimPy materials-science tools. Tools that create or change a structure return a "
            "'structure_ref' such as 'structure:1'; pass it to later tools as the structure argument. "
            f"Files are read from and written to {self.executor.workspace.path}."
        )
        self.initialized = False

    def handle(self, message: Any) -> dict | None:
        """The response to one JSON-RPC message (``None`` for a notification)."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
            if isinstance(message, dict) and ("result" in message or "error" in message):
                return None  # a response to a request we never send
            return _error(message.get("id") if isinstance(message, dict) else None, INVALID_REQUEST,
                          "invalid JSON-RPC request")
        method, request_id = message["method"], message.get("id")
        params = message.get("params") or {}
        if "id" not in message:
            if method == "notifications/initialized":
                self.initialized = True
            return None
        try:
            handler = {
                "initialize": self._initialize,
                "ping": lambda p: {},
                "tools/list": self._list_tools,
                "tools/call": self._call_tool,
            }.get(method)
            if handler is None:
                return _error(request_id, METHOD_NOT_FOUND, f"method not found: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": handler(params)}
        except MCPError as exc:
            return _error(request_id, exc.code, str(exc))
        except Exception as exc:  # never let one request stop the server
            logger.exception("MCP request %s failed", method)
            return _error(request_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")

    def _initialize(self, params: Mapping[str, Any]) -> dict:
        requested = params.get("protocolVersion")
        return {
            "protocolVersion": requested if requested in SUPPORTED_VERSIONS else PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self.name, "version": _version()},
            "instructions": self.instructions,
        }

    def _list_tools(self, params: Mapping[str, Any]) -> dict:
        return {"tools": [tool.mcp_schema() for tool in self.catalog.values()]}

    def _call_tool(self, params: Mapping[str, Any]) -> dict:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise MCPError("tools/call needs a 'name' string and an 'arguments' object", INVALID_PARAMS)
        if name not in self.catalog:
            raise MCPError(f"unknown tool: {name}", INVALID_PARAMS)
        with contextlib.redirect_stdout(sys.stderr):  # stdout carries the protocol
            result = self.executor.call(name, arguments)
        content = result.content()
        return {
            "content": [{"type": "text", "text": json.dumps(content, ensure_ascii=False)}],
            "structuredContent": content,
            "isError": not result.ok,
        }

    def serve(self, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> None:
        """Answer newline-delimited JSON-RPC messages until ``stdin`` closes.  Logs go to stderr."""
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                response = _error(None, PARSE_ERROR, f"parse error: {exc}")
            else:
                response = self.handle(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                stdout.flush()


def _error(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
