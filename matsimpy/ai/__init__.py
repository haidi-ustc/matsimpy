"""
AI module for MatSimPy.

Provides AI interfaces and operations for structure generation,
prediction, analysis, and optimization.

This module supports multiple AI protocols:
- MCP (Model Context Protocol) - Primary interface
- (Future: OpenAI, Anthropic, Local models)

Examples:
    >>> from matsimpy.ai import MCPInterface, AIGeneration, get_ai_interface
    >>>
    >>> # Direct usage
    >>> mcp = MCPInterface(transport="stdio")
    >>> mcp.connect({"command": "python", "args": ["server.py"]})
    >>> gen = AIGeneration(mcp)
    >>> structure = gen.generate_from_composition("TiO2")
    >>> mcp.disconnect()
    >>>
    >>> # Factory pattern
    >>> ai = get_ai_interface("mcp", transport="stdio")
    >>> ai.connect({"command": "python", "args": ["server.py"]})
    >>> gen = AIGeneration(ai)
    >>> structure = gen.generate_from_description("diamond silicon")
"""

# Base classes
from .base import AIInterface, AIOperation

# Protocol interfaces
from .interfaces import MCPInterface

# Operations
from .operations import AIGeneration, PropertyPrediction, AIAnalysis, AIOptimization

# Utilities
from .utils import get_ai_interface, list_available_protocols, prompts, formatting

# Models
from .models import ModelRegistry, ResponseCache, cached

__all__ = [
    # Base classes
    "AIInterface",
    "AIOperation",
    # Interfaces
    "MCPInterface",
    # Operations
    "AIGeneration",
    "PropertyPrediction",
    "AIAnalysis",
    "AIOptimization",
    # Utilities
    "get_ai_interface",
    "list_available_protocols",
    "prompts",
    "formatting",
    # Models
    "ModelRegistry",
    "ResponseCache",
    "cached",
]
