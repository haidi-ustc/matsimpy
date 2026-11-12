"""MCP client and server, and interoperability with the official MCP Python SDK."""

from __future__ import annotations

import io
import json
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from matsimpy.ai.mcp import (
    METHOD_NOT_FOUND,
    MCPClient,
    MCPError,
    MCPServer,
    MCPServerConfig,
    load_config,
)
from matsimpy.ai.tools import ToolCatalog, ToolError

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def our_server(workspace: Path, name: str = "matsimpy", timeout: float = 30) -> MCPServerConfig:
    """MatSimPy's own stdio server, as a subprocess."""
    code = (f"from matsimpy.ai.mcp import MCPServer; from matsimpy.ai.tools import ToolCatalog; "
            f"MCPServer(ToolCatalog.default(), {str(workspace)!r}).serve()")
    return MCPServerConfig(name, command=PYTHON, args=("-c", code), cwd=str(ROOT), timeout=timeout)


# --------------------------------------------------------------------------- configuration


def test_load_config(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "secret")
    user = tmp_path / "user.json"
    user.write_text(json.dumps({"mcpServers": {
        "local": {"command": "python", "args": ["server.py", "--key=${MY_TOKEN}"], "env": {"TOKEN": "${MY_TOKEN}"}},
        "web": {"url": "https://example.org/mcp", "headers": {"Authorization": "Bearer ${MY_TOKEN}"},
                "timeout": 5},
    }}))
    workspace = tmp_path / "ws.json"
    # a disabled server is not expanded, so it may name variables that are not set
    workspace.write_text(json.dumps({"mcpServers": {"local": {"command": "other", "disabled": True,
                                                              "env": {"X": "${NOT_SET_ANYWHERE}"}}}}))
    servers = load_config([user, workspace, tmp_path / "missing.json"])
    assert servers["web"].transport == "http" and servers["web"].headers["Authorization"] == "Bearer secret"
    assert servers["web"].timeout == 5
    assert servers["local"].command == "other" and servers["local"].enabled is False  # the later file wins
    assert servers["local"].env == {"X": "${NOT_SET_ANYWHERE}"}
    local = load_config([user])["local"]
    assert local.env == {"TOKEN": "secret"} and local.args == ("server.py", "--key=secret")


@pytest.mark.parametrize(("entry", "message"), [
    ({"command": "a", "url": "b"}, "exactly one of"),
    ({}, "exactly one of"),
    ({"command": "a", "args": "x"}, "'args' must be a list"),
    ({"command": "a", "colour": 1}, "unknown keys"),
    ({"url": "x", "type": "sse"}, "unsupported type"),
    ({"command": "a", "env": {"X": "${NOT_SET_ANYWHERE}"}}, "NOT_SET_ANYWHERE is not set"),
])
def test_config_errors_name_the_file_and_server(tmp_path, entry, message):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"s": entry}}))
    with pytest.raises(ValueError, match=message) as error:
        load_config([path])
    assert str(path) in str(error.value)
    path.write_text("{not json")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_config([path])


# --------------------------------------------------------------------------- server


@pytest.fixture
def server(tmp_path):
    return MCPServer(ToolCatalog.default(), tmp_path)


