# AI Module Architecture Proposal

## Overview

This document proposes a comprehensive AI module structure for MatSimPy that supports:
- **MCP (Model Context Protocol)** integration
- **Future extensibility** for other AI interfaces and methods
- **Multiple AI operations** (generation, prediction, analysis, optimization)
- **Unified interface** similar to existing `code/` module pattern

## Proposed Structure

```
matsimpy/ai/
├── __init__.py              # Unified exports
├── base.py                  # Base classes for AI interfaces
├── interfaces/              # AI protocol interfaces
│   ├── __init__.py
│   ├── mcp.py              # MCP (Model Context Protocol) interface
│   ├── openai.py            # OpenAI API (future)
│   ├── anthropic.py         # Anthropic API (future)
│   └── local.py             # Local model inference (future)
├── operations/              # AI operation types
│   ├── __init__.py
│   ├── generation.py        # Structure generation via AI
│   ├── prediction.py        # Property prediction
│   ├── analysis.py           # AI-assisted analysis
│   └── optimization.py      # Structure optimization
├── models/                  # Model management
│   ├── __init__.py
│   ├── registry.py          # Model registry
│   └── cache.py             # Model caching
└── utils/                   # AI utilities
    ├── __init__.py
    ├── prompts.py           # Prompt templates
    └── formatting.py        # Input/output formatting
```

## Design Principles

### 1. **Protocol Abstraction**
- Base classes for different AI protocols (MCP, REST API, Local, etc.)
- Easy to add new protocols without changing operation code

### 2. **Operation-Based Organization**
- Separate concerns: generation, prediction, analysis, optimization
- Each operation can use any compatible protocol

### 3. **Extensibility First**
- Plugin architecture for new models
- Configuration-driven approach
- Easy to add new operations

### 4. **Consistency with Existing Code**
- Follows `code/` module pattern (base classes)
- Similar to `builders/` organization (by functionality)

## Base Classes

### AIInterface (Base Protocol Interface)

```python
# matsimpy/ai/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..core import Crystal, Molecule

class AIInterface(ABC):
    """Base class for AI protocol interfaces."""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to AI service."""
        pass
    
    @abstractmethod
    def call(self, 
             operation: str,
             inputs: Dict[str, Any],
             **kwargs) -> Dict[str, Any]:
        """Call AI operation."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from service."""
        pass
```

### Operation Base Classes

```python
# matsimpy/ai/operations/base.py
class AIOperation(ABC):
    """Base class for AI operations."""
    
    def __init__(self, interface: AIInterface):
        self.interface = interface
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the operation."""
        pass
```

## MCP Implementation

### MCP Interface

```python
# matsimpy/ai/interfaces/mcp.py
from typing import Dict, Any, Optional
import json
from ..base import AIInterface

class MCPInterface(AIInterface):
    """
    Model Context Protocol (MCP) interface.
    
    MCP is a protocol for interacting with AI models through
    standardized tools and resources.
    """
    
    def __init__(self, server_url: Optional[str] = None,
                 transport: str = "stdio"):
        """
        Initialize MCP interface.
        
        Args:
            server_url: MCP server URL (if using HTTP transport)
            transport: Transport type ('stdio', 'http', 'websocket')
        """
        self.server_url = server_url
        self.transport = transport
        self._connected = False
        self._client = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to MCP server."""
        # Implementation depends on MCP client library
        # For example: mcp-client-python
        try:
            if self.transport == "stdio":
                # Connect via stdio
                self._client = self._connect_stdio(config)
            elif self.transport == "http":
                # Connect via HTTP
                self._client = self._connect_http(config)
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")
            
            self._connected = True
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP server: {e}")
    
    def call(self, 
             operation: str,
             inputs: Dict[str, Any],
             **kwargs) -> Dict[str, Any]:
        """
        Call MCP tool/function.
        
        Args:
            operation: Tool name or function identifier
            inputs: Input parameters for the tool
            **kwargs: Additional parameters
        
        Returns:
            Tool execution result
        """
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")
        
        # Format request according to MCP spec
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": operation,
                "arguments": inputs
            },
            "id": kwargs.get("request_id", 1)
        }
        
        # Send request and get response
        response = self._client.call(request)
        return response
    
    def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._client:
            self._client.close()
        self._connected = False
```

## AI Operations

### Structure Generation

```python
# matsimpy/ai/operations/generation.py
from typing import List, Optional
from ..base import AIInterface
from ...core import Crystal, Molecule

class AIGeneration(AIOperation):
    """AI-based structure generation."""
    
    def generate_from_composition(self,
                                  composition: str,
                                  constraints: Optional[Dict] = None) -> Crystal:
        """
        Generate crystal structure from composition using AI.
        
        Args:
            composition: Chemical formula (e.g., "TiO2")
            constraints: Optional constraints (space group, lattice params, etc.)
        
        Returns:
            Generated crystal structure
        """
        prompt = self._format_generation_prompt(composition, constraints)
        
        result = self.interface.call(
            operation="generate_structure",
            inputs={"prompt": prompt, "composition": composition}
        )
        
        # Parse result and create Crystal object
        return self._parse_structure_result(result)
    
    def generate_from_description(self, description: str) -> Crystal:
        """Generate structure from natural language description."""
        result = self.interface.call(
            operation="generate_from_text",
            inputs={"description": description}
        )
        return self._parse_structure_result(result)
```

