"""
Extending the MatSimPy AI agent, offline (no API key needed).

1. Add a tool: decorate a function with ``@tool``; its signature and docstring are the schema.
2. Add a Skill: a folder with SKILL.md (and optionally tools.py), see skills/cubic-supercell.
3. Use MCP: MatSimPy serves its tools over MCP and connects to servers listed in mcp.json.
4. Run the agent loop with a stand-in model, to show what a real model would see and do.

Run from the repository root:  python -m examples.ai.extending
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from matsimpy.ai import Agent, MCPClient, MCPServerConfig, SkillLibrary, ToolCatalog, ToolExecutor, load_config
from matsimpy.ai.provider import ChatMessage, ChatResponse, ToolCall
from matsimpy.ai.skills import validate
from matsimpy.core import Crystal
from matsimpy.utils.tooling import tool

HERE = Path(__file__).resolve().parent
workspace = Path(tempfile.mkdtemp(prefix="matsimpy-ai-"))

# ---------------------------------------------------------------------------- 1. a tool
print("1. A custom tool")


@tool
def density(crystal: Crystal) -> dict:
    """Mass density of a crystal.

    Args:
        crystal: The crystal.

    Returns:
        The density in g/cm^3.
    """
    return {"density_g_cm3": round(float(crystal.density), 3)}


catalog = ToolCatalog.default()          # every @tool in MatSimPy
catalog.add(density)
print(f"   {len(catalog)} tools; schema of 'density':")
print("   " + json.dumps(catalog["density"].openai_schema()["function"]["parameters"]))

executor = ToolExecutor(catalog, workspace)
built = executor.call("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})
print(f"   from_prototype -> {built.content()['structure_ref']} ({built.content()['formula']})")
print(f"   density -> {executor.call('density', {'crystal': 'structure:1'}).content()}")
print(f"   a bad call -> {executor.call('density', {'crystal': 42}).content()}")

# ---------------------------------------------------------------------------- 2. a Skill
print("\n2. A Skill")
source = HERE / "skills" / "cubic-supercell"
print(f"   validate: {validate(source) or 'valid'}")
skills = SkillLibrary(workspace, user=workspace / "user-skills")
skills.install(source)                   # like `matsimpy-ai skills install <folder>`
print("   discovered: " + ", ".join(f"{s.name} ({s.source})" for s in skills.discover()))
skill = skills.activate("cubic-supercell")
print(f"   activated: {len(skill.instructions)} characters of instructions, tools {[t.name for t in skill.tools]}")
catalog.extend(skill.tools)
print(f"   cubic_supercell_matrix -> {executor.call('cubic_supercell_matrix', {'crystal': 'structure:1'}).value}")

# ---------------------------------------------------------------------------- 3. MCP
print("\n3. MCP")
servers = load_config([HERE / "mcp.json"])
print("   mcp.json: " + ", ".join(f"{n} ({'on' if c.enabled else 'off'})" for n, c in servers.items()))
# Start MatSimPy's own server (what `matsimpy-ai mcp serve` runs) and talk to it as a client.
server = MCPServerConfig("matsimpy", command=sys.executable, cwd=str(HERE.parents[1]),
                         args=("-m", "matsimpy.ai.cli", "mcp", "serve", "-w", str(workspace)))
with MCPClient(server) as client:
    print(f"   connected, protocol {client.protocol_version}, {len(client.list_tools())} tools")
    reply = client.call_tool("from_prototype", {"prototype": "bcc", "species": "Fe", "lattice_constant": 2.87})
    print(f"   from_prototype over MCP -> {reply['structuredContent']['formula']}")

# ---------------------------------------------------------------------------- 4. the agent loop
print("\n4. The agent loop, with a stand-in model")


class StandInModel:
    """Asks for one tool call, then answers. Replace with DeepSeekProvider() for a real model."""

    model = "stand-in"

    def chat(self, messages, tools=None):
        if messages[-1].role == "user":
            call = ToolCall("call_1", "from_prototype", {"prototype": "rocksalt", "species": ["Na", "Cl"],
                                                         "lattice_constant": 5.64})
            return ChatResponse(ChatMessage.assistant("", [call]), [call], "tool_calls", {})
        built = json.loads(messages[-1].content)
        return ChatResponse(ChatMessage.assistant(f"Built {built['formula']}."), [], "stop", {})


with Agent(StandInModel(), workspace=workspace, skills=skills, mcp_servers={}, memory=None) as agent:
    result = agent.run("Build rocksalt NaCl with a = 5.64 A")
    print(f"   {result.status}: {result.response}  tools={[call.name for call in result.tool_calls]}")
    print(f"   tools loaded for the model: {', '.join(agent.session.loaded_tools)} (others via search_tools/load_tools)")
    print(f"   session saved to {agent.sessions_dir / (agent.session.id + '.json')}")

shutil.rmtree(workspace)
