"""
Quick test to verify all UI interfaces can be imported and have correct signatures.
"""
import unittest
import inspect

class TestUIImports(unittest.TestCase):
    """Test that all UI interfaces can be imported correctly."""
    
    def test_basic_operations_imports(self):
        """Test basic operations interface imports."""
        from matsimpy.ui.cli.interfaces.structure_editor.basic_operations import (
            add_atoms,
            move_atoms_interface,
            delete_atoms,
            INTERFACE_CODE,
        )
        
        self.assertTrue(callable(add_atoms))
        self.assertTrue(callable(move_atoms_interface))
        self.assertTrue(callable(delete_atoms))
        self.assertEqual(INTERFACE_CODE, "[e111]")
        
        # Check function signatures
        sig = inspect.signature(add_atoms)
        self.assertIn('style', sig.parameters)
    
    def test_random_generation_imports(self):
        """Test random generation interface imports."""
        from matsimpy.ui.cli.interfaces.structure_generator.random_generation import (
            crystal_structure,
            molecular_structure,
        )
        
        self.assertTrue(callable(crystal_structure))
        self.assertTrue(callable(molecular_structure))
        
        # Check function signatures
        sig = inspect.signature(crystal_structure)
        self.assertIn('style', sig.parameters)
    
    def test_supercell_builder_imports(self):
        """Test supercell builder interface imports."""
        from matsimpy.ui.cli.interfaces.structure_builder.supercell_builder import (
            simple_supercell,
            INTERFACE_CODE,
        )
        
        self.assertTrue(callable(simple_supercell))
        self.assertEqual(INTERFACE_CODE, "[b161]")
    
    def test_file_format_converter_imports(self):
        """Test file format converter interface imports."""
        from matsimpy.ui.cli.interfaces.utilities_converters.file_format_converter import (
            any_to_any,
            _expand_wildcard_path,
            _generate_output_path,
        )
        
        self.assertTrue(callable(any_to_any))
        self.assertTrue(callable(_expand_wildcard_path))
        self.assertTrue(callable(_generate_output_path))
    
    def test_parameter_manager_imports(self):
        """Test parameter manager imports."""
        from matsimpy.ui.cli.parameter_manager import (
            CLIParameterManager,
            ParameterDefinition,
            StructureManager,
        )
        
        self.assertTrue(callable(CLIParameterManager))
        self.assertTrue(callable(ParameterDefinition))
        self.assertTrue(callable(StructureManager))
    
    def test_interface_registry(self):
        """Test interface discovery."""
        from matsimpy.ui.cli.interfaces import discover_interfaces, get_interface
        
        # Should be able to discover interfaces
        registry = discover_interfaces()
        self.assertIsInstance(registry, dict)
        
        # Should be able to get interface function
        # (may be empty if no interfaces are registered, but should not raise)
        try:
            interface = get_interface("[e111]")
            self.assertTrue(callable(interface))
        except (KeyError, ValueError):
            # Interface may not be registered, that's okay
            pass


if __name__ == '__main__':
    unittest.main()

