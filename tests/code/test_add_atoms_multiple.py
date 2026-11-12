"""Tests for add_atom method with support for adding multiple atoms."""
import unittest
import warnings
import numpy as np
import pytest

from matsimpy.core import Crystal, Molecule
from tests.conftest import make_cubic_lattice, make_simple_molecule


@pytest.mark.parametrize(
    ("species", "positions", "message"),
    [
        (['H', 'N'], [[2.0, 0, 0]], "must match"),
        (['H', 'N', 'O'], [[2.0, 0, 0], [3.0, 0, 0]], "must match"),
        ('H', [0, 0], "3D coordinate"),
        (['H', 'O'], [[0, 0, 0], [1, 2]], "3D coordinate"),
    ],
)
def test_add_atom_rejects_invalid_batch_inputs(species, positions, message):
    molecule = make_simple_molecule()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with pytest.raises(ValueError, match=message):
            molecule.add_atom(species, positions)


class TestCrystalAddAtomsWithSiteProperties(unittest.TestCase):
    """Test adding atoms with site properties."""

    def setUp(self):
        """Set up test crystal."""
        self.lattice = make_cubic_lattice(10.0)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)

    def test_add_multiple_with_single_site_property_dict(self):
        """Test adding multiple atoms with single dict (applied to all)."""
        result = self.crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]], {'type': 'hydrogen'})

        self.assertEqual(len(result.site_properties), 3)
        self.assertEqual(result.site_properties[-2], {'type': 'hydrogen'})
        self.assertEqual(result.site_properties[-1], {'type': 'hydrogen'})

    def test_maintains_existing_site_properties(self):
        """Test that existing site_properties are maintained."""
        # Create crystal with site properties
        crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0, 0]], self.lattice,
                         site_properties=[{'oxidation': 4}, {'oxidation': -2}])

        # Add atoms with properties
        result = crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]], [{'charge': 1}, {'charge': 1}])

        # Check all properties maintained
        self.assertEqual(len(result.site_properties), 4)
        self.assertEqual(result.site_properties[0], {'oxidation': 4})
        self.assertEqual(result.site_properties[1], {'oxidation': -2})
        self.assertEqual(result.site_properties[2], {'charge': 1})
        self.assertEqual(result.site_properties[3], {'charge': 1})


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test structures."""
        self.molecule = Molecule(['C'], [[0, 0, 0]])
        self.lattice = make_cubic_lattice(10.0)
        self.crystal = Crystal(['O'], [[0.5, 0.5, 0.5]], self.lattice)

    def test_large_batch_add(self):
        """Test adding many atoms at once."""
        n = 100
        species = ['H'] * n
        positions = [[1.0 + i * 0.6, 0, 0] for i in range(n)]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = self.molecule.add_atom(species, positions)

        self.assertEqual(len(result), n + 1)

    def test_numpy_array_positions(self):
        """Test that numpy array positions work."""
        positions = np.array([[1, 0, 0], [2, 0, 0]])
        result = self.molecule.add_atom(['H', 'O'], positions)

        self.assertEqual(len(result), 3)

    def test_duplicate_position_raises_error_molecule(self):
        """Test that adding atom at duplicate position raises error."""
        with self.assertRaises(ValueError) as context:
            self.molecule.add_atom('O', [0, 0, 0])

        self.assertIn("already exists", str(context.exception).lower())

    def test_very_close_atoms_raise_error(self):
        """Test that atoms too close (< 0.5 A) raise error."""
        with self.assertRaises(ValueError) as context:
            self.molecule.add_atom('O', [0.05, 0, 0])

        self.assertIn("too close", str(context.exception).lower())
        self.assertIn("0.5", str(context.exception))

    def test_duplicate_within_new_atoms_raises_error(self):
        """Test that duplicate positions within new atoms raise error."""
        with self.assertRaises(ValueError) as context:
            self.molecule.add_atom(['H', 'H'], [[1, 0, 0], [1, 0, 0]])

        self.assertIn("duplicate", str(context.exception).lower())

class TestIntegrationWithOtherMethods(unittest.TestCase):
    """Test that add_atom works well with other methods."""

    def test_add_then_copy(self):
        """Test that copy works after adding atoms."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol = mol.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])

        mol_copy = mol.copy()

        self.assertEqual(mol.species, mol_copy.species)
        self.assertTrue(np.allclose(mol.positions, mol_copy.positions))


if __name__ == '__main__':
    unittest.main()
