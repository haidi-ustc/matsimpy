"""
AI module for MatSimPy — LLM function calling + interactive REPL.

Provides:
- AIEngine: orchestrates LLM conversation with tool execution
- DeepSeekProvider: OpenAI-compatible client for DeepSeek API
- SkillManager: progressive skill loading (like Claude skills)
- FunctionDef/Skill: metadata for LLM-callable functions
- FunctionExecutor: validates parameters and executes tool calls
- Interactive REPL with /commands

Usage::

    >>> from matsimpy.ai import AIEngine
    >>> engine = AIEngine()
    >>> engine.skill_manager.load("builders")
    >>> response = engine.chat("Create an FCC copper crystal")
    >>> print(response)

    # Or launch the interactive REPL:
    >>> from matsimpy.ai.cli import main
    >>> main()

Requirements:
    - requests
    - DEEPSEEK_API_KEY environment variable (or pass api_key= to AIEngine)
"""

from .conversation import ChatMessage, ToolCall, ChatResponse
from .skill import FunctionDef, Skill, SkillManager
from .provider import DeepSeekProvider
from .executor import FunctionExecutor
from .engine import AIEngine

__all__ = [
    "AIEngine",
    "DeepSeekProvider",
    "SkillManager",
    "FunctionDef",
    "Skill",
    "FunctionExecutor",
    "ChatMessage",
    "ToolCall",
    "ChatResponse",
]
