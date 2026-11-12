"""Provider parsing, REPL commands, terminal, CLI and doctor."""

from __future__ import annotations

import json
import sys

import pytest

from matsimpy.ai.agent import Agent
from matsimpy.ai.doctor import Doctor, render_diagnostics
from matsimpy.ai.provider import ChatMessage, DeepSeekProvider, ToolCall, parse_chat_completion
from matsimpy.ai.repl import ReplController
from matsimpy.ai.skills import PACKAGED_SKILLS, SkillLibrary
from matsimpy.ai.terminal import PlainTerminal, format_event

from .test_mcp import ROOT, our_server
from .test_skills import make_skill

typer_testing = pytest.importorskip("typer.testing")


# --------------------------------------------------------------------------- provider


def test_parse_chat_completion_with_tool_calls():
    response = parse_chat_completion({
        "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "translate", "arguments": '{"vector": [1, 0, 0]}'}},
            {"id": "c2", "type": "function", "function": {"name": "broken", "arguments": "{not json"}},
        ]}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15, "details": {}},
    })
    assert response.finish_reason == "tool_calls" and response.message.content == ""
    assert response.tool_calls[0] == ToolCall("c1", "translate", {"vector": [1, 0, 0]})
    # invalid JSON reaches the executor as an argument it rejects, so the model sees the problem
    assert response.tool_calls[1].arguments == {"__invalid_json__": "{not json"}
    assert response.usage == {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}
    assert response.message.to_dict()["tool_calls"][0]["function"]["arguments"] == '{"vector": [1, 0, 0]}'
    assert ChatMessage.from_dict(response.message.to_dict()) == response.message


def test_deepseek_provider_request(monkeypatch):
    sent = {}

    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]}

    def post(url, json, headers, timeout):
        sent.update(url=url, payload=json, headers=headers)
        return Reply()

    monkeypatch.setattr("requests.post", post)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider()
    provider = DeepSeekProvider("key", "deepseek-v4-flash", "https://example.org/")
    tools = [{"type": "function", "function": {"name": "t", "parameters": {"type": "object"}}}]
    assert provider.chat([ChatMessage.user("hello")], tools).message.content == "hi"
    assert sent["url"] == "https://example.org/v1/chat/completions"
    assert sent["payload"]["model"] == "deepseek-v4-flash" and sent["payload"]["tool_choice"] == "auto"
    assert sent["headers"]["Authorization"] == "Bearer key"


# --------------------------------------------------------------------------- REPL


@pytest.fixture
def agent(tmp_path, scripted):
    agent = Agent(scripted("an answer", "retried", "after skill"), workspace=tmp_path / "ws",
                  skills=SkillLibrary(tmp_path / "ws", user=tmp_path / "skills", packaged=PACKAGED_SKILLS),
                  mcp_servers={"remote": our_server(tmp_path / "remote")})
    yield agent
    agent.close()


def test_repl_commands(agent, tmp_path):
    repl = ReplController(agent)
    assert "/resume" in repl.execute("/help").text
    assert repl.complete("/re") == ("/reject", "/resume", "/retry")
    assert not repl.execute("/nope").ok

    assert repl.execute("/sessions").text == "No saved sessions."
    agent.run("first")
    assert agent.session.id in repl.execute("/sessions").text
    assert repl.execute("/retry").text == "retried"
    assert repl.execute("/undo").text == "Removed the turn: first"
    assert repl.execute("/undo").ok is False
    assert repl.execute("/usage").data == {"prompt_tokens": 20, "completion_tokens": 4}
    saved = repl.execute(f"/save {tmp_path / 'copy.json'}")
    assert saved.ok and json.loads((tmp_path / "copy.json").read_text())["id"] == agent.session.id
    old = agent.session.id
    assert repl.execute("/new").ok and agent.session.id != old
    assert repl.execute(f"/resume {old}").text.startswith(f"Resumed {old}")
    assert repl.execute("/resume nope").ok is False

    assert "make_supercell" in repl.execute("/tools supercell").text
    assert repl.execute("/tool make_supercell").data.name == "make_supercell"
    assert repl.execute("/tools reload").ok
    assert "remote (stdio, protocol 2025-11-25): remote__" in repl.execute("/mcp").text
    assert repl.execute("/model other-model").text == "Model: other-model"
    assert str(agent.workspace.path) in repl.execute("/workspace").text
    assert repl.execute("/quit").exit


def test_repl_skill_commands(agent, tmp_path):
    repl = ReplController(agent)
    assert "vasp-inputs (packaged)" in repl.execute("/skills").text
    activated = repl.execute("/skill vasp-inputs")
    assert activated.text == "Activated vasp-inputs. Tools: kpoint_mesh."
    assert agent.session.messages[-1]["content"].startswith("[I activated the skill vasp-inputs.")
    assert "* vasp-inputs" in repl.execute("/skills").text

    source = make_skill(tmp_path / "src", "my-skill")
    assert repl.execute(f"/skills validate {source}").text == "Valid."
    assert repl.execute(f"/skills install {source}").ok
    assert repl.execute(f"/skills install {source}").ok is False
    assert repl.execute(f"/skills install {source} --replace").ok
    assert repl.execute("/skills remove my-skill").ok
    assert not repl.execute("/skills frobnicate").ok

    agent.skills.create_draft("draft-one", "A draft.", "Do it.")
    assert repl.execute("/drafts").text == "draft-one: A draft."
    assert repl.execute("/drafts draft-one").text.endswith("Do it.")
    assert repl.execute("/approve draft-one").ok
    agent.skills.create_draft("draft-two", "Another.", "x")
    assert repl.execute("/reject draft-two").ok and repl.execute("/drafts").text == "No drafts."


