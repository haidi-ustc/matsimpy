"""
Model Context Protocol (MCP) interface.

MCP is a protocol for interacting with AI models through standardized
tools and resources. This interface provides MCP client functionality
for MatSimPy.
"""

from typing import Dict, Any, Optional, Union
import json
import subprocess
import sys
from ..base import AIInterface


class MCPInterface(AIInterface):
    """
    Model Context Protocol (MCP) interface.
    
    Supports multiple transport methods:
    - stdio: Standard input/output communication
    - http: HTTP-based communication
    - websocket: WebSocket-based communication
    
    Examples:
        >>> mcp = MCPInterface(transport="stdio")
        >>> config = {
        ...     "command": "python",
        ...     "args": ["path/to/mcp_server.py"]
        ... }
        >>> mcp.connect(config)
        >>> result = mcp.call("generate_structure", {"composition": "TiO2"})
        >>> mcp.disconnect()
    """
    
    def __init__(self, 
                 server_url: Optional[str] = None,
                 transport: str = "stdio"):
        """
        Initialize MCP interface.
        
        Args:
            server_url: MCP server URL (for HTTP/WebSocket transport)
            transport: Transport type ('stdio', 'http', 'websocket')
        
        Raises:
            ValueError: If transport type is invalid
        """
        if transport not in ["stdio", "http", "websocket"]:
            raise ValueError(
                f"Unsupported transport: {transport}. "
                f"Must be one of: stdio, http, websocket"
            )
        
        self.server_url = server_url
        self.transport = transport
        self._connected = False
        self._client = None
        self._process = None
        self._config = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Connect to MCP server.
        
        Args:
            config: Configuration dictionary. For stdio transport:
                   - command: Command to run (e.g., "python")
                   - args: List of arguments (e.g., ["server.py"])
                   For HTTP/WebSocket:
                   - url: Server URL
        
        Returns:
            True if connection successful
        
        Raises:
            ConnectionError: If connection fails
        """
        self._config = config
        
        try:
            if self.transport == "stdio":
                self._connect_stdio(config)
            elif self.transport == "http":
                self._connect_http(config)
            elif self.transport == "websocket":
                self._connect_websocket(config)
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")
            
            self._connected = True
            return True
        
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to MCP server: {e}")
    
    def _connect_stdio(self, config: Dict[str, Any]) -> None:
        """Connect via stdio transport."""
        command = config.get("command")
        args = config.get("args", [])
        
        if not command:
            raise ValueError("stdio transport requires 'command' in config")
        
        # Start subprocess
        cmd = [command] + (args if isinstance(args, list) else [args])
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # For now, store process reference
        # Full MCP implementation would use proper MCP client library
        self._client = self._process
    
    def _connect_http(self, config: Dict[str, Any]) -> None:
        """Connect via HTTP transport."""
        url = config.get("url") or self.server_url
        
        if not url:
            raise ValueError("HTTP transport requires 'url' in config or server_url")
        
        # Placeholder for HTTP client
        # Would use requests or httpx library
        try:
            import requests
            # Test connection
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                self._client = {"url": url, "session": requests.Session()}
            else:
                raise ConnectionError(f"Server returned {response.status_code}")
        except ImportError:
            raise ImportError(
                "HTTP transport requires 'requests' library. "
                "Install with: pip install requests"
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect via HTTP: {e}")
    
    def _connect_websocket(self, config: Dict[str, Any]) -> None:
        """Connect via WebSocket transport."""
        url = config.get("url") or self.server_url
        
        if not url:
            raise ValueError("WebSocket transport requires 'url' in config or server_url")
        
        # Placeholder for WebSocket client
        # Would use websockets library
        try:
            import websockets
            # Store URL for later connection
            self._client = {"url": url, "websockets": websockets}
        except ImportError:
            raise ImportError(
                "WebSocket transport requires 'websockets' library. "
                "Install with: pip install websockets"
            )
    
    def call(self, 
             operation: str,
             inputs: Dict[str, Any],
             **kwargs) -> Dict[str, Any]:
        """
        Call MCP tool/function.
        
        Args:
            operation: Tool name or function identifier
            inputs: Input parameters for the tool
            **kwargs: Additional parameters (request_id, etc.)
        
        Returns:
            Tool execution result
        
        Raises:
            RuntimeError: If not connected or operation fails
        """
        if not self._connected:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        # Format request according to MCP JSON-RPC 2.0 spec
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": operation,
                "arguments": inputs
            },
            "id": kwargs.get("request_id", 1)
        }
        
        try:
            if self.transport == "stdio":
                return self._call_stdio(request)
            elif self.transport == "http":
                return self._call_http(request)
            elif self.transport == "websocket":
                return self._call_websocket(request)
        except Exception as e:
            raise RuntimeError(f"MCP operation '{operation}' failed: {e}")
    
    def _call_stdio(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call via stdio transport."""
        if not self._process:
            raise RuntimeError("No stdio process available")
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self._process.stdin.write(request_json)
        self._process.stdin.flush()
        
        # Read response
        response_line = self._process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
        
        response = json.loads(response_line.strip())
        
        # Check for errors
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        
        return response.get("result", {})
    
    def _call_http(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call via HTTP transport."""
        if not self._client:
            raise RuntimeError("No HTTP client available")
        
        import requests
        url = self._client["url"]
        session = self._client.get("session")
        
        if session:
            response = session.post(
                f"{url}/jsonrpc",
                json=request,
                timeout=30
            )
        else:
            response = requests.post(
                f"{url}/jsonrpc",
                json=request,
                timeout=30
            )
        
        response.raise_for_status()
        
        result = response.json()
        
        if "error" in result:
            raise RuntimeError(f"MCP error: {result['error']}")
        
        return result.get("result", {})
    
    def _call_websocket(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call via WebSocket transport."""
        # Placeholder - would use async websocket connection
        raise NotImplementedError("WebSocket transport not yet fully implemented")
    
    def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.transport == "stdio" and self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
        
        self._connected = False
        self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._connected and self._client is not None


__all__ = ['MCPInterface']