### Property Prediction

```python
# matsimpy/ai/operations/prediction.py
class PropertyPrediction(AIOperation):
    """AI-based property prediction."""
    
    def predict_band_gap(self, crystal: Crystal) -> float:
        """Predict band gap using AI model."""
        structure_data = self._format_structure(crystal)
        
        result = self.interface.call(
            operation="predict_band_gap",
            inputs={"structure": structure_data}
        )
        
        return result.get("band_gap", 0.0)
    
    def predict_formation_energy(self, crystal: Crystal) -> float:
        """Predict formation energy."""
        # Similar implementation
        pass
```

## Usage Examples

### Basic MCP Setup

```python
from matsimpy.ai import MCPInterface, AIGeneration

# Initialize MCP interface
mcp = MCPInterface(transport="stdio")

# Connect (configure with your MCP server)
config = {
    "command": "python",
    "args": ["path/to/mcp_server.py"]
}
mcp.connect(config)

# Use for generation
gen = AIGeneration(mcp)
structure = gen.generate_from_composition("TiO2", constraints={"space_group": 136})

# Cleanup
mcp.disconnect()
```

### Unified Interface (Factory Pattern)

```python
from matsimpy.ai import get_ai_interface, AIGeneration

# Factory function to get appropriate interface
ai = get_ai_interface(
    protocol="mcp",
    config={"transport": "stdio", "command": "python", "args": ["server.py"]}
)

# Operations work with any interface
gen = AIGeneration(ai)
structure = gen.generate_from_composition("SiC")
```

### Future: Multiple Protocols

```python
# Same operations, different protocols
mcp_interface = get_ai_interface("mcp", config1)
openai_interface = get_ai_interface("openai", config2)
local_interface = get_ai_interface("local", config3)

# All work the same way
gen1 = AIGeneration(mcp_interface)
gen2 = AIGeneration(openai_interface)
gen3 = AIGeneration(local_interface)
```

## Future Expansion Points

### 1. Additional Protocols
- **OpenAI API**: Direct API integration
- **Anthropic Claude**: Anthropic API
- **Local Models**: HuggingFace, Ollama, etc.
- **Custom Protocols**: User-defined interfaces

### 2. Additional Operations
- **Optimization**: AI-guided structure optimization
- **Analysis**: AI-assisted analysis workflows
- **Validation**: AI-based structure validation
- **Recommendation**: Suggest similar structures

### 3. Advanced Features
- **Batch Processing**: Process multiple structures
- **Caching**: Cache model responses
- **Streaming**: Stream large responses
- **Async Support**: Asynchronous operations

### 4. Integration Points
- **With builders/**: AI-guided structure building
- **With analysis/**: AI-enhanced analysis
- **With transformation/**: AI-suggested transformations

## Module Exports

```python
# matsimpy/ai/__init__.py
"""
AI module for MatSimPy.

Provides AI interfaces and operations for structure generation,
prediction, analysis, and optimization.
"""

from .base import AIInterface, AIOperation
from .interfaces.mcp import MCPInterface
from .operations.generation import AIGeneration
from .operations.prediction import PropertyPrediction
from .utils import get_ai_interface, list_available_protocols

__all__ = [
    'AIInterface',
    'AIOperation',
    'MCPInterface',
    'AIGeneration',
    'PropertyPrediction',
    'get_ai_interface',
    'list_available_protocols',
]
```

## Implementation Phases

### Phase 1: Core Infrastructure (COMPLETE ✅)
- ✅ Base classes
- ✅ MCP interface implementation
- ✅ Basic generation operation
- ✅ Module structure

### Phase 2: Enhanced Operations (COMPLETE ✅)
- ✅ Property prediction
- ✅ Structure analysis
- ✅ Optimization workflows
- ✅ Prompt templates
- ✅ Formatting utilities
- ✅ Response caching

### Phase 3: Additional Protocols
- OpenAI integration
- Local model support
- Custom protocol support

### Phase 4: Advanced Features
- Caching layer
- Batch processing
- Async support
- Streaming responses

## Benefits

1. **Extensible**: Easy to add new protocols and operations
2. **Consistent**: Follows existing MatSimPy patterns
3. **Flexible**: Supports multiple AI backends
4. **Maintainable**: Clear separation of concerns
5. **Future-proof**: Designed for growth

## Dependencies

```python
# Minimal dependencies for MCP
# mcp-client-python (or similar MCP client library)

# Optional dependencies for future protocols
# openai  # For OpenAI API
# anthropic  # For Anthropic API
# transformers  # For local models
```

## Testing Strategy

```python
# tests/test_ai/
├── test_base.py           # Base class tests
├── test_mcp_interface.py  # MCP interface tests
├── test_generation.py     # Generation operation tests
└── test_integration.py    # Integration tests
```

## Migration Path

If you have existing AI code:
1. Create MCP wrapper for existing code
2. Implement base interface
3. Gradually migrate operations
4. Add new protocols as needed

