"""
Tests for MatSimPy UI CLI interfaces.

This module tests the CLI interface functions to ensure they work correctly
with matsimpy's native API.
"""
import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.ui.cli.interfaces.structure_editor.basic_operations import (
    _validate_element,
    _parse_element_list,
    _parse_coordinates_list,
    _validate_coordinates_list,
    _validate_element_list,
    _calculate_min_distance,
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
    _expand_wildcard_path,
    _generate_output_path,
)
from matsimpy.ui.cli.parameter_manager import CLIParameterManager, ParameterDefinition


class TestBasicOperationsHelpers(unittest.TestCase):
    """Test helper functions in basic_operations."""
    
    def test_validate_element(self):
        """Test element validation."""
        self.assertTrue(_validate_element("H"))
        self.assertTrue(_validate_element("Fe"))
        self.assertTrue(_validate_element("Si"))
        self.assertFalse(_validate_element("XX"))
        self.assertFalse(_validate_element(""))
    
    def test_parse_element_list(self):
        """Test element list parsing."""
        elements = _parse_element_list("['H', 'O', 'C']")
        self.assertEqual(elements, ['H', 'O', 'C'])
        
        elements = _parse_element_list('["Fe", "O"]')
        self.assertEqual(elements, ['Fe', 'O'])
    
    def test_validate_element_list(self):
        """Test element list validation."""
        self.assertTrue(_validate_element_list("['H', 'O']"))
        self.assertTrue(_validate_element_list('["Fe", "O"]'))
        self.assertFalse(_validate_element_list("['XX', 'O']"))
        self.assertFalse(_validate_element_list("invalid"))
    
    def test_parse_coordinates_list(self):
        """Test coordinates list parsing."""
        # Test with proper format that the function expects
        coords = _parse_coordinates_list("[[0,0,0],[1,1,1]]")
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], [0.0, 0.0, 0.0])
        self.assertEqual(coords[1], [1.0, 1.0, 1.0])
    
    def test_validate_coordinates_list(self):
        """Test coordinates list validation."""
        self.assertTrue(_validate_coordinates_list("[[0,0,0],[1,1,1]]"))
        self.assertFalse(_validate_coordinates_list("invalid"))
        self.assertFalse(_validate_coordinates_list("[[0,0]]"))  # Not 3D
    
    def test_calculate_min_distance(self):
        """Test minimum distance calculation."""
        # Create a simple crystal
        lattice = Lattice.cubic(5.0)
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)
        
        min_dist = _calculate_min_distance(crystal)
        self.assertIsInstance(min_dist, float)
        self.assertGreater(min_dist, 0)
        
        # Test with molecule
        molecule = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        min_dist = _calculate_min_distance(molecule)
        self.assertAlmostEqual(min_dist, 1.0, places=1)
        
        # Test with single atom
        single = Molecule(['H'], [[0, 0, 0]])
        min_dist = _calculate_min_distance(single)
        self.assertEqual(min_dist, float('inf'))


class TestRandomGeneration(unittest.TestCase):
    """Test random structure generation interfaces."""
    
    @patch('matsimpy.ui.cli.interfaces.structure_generator.random_generation.CLIParameterManager')
    def test_crystal_structure_interface(self, mock_param_manager):
        """Test crystal structure generation interface."""
        # Mock parameter manager
        mock_manager = MagicMock()
        mock_param_manager.return_value = mock_manager
        
        # Mock parameters
        mock_params = {
            "formula": "SiO2",
            "min_distance": 1.0,
            "max_attempts": 100
        }
        mock_manager.get_parameters.return_value = mock_params
        
        # Mock structure creation
        with patch('matsimpy.ui.cli.interfaces.structure_generator.random_generation.random_crystal') as mock_random:
            from matsimpy.core import Crystal, Lattice
            test_crystal = Crystal(['Si', 'O', 'O'], [[0,0,0], [0.5,0.5,0.5], [0.25,0.25,0.25]], Lattice.cubic(5))
            mock_random.return_value = test_crystal
            
            with patch('matsimpy.io.write') as mock_write:
                result = crystal_structure()
                
                # Check that parameters were requested
                mock_manager.get_parameters.assert_called_once()
                # Check that structure was created
                mock_random.assert_called()
                # Check that structure was saved
                mock_write.assert_called_once()
    
    @patch('matsimpy.ui.cli.interfaces.structure_generator.random_generation.CLIParameterManager')
    def test_molecular_structure_interface(self, mock_param_manager):
        """Test molecular structure generation interface."""
        # Mock parameter manager
        mock_manager = MagicMock()
        mock_param_manager.return_value = mock_manager
        
        # Mock parameters
        mock_params = {
            "formula": "H2O",
            "min_distance": 1.0,
            "max_attempts": 1000,
            "vacuum_size": 10.0
        }
        mock_manager.get_parameters.return_value = mock_params
        
        with patch('matsimpy.io.write') as mock_write:
            result = molecular_structure()
            
            # Check that parameters were requested
            mock_manager.get_parameters.assert_called_once()
            # Check that structure was saved
            mock_write.assert_called_once()
            # Check result status
            self.assertIn("status", result)


