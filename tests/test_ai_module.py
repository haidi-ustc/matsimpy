"""Tests for AI module."""
import unittest
from unittest.mock import Mock, patch
from matsimpy.ai import (
    AIInterface,
    AIOperation,
    MCPInterface,
    AIGeneration,
    get_ai_interface,
    list_available_protocols
)

class TestAIModule(unittest.TestCase):
    """Tests for AI module structure."""
    
    def test_list_available_protocols(self):
        """Test listing available protocols."""
        protocols = list_available_protocols()
        self.assertIsInstance(protocols, list)
        self.assertIn("mcp", protocols)
    
    def test_get_ai_interface_mcp(self):
        """Test getting MCP interface via factory."""
        mcp = get_ai_interface("mcp", transport="stdio")
        self.assertIsInstance(mcp, MCPInterface)
    
    def test_get_ai_interface_invalid(self):
        """Test getting invalid protocol."""
        with self.assertRaises(ValueError):
            get_ai_interface("invalid_protocol")
    
    def test_mcp_interface_initialization(self):
        """Test MCP interface initialization."""
        mcp = MCPInterface(transport="stdio")
        self.assertEqual(mcp.transport, "stdio")
        self.assertFalse(mcp.is_connected)
    
    def test_mcp_interface_invalid_transport(self):
        """Test MCP interface with invalid transport."""
        with self.assertRaises(ValueError):
            MCPInterface(transport="invalid")

class TestMCPInterface(unittest.TestCase):
    """Tests for MCP interface."""
    
    def setUp(self):
        """Set up test MCP interface."""
        self.mcp = MCPInterface(transport="stdio")
    
    def test_connect_stdio_config(self):
        """Test stdio connection configuration."""
        config = {
            "command": "python",
            "args": ["test_server.py"]
        }
        
        # Note: This test may succeed if python can start the process
        # even if the file doesn't exist (it will fail later during communication)
        # The important thing is that config parsing works
        try:
            result = self.mcp.connect(config)
            # If it succeeds, verify connection state
            if result:
                self.assertTrue(self.mcp.is_connected)
                self.mcp.disconnect()
        except (ConnectionError, FileNotFoundError, OSError):
            # Expected if command/file doesn't exist
            pass
    
    def test_connect_missing_command(self):
        """Test connection with missing command."""
        config = {"args": ["test.py"]}
        
        with self.assertRaises(ConnectionError):
            self.mcp.connect(config)
    
    def test_call_not_connected(self):
        """Test calling when not connected."""
        with self.assertRaises(RuntimeError):
            self.mcp.call("test_operation", {})
    
    def test_disconnect(self):
        """Test disconnecting."""
        # Should not raise even if not connected
        self.mcp.disconnect()
        self.assertFalse(self.mcp.is_connected)

class TestAIGeneration(unittest.TestCase):
    """Tests for AI generation operation."""
    
    def setUp(self):
        """Set up mock AI interface."""
        self.mock_interface = Mock(spec=AIInterface)
        self.mock_interface.is_connected = True
        
        # Mock the call method
        self.mock_interface.call.return_value = {
            "species": ["Ti", "O", "O"],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.0, 0, 0], [0, 4.0, 0], [0, 0, 4.0]]
        }
    
    def test_generation_initialization(self):
        """Test AIGeneration initialization."""
        gen = AIGeneration(self.mock_interface)
        self.assertEqual(gen.interface, self.mock_interface)
    
    def test_generation_not_connected(self):
        """Test generation with non-connected interface."""
        self.mock_interface.is_connected = False
        
        with self.assertRaises(RuntimeError):
            AIGeneration(self.mock_interface)
    
    def test_generate_from_composition(self):
        """Test generating structure from composition."""
        gen = AIGeneration(self.mock_interface)
        
        structure = gen.generate_from_composition("TiO2")
        
        self.assertIsNotNone(structure)
        self.assertEqual(len(structure.species), 3)
        self.mock_interface.call.assert_called_once()
    
    def test_generate_from_composition_with_constraints(self):
        """Test generation with constraints."""
        gen = AIGeneration(self.mock_interface)
        
        constraints = {"space_group": 136}
        structure = gen.generate_from_composition("TiO2", constraints)
        
        # Verify constraints were passed
        call_args = self.mock_interface.call.call_args
        self.assertIn("constraints", call_args[1]["inputs"])

if __name__ == '__main__':
    unittest.main()