def request(server, method, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return server.handle(message)


def test_server_handshake_negotiates_the_version(server):
    reply = request(server, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                           "clientInfo": {"name": "t", "version": "1"}})
    assert reply["result"]["protocolVersion"] == "2025-06-18"
    assert reply["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert reply["result"]["serverInfo"]["name"] == "matsimpy"
    unknown = request(server, "initialize", {"protocolVersion": "1999-01-01"})
    assert unknown["result"]["protocolVersion"] == "2025-11-25"
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.initialized
    assert request(server, "ping") == {"jsonrpc": "2.0", "id": 1, "result": {}}


def test_server_lists_and_calls_tools(server, tmp_path):
    tools = request(server, "tools/list")["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"from_prototype", "write_structure", "make_supercell"} <= names
    assert all(t["inputSchema"]["type"] == "object" for t in tools)

    built = request(server, "tools/call", {"name": "from_prototype", "arguments": {
        "prototype": "fcc", "species": "Cu", "lattice_constant": 3.61}})["result"]
    assert built["isError"] is False
    assert built["structuredContent"]["structure_ref"] == "structure:1"
    assert json.loads(built["content"][0]["text"]) == built["structuredContent"]

    saved = request(server, "tools/call", {"name": "write_structure", "arguments": {
        "structure": "structure:1", "filename": "cu.cif"}})["result"]
    assert saved["isError"] is False and (tmp_path / "cu.cif").is_file()

    failed = request(server, "tools/call", {"name": "from_prototype", "arguments": {
        "prototype": "nope", "species": "Cu", "lattice_constant": 3.61}})["result"]
    assert failed["isError"] is True and "Unknown prototype" in failed["structuredContent"]["error"]


def test_server_protocol_errors(server):
    assert request(server, "tools/call", {"name": "nope"})["error"]["code"] == -32602
    assert request(server, "tools/call", {"name": 1})["error"]["code"] == -32602
    # the probe of the stateless 2026 protocol is answered "not found", so clients use the handshake
    assert request(server, "server/discover")["error"]["code"] == METHOD_NOT_FOUND
    assert request(server, "resources/list")["error"]["code"] == METHOD_NOT_FOUND
    assert server.handle({"id": 3, "method": "ping"})["error"]["code"] == -32600
    assert server.handle({"jsonrpc": "2.0", "id": 9, "result": {}}) is None
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/cancelled"}) is None

    out = io.StringIO()
    server.serve(io.StringIO('not json\n\n{"jsonrpc":"2.0","id":2,"method":"ping"}\n'), out)
    first, second = map(json.loads, out.getvalue().splitlines())
    assert first["error"]["code"] == -32700 and first["id"] is None
    assert second == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_tool_output_on_stdout_does_not_corrupt_the_protocol(tmp_path):
    def chatty() -> str:
        """Prints while running."""
        print("progress 50%")
        return "done"

    out = io.StringIO()
    MCPServer(ToolCatalog([chatty_tool(chatty)]), tmp_path).serve(
        io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"chatty"}}\n'), out)
    assert json.loads(out.getvalue())["result"]["structuredContent"] == {"result": "done"}


def chatty_tool(function):
    from matsimpy.ai.tools import Tool

    return Tool.from_function(function)


# --------------------------------------------------------------------------- client <-> server


def test_client_and_server_over_stdio(tmp_path):
    with MCPClient(our_server(tmp_path)) as client:
        assert client.protocol_version == "2025-11-25"
        assert client.server_info["name"] == "matsimpy"
        tools = {t.name: t for t in client.tools()}
        assert "matsimpy__from_prototype" in tools
        build = tools["matsimpy__from_prototype"]
        assert build.source == "mcp:matsimpy" and build.parameters["required"] == [
            "prototype", "species", "lattice_constant"]
        result = build.function(prototype="rocksalt", species=["Na", "Cl"], lattice_constant=5.64)
        assert result["structure_ref"] == "structure:1"
        # references live in the server process
        supercell = tools["matsimpy__make_supercell"].function(crystal="structure:1", scaling_matrix=[2, 2, 2])
        assert supercell["num_atoms"] == 16
        with pytest.raises(ToolError, match="Unknown prototype"):
            build.function(prototype="nope", species="Cu", lattice_constant=1.0)
        with pytest.raises(MCPError, match="unknown tool") as error:
            client.call_tool("nope")
        assert error.value.code == -32602
    assert not client.connected


FAKE_SERVER = textwrap.dedent('''
    import json, sys, time
    for line in sys.stdin:
        message = json.loads(line)
        if message.get("method") == "initialize":
            print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": {
                "protocolVersion": MODE if MODE.startswith("19") else "2025-06-18",
                "capabilities": {}, "serverInfo": {"name": "fake"}}}), flush=True)
        elif message.get("method") == "tools/list":
            if MODE == "crash":
                print("fatal: out of memory", file=sys.stderr, flush=True)
                sys.exit(3)
            if MODE == "slow":
                time.sleep(30)
            cursor = (message.get("params") or {}).get("cursor")
            page = {None: (["a"], "p2"), "p2": (["b"], None)}[cursor]
            result = {"tools": [{"name": n, "inputSchema": {"type": "object"}} for n in page[0]]}
            if page[1]:
                result["nextCursor"] = page[1]
            print(json.dumps({"jsonrpc": "2.0", "method": "notifications/message", "params": {}}), flush=True)
            print(json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"}), flush=True)
            print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
        elif "id" in message and "method" not in message:
            print("got reply", json.dumps(message), file=sys.stderr, flush=True)
''')


def fake_server(tmp_path, mode, timeout=10.0) -> MCPServerConfig:
    script = tmp_path / "fake.py"
    script.write_text(f"MODE = {mode!r}\n" + FAKE_SERVER)
    return MCPServerConfig("fake", command=PYTHON, args=(str(script),), timeout=timeout)


def test_client_pages_and_answers_server_pings(tmp_path):
    with MCPClient(fake_server(tmp_path, "ok")) as client:
        assert client.protocol_version == "2025-06-18"
        assert [t["name"] for t in client.list_tools()] == ["a", "b"]
        for _ in range(50):  # the reply to the server's ping is sent from another thread
            replies = [json.loads(line.removeprefix("got reply ")) for line in client._transport.stderr
                       if line.startswith("got reply ")]
            if replies:
                break
            time.sleep(0.05)
        assert replies == [{"jsonrpc": "2.0", "id": 99, "result": {}}]


def test_client_timeout_crash_and_bad_version(tmp_path):
    with MCPClient(fake_server(tmp_path, "slow", timeout=1)) as client:
        start = time.monotonic()
        with pytest.raises(MCPError, match="timed out after 1 s") as error:
            client.list_tools()
        assert time.monotonic() - start < 5 and error.value.code == -32001
    with MCPClient(fake_server(tmp_path, "crash")) as client:
        with pytest.raises(MCPError, match="connection closed.*out of memory"):
            client.list_tools()
    with pytest.raises(MCPError, match="speaks protocol '1999-01-01'"):
        MCPClient(fake_server(tmp_path, "1999-01-01")).connect()
    with pytest.raises(MCPError, match="cannot start"):
        MCPClient(MCPServerConfig("x", command=str(tmp_path / "missing-binary"))).connect()


# --------------------------------------------------------------------------- official SDK


SDK_SERVER = textwrap.dedent('''
    import sys
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("sdk-demo")

    @server.tool()
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @server.tool()
    def fail(message: str) -> str:
        """Always fails."""
        raise ValueError(message)

    if sys.argv[1:2] == ["http"]:
        server.run("streamable-http", host="127.0.0.1", port=int(sys.argv[2]))
    else:
        server.run()
''')


@pytest.fixture
def sdk_script(tmp_path):
    pytest.importorskip("mcp")
    script = tmp_path / "sdk_server.py"
    script.write_text(SDK_SERVER)
    return script


def check_sdk_server(client: MCPClient) -> None:
    assert client.protocol_version == "2025-11-25"
    tools = {t.name: t for t in client.tools()}
    assert set(tools) == {"sdk__add", "sdk__fail"}
    assert tools["sdk__add"].parameters["required"] == ["a", "b"]
    assert tools["sdk__add"].function(a=2, b=3) == {"result": 5}
    with pytest.raises(ToolError):
        tools["sdk__fail"].function(message="boom")


def test_our_client_with_an_sdk_stdio_server(sdk_script):
    with MCPClient(MCPServerConfig("sdk", command=PYTHON, args=(str(sdk_script),), timeout=30)) as client:
        check_sdk_server(client)


def test_our_client_with_an_sdk_streamable_http_server(sdk_script):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen([PYTHON, str(sdk_script), "http", str(port)], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        config = MCPServerConfig("sdk", url=f"http://127.0.0.1:{port}/mcp", timeout=30)
        with MCPClient(config) as client:
            assert client._transport.session_id  # the server's session header is echoed
            check_sdk_server(client)
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_sdk_client_with_our_stdio_server(tmp_path):
    """The SDK client probes the 2026 protocol first and falls back to our handshake."""
    pytest.importorskip("mcp")
    import anyio
    from mcp import Client, StdioServerParameters

    config = our_server(tmp_path)
    params = StdioServerParameters(command=config.command, args=list(config.args), cwd=config.cwd)

    async def session():
        async with Client(params) as client:
            assert client.protocol_version == "2025-11-25"
            listed = await client.list_tools()
            assert "from_prototype" in {t.name for t in listed.tools}
            built = await client.call_tool("from_prototype", {"prototype": "fcc", "species": "Cu",
                                                              "lattice_constant": 3.61})
            assert built.is_error is False and built.structured_content["structure_ref"] == "structure:1"
            saved = await client.call_tool("write_structure", {"structure": "structure:1", "filename": "cu.cif"})
            assert saved.is_error is False
            failed = await client.call_tool("from_prototype", {"prototype": "nope", "species": "Cu",
                                                               "lattice_constant": 3.61})
            assert failed.is_error is True

    anyio.run(session)
    assert (tmp_path / "cu.cif").is_file()
