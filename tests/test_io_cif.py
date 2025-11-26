"""Tests for CIF IO module."""
import unittest
import tempfile
import numpy as np
from pathlib import Path

from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.io import read_CIF, write_CIF

class TestCIFIo(unittest.TestCase):
    """Tests for CIF format IO."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    def test_write_read_CIF(self):
        """Test writing and reading CIF file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name
        
        try:
            # Write
            write_CIF(self.crystal, temp_file, title="Test Structure")
            
            # Verify file exists
            self.assertTrue(Path(temp_file).exists())
            
            # Read
            crystal2 = read_CIF(temp_file)
            
            # Verify structure
            self.assertIsInstance(crystal2, Crystal)
            self.assertEqual(len(crystal2), len(self.crystal))
            self.assertEqual(crystal2.species, self.crystal.species)
            
            # Verify lattice parameters are similar (may have slight differences due to rounding)
            self.assertAlmostEqual(crystal2.lattice.a, self.crystal.lattice.a, places=2)
        finally:
            Path(temp_file).unlink()
    
    def test_read_CIF_file_not_found(self):
        """Test reading non-existent CIF file."""
        with self.assertRaises(FileNotFoundError):
            read_CIF('nonexistent.cif')
    
    def test_read_CIF_invalid_format(self):
        """Test reading invalid CIF format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            f.write("Invalid\n")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                read_CIF(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_CIF_invalid_input(self):
        """Test writing invalid input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                write_CIF("not a crystal", temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_CIF_default_title(self):
        """Test writing CIF with default title."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name
        
        try:
            write_CIF(self.crystal, temp_file)
            
            # Read back and check
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn('data_', content)
        finally:
            Path(temp_file).unlink()
    
    def test_read_CIF_sample(self):
        """Test reading a sample CIF file."""
        cif_content = """data_test
_chemical_name_common 'Silicon'
_cell_length_a    5.43
_cell_length_b    5.43
_cell_length_c    5.43
_cell_angle_alpha 90.0
_cell_angle_beta  90.0
_cell_angle_gamma 90.0
_space_group_name_H-M_alt 'F d -3 m'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0.0 0.0 0.0
Si2 Si 0.25 0.25 0.25
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            f.write(cif_content)
            temp_file = f.name
        
        try:
            crystal = read_CIF(temp_file)
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)
        finally:
            Path(temp_file).unlink()
    
    def test_CIF_roundtrip(self):
        """Test complete roundtrip for CIF."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name
        
        try:
            # Write and read
            write_CIF(self.crystal, temp_file)
            crystal2 = read_CIF(temp_file)
            
            # Verify species match
            self.assertEqual(crystal2.species, self.crystal.species)
            self.assertEqual(len(crystal2), len(self.crystal))
        finally:
            Path(temp_file).unlink()

if __name__ == '__main__':
    unittest.main()

