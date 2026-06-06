"""Tests for VASP IO module."""
import unittest
import tempfile
import numpy as np
from pathlib import Path

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
        poscar_file = Path(__file__).resolve().parents[1] / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = read_POSCAR(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)

    def test_write_read_interleaved_species(self):
        """Interleaved species (Si/O/Si) must be regrouped on write so read recovers correct chemistry."""
        lattice = Lattice.cubic(10.0)
        # Intentionally interleaved: Si, O, Si
        crystal = Crystal(['Si', 'O', 'Si'], [[0, 0, 0], [0.1, 0.1, 0.1], [0.5, 0.5, 0.5]], lattice)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name

        try:
            write_POSCAR(crystal, temp_file)
            crystal2 = read_POSCAR(temp_file)

            # Both Si atoms come first, then O in the written file;
            # after read, species order follows the header grouping.
            self.assertEqual(set(crystal2.species), {'Si', 'O'})
            self.assertEqual(crystal2.species.count('Si'), 2)
            self.assertEqual(crystal2.species.count('O'), 1)
            self.assertEqual(len(crystal2), 3)
        finally:
            Path(temp_file).unlink()

    def test_read_POSCAR_selective_dynamics(self):
        """Optional Selective dynamics line must not corrupt coordinate parsing."""
        poscar_content = (
            "Selective dynamics test\n"
            "1.0\n"
            "5.0  0.0  0.0\n"
            "0.0  5.0  0.0\n"
            "0.0  0.0  5.0\n"
            "Si\n"
            "2\n"
            "Selective dynamics\n"
            "Direct\n"
            "0.0  0.0  0.0  T T T\n"
            "0.5  0.5  0.5  F F F\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            f.write(poscar_content)
            temp_file = f.name

        try:
            crystal = read_POSCAR(temp_file)
            self.assertEqual(len(crystal), 2)
            self.assertEqual(crystal.species, ('Si', 'Si'))
            np.testing.assert_array_almost_equal(
                crystal.frac_positions[0], [0.0, 0.0, 0.0], decimal=6
            )
            np.testing.assert_array_almost_equal(
                crystal.frac_positions[1], [0.5, 0.5, 0.5], decimal=6
            )
        finally:
            Path(temp_file).unlink()

class TestSymbolSetVaspIntegration(unittest.TestCase):
    def test_symbol_set_matches_vasp_format(self):
        import tempfile
        import os

        crystal = Crystal(['Na', 'Cl', 'Na'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(5.64))

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name

        try:
            write_POSCAR(crystal, temp_file)
            with open(temp_file, 'r') as f:
                lines = f.readlines()
                vasp_species = lines[5].strip().split()
                self.assertEqual(list(crystal.symbol_set), vasp_species)
        finally:
            os.unlink(temp_file)

    def test_sort_atoms_affects_vasp_output(self):
        import tempfile
        import os

        crystal = Crystal(['Cl', 'Na', 'Cl'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(5.64))

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file1 = f.name
        write_POSCAR(crystal, temp_file1)
        with open(temp_file1, 'r') as f:
            vasp_species_before = f.readlines()[5].strip().split()
        self.assertEqual(vasp_species_before, ['Cl', 'Na'])

        sorted_crystal = crystal.sort_atoms('element')
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file2 = f.name
        write_POSCAR(sorted_crystal, temp_file2)
        with open(temp_file2, 'r') as f:
            vasp_species_after = f.readlines()[5].strip().split()
        self.assertEqual(vasp_species_after, ['Na', 'Cl'])
        self.assertEqual(list(sorted_crystal.symbol_set), vasp_species_after)

        os.unlink(temp_file1)
        os.unlink(temp_file2)


if __name__ == '__main__':
    unittest.main()

