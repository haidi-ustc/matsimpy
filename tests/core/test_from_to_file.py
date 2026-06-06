"""Tests for IO read/write functions (replaces from_file/to_file methods)."""
import unittest
import tempfile
import numpy as np
from pathlib import Path

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io import read, write


class TestFromToFile(unittest.TestCase):
    """Tests for IO read/write functions."""

    def setUp(self):
        """Set up test structures."""
        self.crystal_species = ['Si', 'O', 'O']
        self.crystal_positions = [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.crystal_species, self.crystal_positions, self.lattice)

        self.molecule_species = ['C', 'O', 'O']
        self.molecule_positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.molecule_species, self.molecule_positions)

    def test_crystal_read_vasp(self):
        """Test read() with VASP format returns Crystal."""
        poscar_file = Path(__file__).resolve().parents[1] / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = read(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)

    def test_crystal_read_with_format(self):
        """Test read() with explicit format."""
        poscar_file = Path(__file__).resolve().parents[1] / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = read(str(poscar_file), format='vasp')
            self.assertIsInstance(crystal, Crystal)

    def test_crystal_write_vasp(self):
        """Test write() with VASP format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name

        try:
            write(self.crystal, temp_file)
            self.assertTrue(Path(temp_file).exists())

            # Read back
            crystal2 = read(temp_file)
            self.assertEqual(len(crystal2), len(self.crystal))
        finally:
            Path(temp_file).unlink()

    def test_crystal_write_with_format(self):
        """Test write() with explicit format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as f:
            temp_file = f.name

        try:
            write(self.crystal, temp_file, format='vasp')
            self.assertTrue(Path(temp_file).exists())
        finally:
            Path(temp_file).unlink()

    def test_crystal_write_read_cif(self):
        """Test write() and read() with CIF format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cif') as f:
            temp_file = f.name

        try:
            write(self.crystal, temp_file)
            self.assertTrue(Path(temp_file).exists())

            # Read back
            crystal2 = read(temp_file)
            self.assertEqual(len(crystal2), len(self.crystal))
        finally:
            Path(temp_file).unlink()

    def test_read_invalid_format(self):
        """Test read() with unknown extension raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.unknown') as f:
            f.write("test")
            temp_file = f.name

        try:
            with self.assertRaises(ValueError):
                read(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_molecule_read_xyz(self):
        """Test read() with XYZ format returns Molecule."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            f.write("3\nCO2\nC 0.0 0.0 0.0\nO 1.2 0.0 0.0\nO -1.2 0.0 0.0\n")
            temp_file = f.name

        try:
            molecule = read(temp_file)
            self.assertIsInstance(molecule, Molecule)
            self.assertEqual(len(molecule), 3)
        finally:
            Path(temp_file).unlink()

    def test_molecule_write_read_xyz(self):
        """Test write() and read() with XYZ format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name

        try:
            write(self.molecule, temp_file)
            self.assertTrue(Path(temp_file).exists())

            # Read back
            molecule2 = read(temp_file)
            self.assertEqual(len(molecule2), len(self.molecule))
        finally:
            Path(temp_file).unlink()

    def test_molecule_write_read_mol(self):
        """Test write() and read() with MOL format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mol') as f:
            temp_file = f.name

        try:
            write(self.molecule, temp_file)
            self.assertTrue(Path(temp_file).exists())

            # Read back
            molecule2 = read(temp_file)
            self.assertEqual(len(molecule2), len(self.molecule))
        finally:
            Path(temp_file).unlink()

    def test_crystal_roundtrip(self):
        """Test complete roundtrip for Crystal using read/write."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name

        try:
            # Write
            write(self.crystal, temp_file)

            # Read
            crystal2 = read(temp_file)

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
        """Test complete roundtrip for Molecule using read/write."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xyz') as f:
            temp_file = f.name

        try:
            # Write
            write(self.molecule, temp_file)

            # Read
            molecule2 = read(temp_file)

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
