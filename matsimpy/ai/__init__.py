"""
AI module for MatSimPy — LLM function calling + interactive REPL.

Provides:
- Agent: simple, structured Python interface
- AIEngine: deprecated REPL compatibility interface
- DeepSeekProvider: OpenAI-compatible client for DeepSeek API
- SkillManager: progressive skill loading (like Claude skills)
- FunctionDef/Skill: metadata for LLM-callable functions
- FunctionExecutor: validates parameters and executes tool calls
- Interactive REPL with /commands

Usage::

    >>> from matsimpy.ai import Agent
    >>> result = Agent(workspace="project").run("Create an FCC copper crystal")
    >>> print(result.response)

    # Or launch the interactive REPL:
    >>> from matsimpy.ai.cli import main
    >>> main()

Requirements:
    - requests
    - DEEPSEEK_API_KEY environment variable (or inject a provider into Agent)
"""

from .conversation import ChatMessage, ToolCall, ChatResponse
from .skill import FunctionDef, Skill, SkillManager
from .provider import DeepSeekProvider
from .providers import ChatProvider
from .executor import FunctionExecutor
from .runtime import AgentRuntime, TaskResult
from .session_store import SessionStore, SkillVersion
from .session import AgentSession, SessionTurn
from .agent import Agent, AgentResult
from .repl import CommandResult, ReplController
from .terminal import (
    PlainTerminal,
    PromptToolkitTerminal,
    TerminalFrontend,
    create_terminal,
)
from .engine import AIEngine
from .doctor import Diagnostic, Doctor
from .evolution import (
    EvolutionCandidate,
    EvolutionManager,
    EvolutionPolicy,
    SkillEvolutionError,
)
from .memory import AgentMemory, MemoryEntry, MemoryValidationError

__all__ = [
    "AIEngine",
    "Agent",
    "AgentResult",
    "CommandResult",
    "ReplController",
    "TerminalFrontend",
    "PlainTerminal",
    "PromptToolkitTerminal",
    "create_terminal",
    "AgentRuntime",
    "ChatProvider",
    "DeepSeekProvider",
    "Diagnostic",
    "Doctor",
    "EvolutionCandidate",
    "EvolutionManager",
    "EvolutionPolicy",
    "SkillEvolutionError",
    "SkillVersion",
    "AgentMemory",
    "MemoryEntry",
    "MemoryValidationError",
    "TaskResult",
    "SessionStore",
    "AgentSession",
    "SessionTurn",
    "SkillManager",
    "FunctionDef",
    "Skill",
    "FunctionExecutor",
    "ChatMessage",
    "ToolCall",
    "ChatResponse",
]
