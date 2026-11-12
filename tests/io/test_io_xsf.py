"""Tests for XSF IO module."""
import unittest
import tempfile
import numpy as np
from pathlib import Path


from matsimpy.core import Crystal
from matsimpy.builders.bulk import from_prototype
from matsimpy.io import read_XSF, write_XSF

class TestXSFIo(unittest.TestCase):
    """Tests for XSF format IO."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    
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


if __name__ == '__main__':
    unittest.main()

