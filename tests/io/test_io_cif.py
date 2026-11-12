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
    
    
    

    def test_read_CIF_cartesian_coords(self):
        """CIF with _atom_site_Cartn_* must be converted to fractional correctly."""
        cif_content = (
            "data_test\n"
            "_cell_length_a  5.0\n"
            "_cell_length_b  5.0\n"
            "_cell_length_c  5.0\n"
            "_cell_angle_alpha 90\n"
            "_cell_angle_beta  90\n"
            "_cell_angle_gamma 90\n"
            "loop_\n"
            "_atom_site_type_symbol\n"
            "_atom_site_Cartn_x\n"
            "_atom_site_Cartn_y\n"
            "_atom_site_Cartn_z\n"
            "Si 0.0 0.0 0.0\n"
            "O  2.5 2.5 2.5\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            f.write(cif_content)
            temp_file = f.name

        try:
            crystal = read_CIF(temp_file)
            self.assertEqual(len(crystal), 2)
            self.assertEqual(crystal.species[0], 'Si')
            # 2.5 Å in a 5 Å cubic cell → fractional 0.5
            np.testing.assert_array_almost_equal(
                crystal.frac_positions[1], [0.5, 0.5, 0.5], decimal=6
            )
        finally:
            Path(temp_file).unlink()

    def test_write_CIF_per_element_labels(self):
        """write_CIF must use per-element labels (Si1, Si2, O1) not global index."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name

        try:
            lattice = Lattice.cubic(5.0)
            crystal = Crystal(['Si', 'O', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]], lattice)
            write_CIF(crystal, temp_file)

            with open(temp_file) as fh:
                content = fh.read()

            self.assertIn('Si1', content)
            self.assertIn('Si2', content)
            self.assertIn('O1', content)
            # Global index label Si3 must NOT appear
            self.assertNotIn('Si3', content)
        finally:
            Path(temp_file).unlink()

if __name__ == '__main__':
    unittest.main()

