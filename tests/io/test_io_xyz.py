"""Tests for XYZ IO module."""
import unittest
import tempfile
from pathlib import Path

from matsimpy.core import Molecule
from matsimpy.io import read_XYZ, write_XYZ, read_XYZ_multiframe

class TestXYZIo(unittest.TestCase):
    """Tests for XYZ format IO."""
    
    def setUp(self):
        """Set up test molecules."""
        self.species = ['C', 'O', 'O']
        self.positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.species, self.positions)
    
    def test_write_read_XYZ(self):
        """Test writing and reading XYZ file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name
        
        try:
            # Write
            write_XYZ(self.molecule, temp_file, title="CO2")
            
            # Verify file exists
            self.assertTrue(Path(temp_file).exists())
            
            # Read
            molecule2 = read_XYZ(temp_file)
            
            # Verify structure
            self.assertEqual(len(molecule2), 3)
            self.assertEqual(molecule2.species, ('C', 'O', 'O'))
        finally:
            Path(temp_file).unlink()
    
    def test_read_XYZ_file_not_found(self):
        """Test reading non-existent XYZ file."""
        with self.assertRaises(FileNotFoundError):
            read_XYZ('nonexistent.xyz')
    
    def test_read_XYZ_invalid_format(self):
        """Test reading invalid XYZ format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            f.write("Invalid\n")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                read_XYZ(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_XYZ_invalid_input(self):
        """Test writing invalid input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                write_XYZ("not a molecule", temp_file)
        finally:
            Path(temp_file).unlink()
    
    

    def test_read_XYZ_multiframe_includes_last_frame(self):
        """read_XYZ_multiframe must return all frames, including the last one."""
        xyz_content = (
            "2\nFrame 1\nH 0.0 0.0 0.0\nH 0.74 0.0 0.0\n"
            "2\nFrame 2\nH 0.0 0.0 0.0\nH 0.75 0.0 0.0\n"
            "2\nFrame 3\nH 0.0 0.0 0.0\nH 0.76 0.0 0.0\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            f.write(xyz_content)
            temp_file = f.name

        try:
            molecules = read_XYZ_multiframe(temp_file)
            self.assertEqual(len(molecules), 3)
            # Last frame must be present
            import numpy as np
            np.testing.assert_almost_equal(
                molecules[-1].positions[1][0], 0.76, decimal=6
            )
        finally:
            Path(temp_file).unlink()

if __name__ == '__main__':
    unittest.main()

