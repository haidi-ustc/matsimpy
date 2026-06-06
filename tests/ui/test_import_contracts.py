"""Import-surface contract tests for UI modules.

Verifies that all public UI interfaces can be imported and have correct callable signatures.
"""
import unittest
import inspect


class TestUIImportContracts(unittest.TestCase):
    """Test that all UI interfaces can be imported correctly."""

    def test_basic_operations_imports(self):
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
        sig = inspect.signature(add_atoms)
        self.assertIn('style', sig.parameters)

    def test_random_generation_imports(self):
        from matsimpy.ui.cli.interfaces.structure_generator.random_generation import (
            crystal_structure,
            molecular_structure,
        )
        self.assertTrue(callable(crystal_structure))
        self.assertTrue(callable(molecular_structure))
        sig = inspect.signature(crystal_structure)
        self.assertIn('style', sig.parameters)

    def test_supercell_builder_imports(self):
        from matsimpy.ui.cli.interfaces.structure_builder.supercell_builder import (
            simple_supercell,
            INTERFACE_CODE,
        )
        self.assertTrue(callable(simple_supercell))
        self.assertEqual(INTERFACE_CODE, "[b161]")

    def test_file_format_converter_imports(self):
        from matsimpy.ui.cli.interfaces.utilities_converters.file_format_converter import (
            any_to_any,
            _expand_wildcard_path,
            _generate_output_path,
        )
        self.assertTrue(callable(any_to_any))
        self.assertTrue(callable(_expand_wildcard_path))
        self.assertTrue(callable(_generate_output_path))

    def test_parameter_manager_imports(self):
        from matsimpy.ui.cli.parameter_manager import (
            CLIParameterManager,
            ParameterDefinition,
            StructureManager,
        )
        self.assertTrue(callable(CLIParameterManager))
        self.assertTrue(callable(ParameterDefinition))
        self.assertTrue(callable(StructureManager))

    def test_interface_registry(self):
        from matsimpy.ui.cli.interfaces import discover_interfaces, get_interface
        registry = discover_interfaces()
        self.assertIsInstance(registry, dict)
        try:
            interface = get_interface("[e111]")
            self.assertTrue(callable(interface))
        except (KeyError, ValueError):
            pass

    def test_interface_imports(self):
        from matsimpy.ui.cli.interfaces.structure_editor.basic_operations import (
            add_atoms,
            move_atoms_interface,
            delete_atoms,
        )
        from matsimpy.ui.cli.interfaces.structure_generator.random_generation import (
            crystal_structure,
            molecular_structure,
        )
        from matsimpy.ui.cli.interfaces.structure_builder.supercell_builder import (
            simple_supercell,
        )
        from matsimpy.ui.cli.interfaces.utilities_converters.file_format_converter import (
            any_to_any,
        )
        self.assertTrue(callable(add_atoms))
        self.assertTrue(callable(move_atoms_interface))
        self.assertTrue(callable(delete_atoms))
        self.assertTrue(callable(crystal_structure))
        self.assertTrue(callable(molecular_structure))
        self.assertTrue(callable(simple_supercell))
        self.assertTrue(callable(any_to_any))


if __name__ == '__main__':
    unittest.main()
