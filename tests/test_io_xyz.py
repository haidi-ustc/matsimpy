"""Tests for XYZ IO module."""
import os
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    
    def test_read_XYZ_multiframe(self):
        """Test reading multi-frame XYZ file."""
        xyz_content = """2
Frame 1
H 0.0 0.0 0.0
H 0.74 0.0 0.0
2
Frame 2
H 0.0 0.0 0.0
H 0.75 0.0 0.0
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            f.write(xyz_content)
            temp_file = f.name
        
        try:
            molecules = read_XYZ_multiframe(temp_file)
            self.assertEqual(len(molecules), 2)
            self.assertIsInstance(molecules[0], Molecule)
            self.assertEqual(len(molecules[0]), 2)
        finally:
            Path(temp_file).unlink()
    
    def test_write_XYZ_default_title(self):
        """Test writing XYZ with default title."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name
        
        try:
            write_XYZ(self.molecule, temp_file)
            
            # Read back and check
            with open(temp_file, 'r') as f:
                lines = f.readlines()
                self.assertEqual(int(lines[0].strip()), 3)
                self.assertIn('C', lines[2])  # First atom line
        finally:
            Path(temp_file).unlink()


if __name__ == '__main__':
    unittest.main()

