"""
AI utilities module.

Provides utility functions for AI operations:
- get_ai_interface: Factory function for AI interfaces
- list_available_protocols: List available protocols
- Prompt templates and formatting utilities
"""

from typing import Dict, Any, Optional, List
from ..base import AIInterface
from ..interfaces import MCPInterface
from . import prompts
from . import formatting

_PROTOCOL_REGISTRY = {
    "mcp": MCPInterface,
    # Future protocols can be added here
    # "openai": OpenAIInterface,
    # "anthropic": AnthropicInterface,
    # "local": LocalModelInterface,
}


def get_ai_interface(protocol: str, 
                     config: Optional[Dict[str, Any]] = None,
                     **kwargs) -> AIInterface:
    """
    Factory function to get AI interface instance.
    
    Args:
        protocol: Protocol name ('mcp', 'openai', etc.)
        config: Configuration dictionary
        **kwargs: Additional parameters passed to interface constructor
    
    Returns:
        AIInterface instance
    
    Raises:
        ValueError: If protocol not supported
    
    Examples:
        >>> # Get MCP interface
        >>> mcp = get_ai_interface("mcp", transport="stdio")
        >>> mcp.connect({"command": "python", "args": ["server.py"]})
        >>> 
        >>> # Get OpenAI interface (future)
        >>> # openai = get_ai_interface("openai", api_key="...")
    """
    protocol_lower = protocol.lower()
    
    if protocol_lower not in _PROTOCOL_REGISTRY:
        available = ", ".join(_PROTOCOL_REGISTRY.keys())
        raise ValueError(
            f"Unsupported protocol '{protocol}'. "
            f"Available protocols: {available}"
        )
    
    interface_class = _PROTOCOL_REGISTRY[protocol_lower]
    return interface_class(**kwargs)


def list_available_protocols() -> List[str]:
    """
    List all available AI protocols.
    
    Returns:
        List of protocol names
    
    Examples:
        >>> protocols = list_available_protocols()
        >>> print(protocols)
        ['mcp']
    """
    return list(_PROTOCOL_REGISTRY.keys())


__all__ = [
    'get_ai_interface',
    'list_available_protocols',
    'prompts',
    'formatting',
]

