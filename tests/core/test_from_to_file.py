"""Tests for from_file and to_file methods."""
import unittest
import tempfile
import numpy as np
from pathlib import Path

from matsimpy.core import Crystal, Molecule, Lattice

class TestFromToFile(unittest.TestCase):
    """Tests for from_file and to_file methods."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal_species = ['Si', 'O', 'O']
        self.crystal_positions = [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.crystal_species, self.crystal_positions, self.lattice)
        
        self.molecule_species = ['C', 'O', 'O']
        self.molecule_positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.molecule_species, self.molecule_positions)
    
    def test_crystal_from_file_vasp(self):
        """Test Crystal.from_file with VASP format."""
        poscar_file = Path(__file__).resolve().parents[1] / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = Crystal.from_file(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)
    
    def test_crystal_from_file_with_format(self):
        """Test Crystal.from_file with explicit format."""
        poscar_file = Path(__file__).resolve().parents[1] / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = Crystal.from_file(str(poscar_file), format='vasp')
            self.assertIsInstance(crystal, Crystal)
    
    def test_crystal_to_file_vasp(self):
        """Test Crystal.to_file with VASP format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            self.crystal.to_file(temp_file)
            self.assertTrue(Path(temp_file).exists())
            
            # Read back
            crystal2 = Crystal.from_file(temp_file)
            self.assertEqual(len(crystal2), len(self.crystal))
        finally:
            Path(temp_file).unlink()
    
    def test_crystal_to_file_with_format(self):
        """Test Crystal.to_file with explicit format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as f:
            temp_file = f.name
        
        try:
            self.crystal.to_file(temp_file, format='vasp')
            self.assertTrue(Path(temp_file).exists())
        finally:
            Path(temp_file).unlink()
    
    def test_crystal_to_file_cif(self):
        """Test Crystal.to_file with CIF format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name
        
        try:
            self.crystal.to_file(temp_file)
            self.assertTrue(Path(temp_file).exists())
            
            # Read back
            crystal2 = Crystal.from_file(temp_file)
            self.assertEqual(len(crystal2), len(self.crystal))
        finally:
            Path(temp_file).unlink()
    
    def test_crystal_from_file_invalid_format(self):
        """Test Crystal.from_file with invalid format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.unknown') as f:
            f.write("test")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                Crystal.from_file(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_from_file_xyz(self):
        """Test Molecule.from_file with XYZ format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            f.write("3\nCO2\nC 0.0 0.0 0.0\nO 1.2 0.0 0.0\nO -1.2 0.0 0.0\n")
            temp_file = f.name
        
        try:
            molecule = Molecule.from_file(temp_file)
            self.assertIsInstance(molecule, Molecule)
            self.assertEqual(len(molecule), 3)
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_to_file_xyz(self):
        """Test Molecule.to_file with XYZ format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name
        
        try:
            self.molecule.to_file(temp_file)
            self.assertTrue(Path(temp_file).exists())
            
            # Read back
            molecule2 = Molecule.from_file(temp_file)
            self.assertEqual(len(molecule2), len(self.molecule))
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_to_file_mol(self):
        """Test Molecule.to_file with MOL format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mol') as f:
            temp_file = f.name
        
        try:
            self.molecule.to_file(temp_file)
            self.assertTrue(Path(temp_file).exists())
            
            # Read back
            molecule2 = Molecule.from_file(temp_file)
            self.assertEqual(len(molecule2), len(self.molecule))
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_from_file_invalid_format(self):
        """Test Molecule.from_file with invalid format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.unknown') as f:
            f.write("test")
            temp_file = f.name
        
        try:
            with self.assertRaises(ValueError):
                Molecule.from_file(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_crystal_roundtrip(self):
        """Test complete roundtrip for Crystal."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            # Write
            self.crystal.to_file(temp_file)
            
            # Read
            crystal2 = Crystal.from_file(temp_file)
            
            # Verify
            self.assertEqual(crystal2.species, self.crystal.species)
            np.testing.assert_array_almost_equal(
                crystal2.frac_positions,
                self.crystal.frac_positions,
                decimal=6
            )
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_roundtrip(self):
        """Test complete roundtrip for Molecule."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name
        
        try:
            # Write
            self.molecule.to_file(temp_file)
            
            # Read
            molecule2 = Molecule.from_file(temp_file)
            
            # Verify
            self.assertEqual(molecule2.species, self.molecule.species)
            np.testing.assert_array_almost_equal(
                molecule2.positions,
                self.molecule.positions,
                decimal=6
            )
        finally:
            Path(temp_file).unlink()

if __name__ == '__main__':
    unittest.main()

