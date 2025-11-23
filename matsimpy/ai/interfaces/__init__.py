"""
AI protocol interfaces.

This module provides interfaces for different AI protocols:
- MCP: Model Context Protocol
- (Future: OpenAI, Anthropic, Local models, etc.)
"""

from .mcp import MCPInterface

__all__ = ["MCPInterface"]
