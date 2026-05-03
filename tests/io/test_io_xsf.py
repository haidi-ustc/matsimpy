"""Tests for XSF IO module."""
import unittest
import tempfile
import numpy as np
from pathlib import Path


from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.io import read_XSF, write_XSF

class TestXSFIo(unittest.TestCase):
    """Tests for XSF format IO."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    def test_write_XSF(self):
        """Test writing XSF file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            temp_file = f.name
        
        try:
            # Write
            write_XSF(self.crystal, temp_file, title="Test Structure")
            
            # Verify file exists
            self.assertTrue(Path(temp_file).exists())
            
            # Verify file content
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn('CRYSTAL', content)
                self.assertIn('PRIMVEC', content)
                self.assertIn('PRIMCOORD', content)
        finally:
            Path(temp_file).unlink()
    
    def test_read_XSF_file_not_found(self):
        """Test reading non-existent XSF file."""
        with self.assertRaises(FileNotFoundError):
            read_XSF('nonexistent.xsf')
    
    def test_read_XSF_invalid_format(self):
        """Test reading invalid XSF format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            f.write("Invalid\n")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                read_XSF(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_XSF_invalid_input(self):
        """Test writing invalid input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                write_XSF("not a crystal", temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_XSF_default_title(self):
        """Test writing XSF with default title."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            temp_file = f.name
        
        try:
            write_XSF(self.crystal, temp_file)
            
            # Read back and check
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn('CRYSTAL', content)
        finally:
            Path(temp_file).unlink()
    
    def test_read_XSF_sample(self):
        """Test reading a sample XSF file with correct Cartesian PRIMCOORD."""
        # PRIMCOORD holds Cartesian Angstrom coordinates (XSF standard).
        # Lattice vectors are read from the PRIMVEC block.
        xsf_content = (
            "CRYSTAL\n"
            "PRIMVEC\n"
            "  5.43  0.00  0.00\n"
            "  0.00  5.43  0.00\n"
            "  0.00  0.00  5.43\n"
            "PRIMCOORD\n"
            "2 1\n"
            "Si   0.000000   0.000000   0.000000\n"
            "Si   1.357500   1.357500   1.357500\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            f.write(xsf_content)
            temp_file = f.name

        try:
            crystal = read_XSF(temp_file)
            self.assertIsInstance(crystal, Crystal)
            self.assertEqual(len(crystal), 2)
            self.assertEqual(crystal.species[0], 'Si')
        finally:
            Path(temp_file).unlink()
    
    def test_XSF_roundtrip(self):
        """Test complete write→read roundtrip asserting Cartesian positions match."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            temp_file = f.name

        try:
            write_XSF(self.crystal, temp_file)
            crystal2 = read_XSF(temp_file)

            self.assertIsInstance(crystal2, Crystal)
            self.assertEqual(len(crystal2), len(self.crystal))
            self.assertEqual(crystal2.species, self.crystal.species)
            np.testing.assert_array_almost_equal(
                crystal2.cart_positions,
                self.crystal.cart_positions,
                decimal=6,
            )
        finally:
            Path(temp_file).unlink()

    def test_read_XSF_uses_PRIMVEC(self):
        """PRIMVEC block (not the line after CRYSTAL) must supply lattice vectors."""
        xsf_content = (
            "# comment\n"
            "CRYSTAL\n"
            "PRIMVEC\n"
            "  5.43  0.00  0.00\n"
            "  0.00  5.43  0.00\n"
            "  0.00  0.00  5.43\n"
            "PRIMCOORD\n"
            "2 1\n"
            "Si   0.000000   0.000000   0.000000\n"
            "Si   1.357500   1.357500   1.357500\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            f.write(xsf_content)
            temp_file = f.name

        try:
            crystal = read_XSF(temp_file)
            self.assertIsInstance(crystal, Crystal)
            self.assertAlmostEqual(crystal.lattice.a, 5.43, places=4)
        finally:
            Path(temp_file).unlink()

    def test_read_XSF_cartesian_coordinates(self):
        """Coordinates in PRIMCOORD are Cartesian — positions must survive roundtrip."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xsf') as f:
            temp_file = f.name

        try:
            write_XSF(self.crystal, temp_file)
            crystal2 = read_XSF(temp_file)

            # Verify lattice vectors survived
            np.testing.assert_array_almost_equal(
                crystal2.lattice.matrix,
                self.crystal.lattice.matrix,
                decimal=6,
            )
            # Verify fractional positions derived from Cartesian match original
            np.testing.assert_array_almost_equal(
                crystal2.frac_positions,
                self.crystal.frac_positions,
                decimal=6,
            )
        finally:
            Path(temp_file).unlink()

if __name__ == '__main__':
    unittest.main()

