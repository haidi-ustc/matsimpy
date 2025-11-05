"""Tests for VASP IO module."""
import os
import sys
import unittest
import tempfile
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Lattice
from matsimpy.io import read_POSCAR, write_POSCAR, read_CONTCAR, write_CONTCAR


class TestVASPIo(unittest.TestCase):
    """Tests for VASP POSCAR/CONTCAR IO."""
    
    def setUp(self):
        """Set up test structures."""
        self.species = ['Si', 'O', 'O']
        self.positions = [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.species, self.positions, self.lattice)
    
    def test_write_read_POSCAR(self):
        """Test writing and reading POSCAR file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            # Write
            write_POSCAR(self.crystal, temp_file, title="Test Structure")
            
            # Verify file exists
            self.assertTrue(Path(temp_file).exists())
            
            # Read
            crystal2 = read_POSCAR(temp_file)
            
            # Verify structure
            self.assertEqual(len(crystal2), 3)
            self.assertEqual(crystal2.species, ('Si', 'O', 'O'))
            np.testing.assert_array_almost_equal(
                crystal2.frac_positions, 
                self.crystal.frac_positions,
                decimal=6
            )
        finally:
            Path(temp_file).unlink()
    
    def test_read_POSCAR_file_not_found(self):
        """Test reading non-existent POSCAR file."""
        with self.assertRaises(FileNotFoundError):
            read_POSCAR('nonexistent.vasp')
    
    def test_read_POSCAR_invalid_format(self):
        """Test reading invalid POSCAR format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            f.write("Invalid\n")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                read_POSCAR(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_POSCAR_invalid_input(self):
        """Test writing invalid input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                write_POSCAR("not a crystal", temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_read_POSCAR_cartesian(self):
        """Test reading POSCAR with cartesian coordinates."""
        poscar_content = """Test Structure
1.0
10.0 0.0 0.0
0.0 10.0 0.0
0.0 0.0 10.0
Si O
1 2
Cartesian
0.0 0.0 0.0
5.0 5.0 5.0
2.5 2.5 2.5
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            f.write(poscar_content)
            temp_file = f.name
        
        try:
            crystal = read_POSCAR(temp_file)
            self.assertEqual(len(crystal), 3)
            # Verify cartesian positions are correct
            self.assertAlmostEqual(crystal.cart_positions[0][0], 0.0, places=5)
        finally:
            Path(temp_file).unlink()
    
    def test_write_POSCAR_default_title(self):
        """Test writing POSCAR with default title."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            write_POSCAR(self.crystal, temp_file)
            
            # Read back and check
            with open(temp_file, 'r') as f:
                first_line = f.readline().strip()
                self.assertIn('Crystal', first_line)
        finally:
            Path(temp_file).unlink()
    
    def test_read_CONTCAR(self):
        """Test reading CONTCAR (alias for POSCAR)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            write_POSCAR(self.crystal, temp_file)
            crystal2 = read_CONTCAR(temp_file)
            self.assertEqual(len(crystal2), 3)
        finally:
            Path(temp_file).unlink()
    
    def test_write_CONTCAR(self):
        """Test writing CONTCAR."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            write_CONTCAR(self.crystal, temp_file)
            self.assertTrue(Path(temp_file).exists())
        finally:
            Path(temp_file).unlink()
    
    def test_read_existing_POSCAR(self):
        """Test reading existing POSCAR file from tests."""
        poscar_file = Path(__file__).parent / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = read_POSCAR(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)


if __name__ == '__main__':
    unittest.main()

