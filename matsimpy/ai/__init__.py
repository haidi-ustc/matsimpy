"""MatSimPy's AI agent: an LLM that works through MatSimPy tools.

- :mod:`~matsimpy.ai.tools`: tools derived from Python functions
  (:class:`ToolCatalog`, :class:`ToolExecutor`).  Mark a function with
  :func:`matsimpy.utils.tooling.tool` to make it a tool.
- :mod:`~matsimpy.ai.skills`: Agent Skills, loaded progressively.
- :mod:`~matsimpy.ai.mcp`: MCP client (stdio, HTTP) and stdio server.
- :mod:`~matsimpy.ai.agent`: the agent loop and JSON sessions.
- ``matsimpy-ai``: REPL, one-shot tasks, ``doctor``, ``skills``, ``tools`` and ``mcp`` commands.

Example::

    from matsimpy.ai import Agent

    with Agent(workspace="project") as agent:
        print(agent.run("Build rocksalt NaCl with a=5.64 and save it as nacl.cif").response)

The default provider needs ``DEEPSEEK_API_KEY``; any object with a
``chat(messages, tools)`` method (:class:`ChatProvider`) can be passed instead.
"""

from .agent import Agent, AgentResult, Session, ToolRecord
from .doctor import Diagnostic, Doctor
from .mcp import MCPClient, MCPError, MCPServer, MCPServerConfig, load_config
from .memory import AgentMemory
from .provider import ChatMessage, ChatProvider, ChatResponse, DeepSeekProvider, ToolCall
from .repl import CommandResult, ReplController
from .skills import Skill, SkillError, SkillLibrary, SkillSummary
from .tools import Tool, ToolCatalog, ToolContext, ToolError, ToolExecutor, ToolResult

__all__ = [
    "Agent", "AgentResult", "AgentMemory", "ChatMessage", "ChatProvider", "ChatResponse", "CommandResult",
    "DeepSeekProvider", "Diagnostic", "Doctor", "MCPClient", "MCPError", "MCPServer", "MCPServerConfig",
    "ReplController", "Session", "Skill", "SkillError", "SkillLibrary", "SkillSummary", "Tool", "ToolCall",
    "ToolCatalog", "ToolContext", "ToolError", "ToolExecutor", "ToolRecord", "ToolResult", "load_config",
]