class TestSupercellBuilder(unittest.TestCase):
    """Test supercell builder interface."""
    
    def setUp(self):
        """Set up test structures."""
        self.lattice = Lattice.cubic(5.0)
        self.crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.5, 0.5, 0.5]], self.lattice)
    
    @patch('matsimpy.ui.cli.interfaces.structure_builder.supercell_builder.CLIParameterManager')
    @patch('matsimpy.ui.cli.interfaces.structure_builder.supercell_builder.write')
    def test_simple_supercell(self, mock_write, mock_param_manager):
        """Test simple supercell creation."""
        # Mock parameter manager
        mock_manager = MagicMock()
        mock_param_manager.return_value = mock_manager
        
        # Mock parameters
        mock_params = {
            "structure_file": "test.cif",
            "size": "2"
        }
        mock_manager.get_parameters.return_value = mock_params
        mock_manager.get_structure_from_params.return_value = self.crystal
        
        # Run interface
        simple_supercell()
        
        # Check that structure was loaded
        mock_manager.get_structure_from_params.assert_called_once()
        # Check that supercell was saved
        mock_write.assert_called_once()
        
        # Verify the saved structure is a supercell
        call_args = mock_write.call_args
        saved_structure = call_args[0][0]
        self.assertIsInstance(saved_structure, Crystal)
        self.assertEqual(len(saved_structure), 16)  # 2x2x2 = 8x original 2 atoms


class TestFileFormatConverter(unittest.TestCase):
    """Test file format converter interface."""
    
    def test_expand_wildcard_path(self):
        """Test wildcard path expansion."""
        # Create temporary test files
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = [
                Path(tmpdir) / "test1.cif",
                Path(tmpdir) / "test2.cif",
                Path(tmpdir) / "test3.xyz",
            ]
            
            for f in test_files:
                f.touch()
            
            # Test wildcard expansion
            pattern = str(Path(tmpdir) / "*.cif")
            expanded = _expand_wildcard_path(pattern)
            
            self.assertEqual(len(expanded), 2)
            self.assertTrue(all(f.suffix == '.cif' for f in expanded))
    
    def test_generate_output_path(self):
        """Test output path generation."""
        input_path = Path("test.cif")
        
        # Test with wildcard
        output = _generate_output_path(input_path, "output_*.xyz")
        self.assertEqual(output.name, "output_test.xyz")
        
        # Test with directory
        output = _generate_output_path(input_path, "output_dir/")
        self.assertEqual(output.parent.name, "output_dir")
        self.assertEqual(output.name, "test.cif")


class TestParameterManager(unittest.TestCase):
    """Test parameter manager functionality."""
    
    def setUp(self):
        """Set up test parameter manager."""
        from prompt_toolkit.styles import Style
        self.style = Style.from_dict({})
        self.param_manager = CLIParameterManager(style=self.style)
    
    def test_define_parameter(self):
        """Test parameter definition."""
        self.param_manager.define_parameter(
            name="test_param",
            description="Test parameter",
            param_type=str,
            required=False,
            default="default_value"
        )
        
        self.assertEqual(len(self.param_manager.parameter_definitions), 1)
        param = self.param_manager.parameter_definitions[0]
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.type, str)
        self.assertEqual(param.default, "default_value")
    
    def test_define_structure_parameter(self):
        """Test structure parameter definition."""
        self.param_manager.define_structure_parameter(
            name="structure_file",
            description="Input structure file",
            required=True
        )
        
        self.assertEqual(len(self.param_manager.parameter_definitions), 1)
        param = self.param_manager.parameter_definitions[0]
        self.assertEqual(param.name, "structure_file")
        self.assertEqual(param.type, str)
        self.assertTrue(param.required)
    
    @patch('matsimpy.ui.cli.parameter_manager.read')
    def test_load_structure(self, mock_read):
        """Test structure loading."""
        from matsimpy.core import Crystal, Lattice
        
        test_crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.0))
        mock_read.return_value = test_crystal
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cif', delete=False) as f:
            f.write("# Test CIF file\n")
            temp_path = f.name
        
        try:
            structure = self.param_manager.structure_manager.load_structure(temp_path)
            self.assertIsInstance(structure, Crystal)
            mock_read.assert_called_once_with(temp_path)
        finally:
            os.unlink(temp_path)


class TestInterfaceIntegration(unittest.TestCase):
    """Integration tests for UI interfaces."""
    
    def setUp(self):
        """Set up test structures."""
        self.lattice = Lattice.cubic(5.0)
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], self.lattice)
        self.molecule = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
    
    @patch('matsimpy.ui.cli.interfaces.structure_editor.basic_operations.CLIParameterManager')
    @patch('matsimpy.ui.cli.interfaces.structure_editor.basic_operations.read')
    @patch('matsimpy.ui.cli.interfaces.structure_editor.basic_operations.write')
    @patch('matsimpy.ui.cli.interfaces.structure_editor.basic_operations.os.path.exists')
    def test_add_atoms_interface_structure(self, mock_exists, mock_write, mock_read, mock_param_manager):
        """Test add_atoms interface with mocked dependencies."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_param_manager.return_value = mock_manager
        
        mock_read.return_value = self.crystal
        mock_exists.return_value = True  # File exists
        
        mock_params = {
            "structure_file": "test.cif",
            "elements": "['Fe']",
            "position_type": "coordinates",
            "coordinates": "[[1,1,1]]"
        }
        mock_manager.get_parameters.return_value = mock_params
        
        # Run interface
        from matsimpy.ui.cli.interfaces.structure_editor.basic_operations import add_atoms
        add_atoms()
        
        # Verify structure was loaded
        mock_read.assert_called_once()
        # Verify structure was saved
        mock_write.assert_called_once()
        
        # Verify saved structure has more atoms
        saved_structure = mock_write.call_args[0][0]
        self.assertIsInstance(saved_structure, Crystal)
        self.assertGreater(len(saved_structure), len(self.crystal))


if __name__ == '__main__':
    unittest.main()

