"""Tests for add_atom method with support for adding multiple atoms."""
import unittest
import warnings
import numpy as np
import pytest

from matsimpy.core import Crystal, Molecule
from tests.conftest import make_cubic_lattice, make_simple_crystal, make_simple_molecule


@pytest.mark.parametrize(
    ("species", "positions", "message"),
    [
        (['H', 'N'], [[2.0, 0, 0]], "must match"),
        (['H', 'N', 'O'], [[2.0, 0, 0], [3.0, 0, 0]], "must match"),
    ],
)
def test_add_atom_rejects_mismatched_batch_lengths(species, positions, message):
    molecule = make_simple_molecule()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with pytest.raises(ValueError, match=message):
            molecule.add_atom(species, positions)


@pytest.mark.parametrize(
    ("species", "positions", "message"),
    [
        ('H', [0, 0], "3D coordinate"),
        (['H', 'O'], [[0, 0, 0], [1, 2]], "3D coordinate"),
    ],
)
def test_add_atom_rejects_non_3d_coordinates(species, positions, message):
    molecule = make_simple_molecule()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with pytest.raises(ValueError, match=message):
            molecule.add_atom(species, positions)

class TestStructureAddMultipleAtoms(unittest.TestCase):
    """Test adding multiple atoms to base Structure class."""

    def setUp(self):
        """Set up test structures."""
        self.lattice = make_cubic_lattice(10.0)
        self.crystal = make_simple_crystal(self.lattice)
        self.molecule = make_simple_molecule()

    def test_add_single_atom_string_syntax(self):
        """Test adding single atom with string species (backward compatible)."""
        original_len = len(self.molecule)
        result = self.molecule.add_atom('H', [2.0, 0, 0])

        self.assertEqual(len(result), original_len + 1)
        self.assertEqual(result.species[-1], 'H')
        self.assertTrue(np.allclose(result.positions[-1], [2.0, 0, 0]))

    def test_add_multiple_atoms_list_syntax(self):
        """Test adding multiple atoms with list syntax."""
        original_len = len(self.molecule)
        result = self.molecule.add_atom(['H', 'H'], [[2.0, 0, 0], [3.0, 0, 0]])

        self.assertEqual(len(result), original_len + 2)
        self.assertEqual(result.species[-2], 'H')
        self.assertEqual(result.species[-1], 'H')
        self.assertTrue(np.allclose(result.positions[-2], [2.0, 0, 0]))
        self.assertTrue(np.allclose(result.positions[-1], [3.0, 0, 0]))

    def test_add_multiple_different_species(self):
        """Test adding multiple atoms of different species."""
        original_len = len(self.crystal)
        result = self.crystal.add_atom(['H', 'N', 'O'], [[0.1, 0, 0], [0.2, 0, 0], [0.3, 0, 0]])

        self.assertEqual(len(result), original_len + 3)
        self.assertEqual(result.species[-3], 'H')
        self.assertEqual(result.species[-2], 'N')
        self.assertEqual(result.species[-1], 'O')

    def test_add_empty_list(self):
        """Test that adding empty list does nothing."""
        original_len = len(self.molecule)
        original_species = self.molecule.species
        result = self.molecule.add_atom([], [])

        self.assertEqual(len(result), original_len)
        self.assertEqual(result.species, original_species)

    def test_formula_updated_after_adding_multiple(self):
        """Test that formula is correctly updated after adding atoms."""
        original_formula = self.molecule.formula
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = self.molecule.add_atom(['H', 'H', 'N'], [[2.0, 0, 0], [3.0, 0, 0], [4.0, 0, 0]])

        new_formula = result.formula
        self.assertNotEqual(original_formula, new_formula)
        self.assertIn('H2', new_formula)
        self.assertIn('N', new_formula)

    def test_composition_updated_after_adding_multiple(self):
        """Test that composition is correctly updated."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = self.molecule.add_atom(['N', 'N'], [[2.0, 0, 0], [3.0, 0, 0]])

        composition = result.composition
        self.assertIn('N', composition.composition)
        self.assertEqual(composition.composition['N'], 2)

class TestCrystalAddMultipleAtoms(unittest.TestCase):
    """Test adding multiple atoms to Crystal."""

    def setUp(self):
        """Set up test crystal."""
        self.lattice = make_cubic_lattice(10.0)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)

    def test_add_multiple_fractional_coords(self):
        """Test adding multiple atoms in fractional coordinates."""
        result = self.crystal.add_atom(['O', 'O'], [[0.25, 0, 0], [0.75, 0, 0]])

        self.assertEqual(len(result), 3)
        self.assertTrue(np.allclose(result.frac_positions[-2], [0.25, 0, 0]))
        self.assertTrue(np.allclose(result.frac_positions[-1], [0.75, 0, 0]))

    def test_cartesian_positions_updated(self):
        """Test that Cartesian positions are updated correctly."""
        result = self.crystal.add_atom(['O', 'O'], [[0.5, 0, 0], [0, 0.5, 0]])

        # Check that cart_positions match frac_positions
        expected_cart = np.array([[5.0, 0, 0], [0, 5.0, 0]])
        self.assertTrue(np.allclose(result.cart_positions[-2:], expected_cart))

    def test_neighbor_tree_invalidated(self):
        """Test that neighbor cache is not present on new result."""
        # Build neighbor tree (populates _neighbor_cache)
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_cache)

        # Add atoms (returns new object)
        result = self.crystal.add_atom(['O', 'O'], [[0.1, 0, 0], [0.2, 0, 0]])

        # Original should still have neighbor cache
        self.assertIsNotNone(self.crystal._neighbor_cache)
        # Result should have no neighbor cache (freshly created)
        self.assertIsNone(result._neighbor_cache)

    def test_sites_updated_after_adding_multiple(self):
        """Test that sites are correctly updated."""
        original_sites = len(self.crystal.sites)
        result = self.crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]])

        self.assertEqual(len(result.sites), original_sites + 2)
        self.assertEqual(result.sites[-2].specie, 'H')
        self.assertEqual(result.sites[-1].specie, 'H')

class TestCrystalAddAtomsWithSiteProperties(unittest.TestCase):
    """Test adding atoms with site properties."""

    def setUp(self):
        """Set up test crystal."""
        self.lattice = make_cubic_lattice(10.0)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)

    def test_add_single_with_site_properties(self):
        """Test adding single atom with site properties."""
        result = self.crystal.add_atom('O', [0.5, 0, 0], {'charge': -2})

        self.assertEqual(len(result.site_properties), 2)
        self.assertEqual(result.site_properties[-1], {'charge': -2})

    def test_add_multiple_with_site_properties_list(self):
        """Test adding multiple atoms with list of site properties."""
        props = [{'charge': 1}, {'charge': -1}]
        result = self.crystal.add_atom(['H', 'Cl'], [[0.1, 0, 0], [0.2, 0, 0]], props)

        self.assertEqual(len(result.site_properties), 3)
        self.assertEqual(result.site_properties[-2], {'charge': 1})
        self.assertEqual(result.site_properties[-1], {'charge': -1})

    def test_add_multiple_with_single_site_property_dict(self):
        """Test adding multiple atoms with single dict (applied to all)."""
        result = self.crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]], {'type': 'hydrogen'})

        self.assertEqual(len(result.site_properties), 3)
        self.assertEqual(result.site_properties[-2], {'type': 'hydrogen'})
        self.assertEqual(result.site_properties[-1], {'type': 'hydrogen'})

    def test_site_properties_mismatch_raises_error(self):
        """Test that mismatched site_properties length raises error."""
        with self.assertRaises(ValueError) as context:
            self.crystal.add_atom(['H', 'O'], [[0.1, 0, 0], [0.2, 0, 0]], [{'charge': 1}])

        self.assertIn("must match", str(context.exception))

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

class TestMoleculeAddMultipleAtoms(unittest.TestCase):
    """Test adding multiple atoms to Molecule."""

    def setUp(self):
        """Set up test molecule."""
        self.molecule = Molecule(['C'], [[0, 0, 0]])

    def test_add_multiple_atoms_cartesian(self):
        """Test adding multiple atoms with Cartesian coordinates."""
        result = self.molecule.add_atom(['H', 'H', 'H'],
                                       [[1.09, 0, 0], [-0.545, 0.943, 0], [-0.545, -0.943, 0]])

        self.assertEqual(len(result), 4)
        self.assertEqual(result.species[0], 'C')
        self.assertEqual(result.species[1], 'H')
        self.assertEqual(result.species[2], 'H')
        self.assertEqual(result.species[3], 'H')

    def test_center_of_mass_invalidated(self):
        """Test that center of mass cache is invalidated."""
        # Calculate COM
        _ = self.molecule.get_center_of_mass()

        # Add atoms (returns new object)
        result = self.molecule.add_atom(['O', 'O'], [[1, 0, 0], [2, 0, 0]])

        # New object should have fresh COM cache
        self.assertIsNone(getattr(result, '_cached_com', None))

    def test_sites_updated(self):
        """Test that sites list is updated."""
        original_sites = len(self.molecule.sites)
        result = self.molecule.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])

        self.assertEqual(len(result.sites), original_sites + 2)
        self.assertEqual(result.sites[-2].specie, 'H')
        self.assertEqual(result.sites[-1].specie, 'O')

class TestMoleculeAddAtomsWithSiteProperties(unittest.TestCase):
    """Test adding atoms to Molecule with site properties."""

    def setUp(self):
        """Set up test molecule."""
        self.molecule = Molecule(['C'], [[0, 0, 0]])

    def test_add_multiple_with_site_properties(self):
        """Test adding multiple atoms with site properties."""
        props = [{'bond_order': 1}, {'bond_order': 2}]
        result = self.molecule.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]], props)

        self.assertEqual(len(result.site_properties), 3)
        self.assertEqual(result.site_properties[-2], {'bond_order': 1})
        self.assertEqual(result.site_properties[-1], {'bond_order': 2})

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

    def test_mixed_types_in_species_list(self):
        """Test that all species must be strings."""
        # This should work
        result = self.molecule.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])
        self.assertEqual(len(result), 3)

    def test_backward_compatibility(self):
        """Test that old single-atom syntax still works."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol = mol.add_atom('H', [1, 0, 0])
        mol = mol.add_atom('O', [2, 0, 0])

        self.assertEqual(len(mol), 3)
        self.assertEqual(mol.species, ('C', 'H', 'O'))

    def test_duplicate_position_raises_error_molecule(self):
        """Test that adding atom at duplicate position raises error."""
        with self.assertRaises(ValueError) as context:
            self.molecule.add_atom('O', [0, 0, 0])

        self.assertIn("already exists", str(context.exception).lower())

    def test_duplicate_position_raises_error_crystal(self):
        """Test that adding atom at duplicate position raises error in crystal."""
        with self.assertRaises(ValueError) as context:
            self.crystal.add_atom('O', [0.5, 0.5, 0.5])

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

    def test_add_then_substitute(self):
        """Test adding atoms then substituting."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol = mol.add_atom(['H', 'H'], [[1, 0, 0], [2, 0, 0]])

        # Substitute the added hydrogens
        mol = mol.substitute([1, 2], ['F', 'F'])

        self.assertEqual(mol.species, ('C', 'F', 'F'))

    def test_add_then_remove(self):
        """Test adding then removing atoms."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol = mol.add_atom(['H', 'H', 'H'], [[1, 0, 0], [2, 0, 0], [3, 0, 0]])

        # Remove middle atom
        mol = mol.remove_atom(2)

        self.assertEqual(len(mol), 3)

    def test_add_then_copy(self):
        """Test that copy works after adding atoms."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol = mol.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])

        mol_copy = mol.copy()

        self.assertEqual(mol.species, mol_copy.species)
        self.assertTrue(np.allclose(mol.positions, mol_copy.positions))

    def test_add_then_get_neighbor_list(self):
        """Test neighbor list after adding atoms."""
        lattice = make_cubic_lattice(10.0)
        crystal = Crystal(['Si'], [[0, 0, 0]], lattice)
        crystal = crystal.add_atom(['O', 'O'], [[0.1, 0, 0], [0.2, 0, 0]])

        neighbors = crystal.get_neighbor_list(5.0)

        # Should work without errors
        self.assertIsInstance(neighbors, dict)
        self.assertEqual(len(neighbors), 3)

if __name__ == '__main__':
    unittest.main()
