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
