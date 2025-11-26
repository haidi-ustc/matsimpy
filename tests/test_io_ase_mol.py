"""Tests for ASE and MOL IO modules."""
import unittest
import tempfile
import numpy as np
from pathlib import Path

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io import read_ASE, write_ASE, read_MOL, write_MOL

class TestASEIo(unittest.TestCase):
    """Tests for ASE format IO."""
    
    def setUp(self):
        """Set up test structures."""
        self.species = ['Si', 'O', 'O']
        self.positions = [[0, 0, 0], [2.5, 2.5, 2.5], [5, 5, 5]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.species, self.positions, self.lattice, coords_are_cartesian=True)
    
    def test_write_read_ASE(self):
        """Test writing and reading ASE file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ase') as f:
            temp_file = f.name
        
        try:
            # Write
            write_ASE(self.crystal, temp_file, title="Test Structure")
            
            # Verify file exists
            self.assertTrue(Path(temp_file).exists())
            
            # Read
            crystal2 = read_ASE(temp_file)
            
            # Verify structure
            self.assertEqual(len(crystal2), 3)
            self.assertEqual(crystal2.species, ('Si', 'O', 'O'))
        finally:
            Path(temp_file).unlink()
    
    def test_read_ASE_file_not_found(self):
        """Test reading non-existent ASE file."""
        with self.assertRaises(FileNotFoundError):
            read_ASE('nonexistent.ase')
    
    def test_read_ASE_no_lattice(self):
        """Test reading ASE file without lattice info."""
        ase_content = """3
No lattice info
Si 0.0 0.0 0.0
O 2.5 2.5 2.5
O 5.0 5.0 5.0
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ase') as f:
            f.write(ase_content)
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                read_ASE(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_ASE_invalid_input(self):
        """Test writing invalid input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ase') as f:
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                write_ASE("not a structure", temp_file)
        finally:
            Path(temp_file).unlink()

class TestMOLIo(unittest.TestCase):
    """Tests for MOL format IO."""
    
    def setUp(self):
        """Set up test molecules."""
        self.species = ['C', 'O', 'O']
        self.positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.species, self.positions)
    
    def test_write_read_MOL(self):
        """Test writing and reading MOL file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mol') as f:
            temp_file = f.name
        
        try:
            # Write
            write_MOL(self.molecule, temp_file, title="CO2")
            
            # Verify file exists
            self.assertTrue(Path(temp_file).exists())
            
            # Read
            molecule2 = read_MOL(temp_file)
            
            # Verify structure
            self.assertEqual(len(molecule2), 3)
            self.assertEqual(molecule2.species, ('C', 'O', 'O'))
        finally:
            Path(temp_file).unlink()
    
    def test_read_MOL_file_not_found(self):
        """Test reading non-existent MOL file."""
        with self.assertRaises(FileNotFoundError):
            read_MOL('nonexistent.mol')
    
    def test_read_MOL_invalid_format(self):
        """Test reading invalid MOL format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mol') as f:
            f.write("Invalid\n")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                read_MOL(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_write_MOL_invalid_input(self):
        """Test writing invalid input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mol') as f:
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                write_MOL("not a molecule", temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_read_MOL_sample(self):
        """Test reading a sample MOL file."""
        mol_content = """Test Molecule
  MatSimPy
Generated
  3  2  0  0  0  0  0  0  0  0  1 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.2000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -1.2000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
M  END
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mol') as f:
            f.write(mol_content)
            temp_file = f.name
        
        try:
            molecule = read_MOL(temp_file)
            self.assertEqual(len(molecule), 3)
            self.assertIn('C', molecule.species)
        finally:
            Path(temp_file).unlink()

if __name__ == '__main__':
    unittest.main()

