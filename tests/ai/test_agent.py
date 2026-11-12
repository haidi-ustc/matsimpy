"""The agent loop: tools, meta-tools, skills, MCP servers and sessions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from matsimpy import io
from matsimpy.ai.agent import SYSTEM_PROMPT, Agent
from matsimpy.ai.mcp import MCPServerConfig
from matsimpy.ai.memory import AgentMemory
from matsimpy.ai.skills import SkillLibrary

from .test_mcp import our_server
from .test_skills import TOOLS, make_skill


@pytest.fixture
def make_agent(tmp_path):
    agents = []

    def build(provider, **options):
        options.setdefault("workspace", tmp_path / "ws")
        options.setdefault("skills", SkillLibrary(options["workspace"], user=tmp_path / "skills",
                                                  packaged=tmp_path / "packaged"))
        options.setdefault("mcp_servers", {})
        agent = Agent(provider, **options)
        agents.append(agent)
        return agent

    yield build
    for agent in agents:
        agent.close()


def test_a_turn_runs_tools_until_the_model_answers(make_agent, scripted, tmp_path):
    provider = scripted(
        [("from_prototype", {"prototype": "rocksalt", "species": ["Na", "Cl"], "lattice_constant": 5.64})],
        [("write_structure", {"structure": "structure:1", "filename": "nacl.cif"})],
        "Built rocksalt NaCl and saved nacl.cif.",
    )
    events = []
    agent = make_agent(provider, on_event=lambda event, data: events.append((event, data["name"])))
    result = agent.run("Build rocksalt NaCl, a=5.64, save nacl.cif")

    assert result.status == "success" and result.response == "Built rocksalt NaCl and saved nacl.cif."
    assert result.tools == ("from_prototype", "write_structure")
    assert all(call.ok for call in result.tool_calls)
    assert result.tool_calls[0].result["structure_ref"] == "structure:1"
    assert result.usage == {"prompt_tokens": 30, "completion_tokens": 2}
    assert len(io.read(str(tmp_path / "ws" / "nacl.cif"))) == 2
    assert events == [("tool_call", "from_prototype"), ("tool_result", "from_prototype"),
                      ("tool_call", "write_structure"), ("tool_result", "write_structure")]

    # the second request carried the first tool result, as a tool message
    assert provider.tool_results(1)[0]["structure_ref"] == "structure:1"
    system = provider.requests[0]["messages"][0]
    assert system["role"] == "system" and system["content"].startswith(SYSTEM_PROMPT)
    assert "make_supercell" in system["content"]  # every tool name is listed
    assert set(provider.requests[0]["tools"]) >= {"search_tools", "load_tools", "activate_skill",
                                                  "from_prototype", "write_structure"}
    assert "make_supercell" not in provider.requests[0]["tools"]  # not loaded yet


def test_meta_tools_load_tools_for_the_next_request(make_agent, scripted):
    provider = scripted(
        [("search_tools", {"query": "supercell"})],
        [("load_tools", {"names": ["create_vacancy", "no_such_tool"]})],
        "ok",
    )
    agent = make_agent(provider)
    agent.run("make a supercell with a vacancy")
    found = provider.tool_results(1)[0]["result"]
    assert found[0] == {"name": "make_supercell", "description": "Create supercell from unit cell."}
    assert "make_supercell" in provider.requests[1]["tools"]
    assert provider.tool_results(2)[1] == {"loaded": ["create_vacancy"], "unknown": ["no_such_tool"]}
    assert "create_vacancy" in provider.requests[2]["tools"]


def test_failed_tools_are_reported_to_the_model_which_can_recover(make_agent, scripted):
    provider = scripted(
        [("from_prototype", {"prototype": "unobtainium", "species": "Cu", "lattice_constant": 3.61}),
         ("translate", {"structure": "structure:1", "vector": [0, 0, 1]})],  # an unloaded tool is still run
        [("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})],
        "Recovered with fcc Cu.",
    )
    agent = make_agent(provider)
    result = agent.run("try unobtainium, else fcc")
    assert [call.ok for call in result.tool_calls] == [False, False, True]
    errors = provider.tool_results(1)
    assert errors[0]["error"].startswith("ValueError: Unknown prototype 'unobtainium'")
    assert errors[1]["error"].startswith("unknown structure reference")
    assert result.status == "success"
    assert "translate" in agent.session.loaded_tools


def test_structures_carry_over_between_turns_and_sessions_resume(make_agent, scripted, tmp_path):
    provider = scripted(
        [("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})],
        "Built.",
        [("load_tools", {"names": ["make_supercell"]})],
        [("make_supercell", {"crystal": "structure:1", "scaling_matrix": [2, 2, 2]})],
        "Made a supercell.",
    )
    agent = make_agent(provider)
    agent.run("Build fcc Cu")
    second = agent.run("Now a 2x2x2 supercell")
    assert second.tool_calls[-1].result["num_atoms"] == 8
    session_id = agent.session.id
    saved = json.loads((tmp_path / "ws" / ".matsimpy" / "sessions" / f"{session_id}.json").read_text())
    assert saved["turns"] == [0, 4] and set(saved["objects"]) == {"structure:1", "structure:2"}
    assert saved["usage"]["prompt_tokens"] == 50

    resumed = make_agent(scripted(
        [("write_structure", {"structure": "structure:2", "filename": "cu8.cif"})], "Saved."))
    assert [s["id"] for s in resumed.list_sessions()] == [session_id]
    assert resumed.list_sessions()[0]["first_request"] == "Build fcc Cu"
    resumed.resume(session_id)
    assert "make_supercell" in resumed.session.loaded_tools
    assert resumed.run("save it").tool_calls[0].ok
    assert len(io.read(str(tmp_path / "ws" / "cu8.cif"))) == 8
    # the resumed conversation is sent to the model
    assert resumed.provider.requests[0]["messages"][1]["content"] == "Build fcc Cu"
    with pytest.raises(KeyError, match="no saved session"):
        resumed.resume("missing")


def test_undo_retry_and_new_session(make_agent, scripted):
    provider = scripted("first answer", "second answer", "retried answer", "fresh")
    agent = make_agent(provider)
    agent.run("one")
    agent.run("two")
    assert agent.retry().response == "retried answer"
    assert [m["content"] for m in agent.session.messages] == ["one", "first answer", "two", "retried answer"]
    assert agent.undo() == "two"
    assert agent.session.turns == [0]
    old = agent.session.id
    agent.new_session()
    assert agent.session.id != old and agent.session.messages == []
    agent.run("hello")
    assert provider.requests[-1]["messages"][1:] == [{"role": "user", "content": "hello"}]
    agent.undo()
    with pytest.raises(ValueError, match="nothing to undo"):
        agent.undo()


def test_provider_errors_and_interrupts_leave_no_half_turn(make_agent, scripted):
    provider = scripted(
        ConnectionError("network down"),
        [("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})],
        KeyboardInterrupt(),
    )
    agent = make_agent(provider)
    failed = agent.run("build")
    assert failed.status == "error" and "ConnectionError: network down" in failed.response
    assert agent.session.messages == [] and agent.session.turns == []
    with pytest.raises(KeyboardInterrupt):
        agent.run("build again")
    assert agent.session.messages == [] and agent.session.turns == []


def test_step_limit(make_agent, scripted):
    agent = make_agent(scripted(*[[("list_workspace_files", {})]] * 3), max_steps=3)
    assert agent.run("loop").status == "max_steps"


def test_skills_are_listed_then_activated_with_their_tools(make_agent, scripted, tmp_path):
    make_skill(tmp_path / "skills", "math-help", description="Doubling numbers.", body="Use double.",
               extra="allowed-tools: make_supercell\n", files={"tools.py": TOOLS, "notes.md": "note"})
    provider = scripted(
        [("activate_skill", {"name": "math-help"})],
        [("double", {"x": 21}), ("read_skill_resource", {"skill": "math-help", "path": "notes.md"})],
        "42",
    )
    agent = make_agent(provider)
    assert "- math-help: Doubling numbers." in agent.system_text()
    result = agent.run("double 21")
    activated = provider.tool_results(1)[0]
    assert activated == {"name": "math-help", "instructions": "Use double.", "resources": ["notes.md"],
                         "tools": ["double"]}
    assert {"double", "make_supercell"} <= set(provider.requests[1]["tools"])
    assert result.tool_calls[1].result == {"result": 42}
    assert result.tool_calls[2].result == {"result": "note"}
    assert agent.session.active_skills == ["math-help"]

    # a resumed session gets the skill's tools back
    resumed = make_agent(scripted([("double", {"x": 1})], "2"))
    resumed.resume(agent.session.id)
    assert resumed.run("again").tool_calls[0].result == {"result": 2}


def test_the_agent_can_only_draft_skills(make_agent, scripted):
    provider = scripted(
        [("propose_skill", {"name": "cu-workflow", "description": "Copper workflows.",
                            "instructions": "Use from_prototype."})],
        [("activate_skill", {"name": "cu-workflow"})],
        "Drafted.",
    )
    agent = make_agent(provider)
    agent.run("remember this workflow as a skill")
    assert provider.tool_results(1)[0]["status"].startswith("awaiting user approval")
    assert provider.tool_results(2)[1]["error"] == "SkillError: unknown skill 'cu-workflow'"
    agent.skills.approve("cu-workflow")
    assert "cu-workflow" in agent.system_text()


def test_mcp_server_tools_join_the_catalog(make_agent, scripted, tmp_path):
    servers = {"remote": our_server(tmp_path / "remote-ws", name="remote"),
               "broken": MCPServerConfig("broken", command=str(tmp_path / "missing"))}
    provider = scripted(
        [("search_tools", {"query": "remote prototype"})],
        [("remote__from_prototype", {"prototype": "bcc", "species": "Fe", "lattice_constant": 2.87})],
        "Built bcc Fe on the remote server.",
    )
    warnings = []
    agent = make_agent(provider, mcp_servers=servers,
                       on_event=lambda e, d: warnings.append(d["message"]) if e == "warning" else None)
    assert "broken" in agent.mcp_errors and "unavailable" in warnings[0]
    assert agent.catalog["remote__from_prototype"].source == "mcp:remote"
    result = agent.run("build bcc Fe remotely")
    assert result.tool_calls[1].ok and result.tool_calls[1].result["formula"] == "Fe"
    assert "remote__from_prototype" in [t["name"] for t in provider.tool_results(1)[0]["result"]]
    agent.close()
    assert "remote__from_prototype" not in agent.catalog


def test_default_mcp_config_is_read_from_the_workspace(scripted, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    config = our_server(tmp_path / "remote", name="local")
    (workspace / "mcp.json").write_text(json.dumps({"mcpServers": {"local": {
        "command": config.command, "args": list(config.args), "cwd": config.cwd}}}))
    with Agent(scripted(), workspace=workspace, skills=SkillLibrary(workspace, user=None)) as agent:
        assert [client.name for client in agent.mcp_clients] == ["local"]
        assert "local__make_supercell" in agent.catalog


def test_extra_tool_modules_and_memory(make_agent, scripted, tmp_path, monkeypatch):
    (tmp_path / "lab_tools.py").write_text(
        "from matsimpy.utils.tooling import tool\n\n@tool\ndef lab_constant() -> float:\n"
        '    """The lab constant."""\n    return 4.2\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    memory = AgentMemory(tmp_path / "memory")
    memory.write("user", "Prefers CIF output.")
    agent = make_agent(scripted([("lab_constant", {})], "4.2"), tool_modules=["lab_tools"], memory=memory)
    assert agent.catalog["lab_constant"].source == "lab_tools"
    assert "Prefers CIF output." in agent.system_text()
    assert agent.run("constant?").tool_calls[0].result == {"result": 4.2}
    sys.modules.pop("lab_tools", None)


def test_call_tool_directly(make_agent, scripted):
    agent = make_agent(scripted())
    built = agent.call_tool("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})
    assert built.ok and agent.call_tool("search_tools", {"query": "slab"}).ok
    assert not agent.call_tool("nope").ok