def test_plain_terminal(agent):
    lines = iter(["", "/usage", "hello", "/quit"])
    output = []
    PlainTerminal(ReplController(agent), input_reader=lambda prompt: next(lines), output_writer=output.append).run()
    assert output == [output[0], "No usage yet.", "an answer", "Goodbye."]

    output.clear()
    PlainTerminal(ReplController(agent), input_reader=lambda p: (_ for _ in ()).throw(EOFError()),
                  output_writer=output.append).run()
    assert output[-1] == "Goodbye."


def test_format_event():
    assert format_event("tool_call", {"name": "t", "arguments": {"a": 1}}) == '  → t {"a": 1}'
    assert format_event("tool_result", {"name": "t", "ok": False, "result": {"error": "bad"}}) == "  ✗ t: bad"
    assert format_event("tool_result", {"name": "t", "ok": True, "result": {}}) is None


# --------------------------------------------------------------------------- doctor and CLI


def test_doctor_offline_and_network(tmp_path):
    workspace = tmp_path / "ws"
    make_skill(workspace / ".matsimpy" / "skills", "Bad_Name")
    (tmp_path / "mcp.json").write_text(json.dumps({"mcpServers": {"remote": {
        "command": our_server(tmp_path).command, "args": list(our_server(tmp_path).args),
        "cwd": our_server(tmp_path).cwd}}}))
    doctor = Doctor(workspace=workspace, environ={}, mcp_config=[tmp_path / "mcp.json"],
                    skills=SkillLibrary(workspace, user=tmp_path / "user"))
    offline = {d.code: d for d in doctor.run()}
    assert offline["provider-api-key"].status == "warn"
    assert offline["tools"].status == "pass" and offline["tools"].summary.endswith("tools")
    assert offline["skills"].status in {"pass", "warn"}
    assert offline["mcp:remote"].summary.startswith("stdio")
    assert "not connected" in offline["mcp:remote"].summary

    def failing_probe():
        raise RuntimeError("Authorization: Bearer sk-secret")

    online = Doctor(workspace=workspace, environ={"DEEPSEEK_API_KEY": "sk-secret"},
                    mcp_config=[tmp_path / "mcp.json"], network_probe=failing_probe,
                    skills=SkillLibrary(workspace, user=tmp_path / "user")).run(network=True)
    text = render_diagnostics(online)
    assert "sk-secret" not in text
    assert "[FAIL] provider-network" in text
    assert "connected (protocol 2025-11-25)" in text


def test_doctor_reports_bad_mcp_config(tmp_path):
    (tmp_path / "mcp.json").write_text('{"mcpServers": {"x": {}}}')
    (diagnostic,) = [d for d in Doctor(workspace=tmp_path, environ={}, mcp_config=[tmp_path / "mcp.json"]).run()
                     if d.code == "mcp-config"]
    assert diagnostic.status == "fail" and "exactly one of" in diagnostic.summary


def test_cli(tmp_path, monkeypatch, scripted):
    from matsimpy.ai import cli

    runner = typer_testing.CliRunner()
    result = runner.invoke(cli.app, ["tools", "list", "supercell"])
    assert result.exit_code == 0 and result.output.startswith("make_supercell:")
    shown = runner.invoke(cli.app, ["tools", "show", "make_supercell"])
    assert json.loads(shown.output)["name"] == "make_supercell"
    assert runner.invoke(cli.app, ["tools", "show", "nope"]).exit_code == 1

    workspace = str(tmp_path / "ws")
    source = make_skill(tmp_path / "src", "cli-skill")
    assert runner.invoke(cli.app, ["skills", "validate", str(source)]).output.strip() == "Valid."
    installed = runner.invoke(cli.app, ["skills", "install", str(source), "-w", workspace])
    assert installed.exit_code == 0, installed.output
    assert "cli-skill (user)" in runner.invoke(cli.app, ["skills", "list", "-w", workspace]).output
    assert runner.invoke(cli.app, ["skills", "install", str(source), "-w", workspace]).exit_code == 1
    assert runner.invoke(cli.app, ["skills", "remove", "cli-skill", "-w", workspace]).exit_code == 0

    doctor = runner.invoke(cli.app, ["doctor", "-w", workspace])
    assert "[PASS] tools" in doctor.output

    def build(*args, **kwargs):
        return Agent(scripted("Done."), workspace=workspace, mcp_servers={})

    monkeypatch.setattr(cli, "build_agent", build)
    one_shot = runner.invoke(cli.app, ["-c", "do it"])
    assert one_shot.exit_code == 0 and one_shot.output.strip() == "Done."


def test_cli_mcp_serve_is_a_working_server(tmp_path):
    from matsimpy.ai.mcp import MCPClient, MCPServerConfig

    config = MCPServerConfig("cli", command=sys.executable, timeout=60, cwd=str(ROOT),
                             args=("-m", "matsimpy.ai.cli", "mcp", "serve", "-w", str(tmp_path)))
    with MCPClient(config) as client:
        result = client.call_tool("from_prototype", {"prototype": "sc", "species": "Po", "lattice_constant": 3.35})
    assert result["structuredContent"]["formula"] == "Po"
