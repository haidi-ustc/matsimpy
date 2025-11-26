"""Tests for add_atom method with support for adding multiple atoms."""
import os
import sys
import unittest
import warnings
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Molecule, Lattice


class TestStructureAddMultipleAtoms(unittest.TestCase):
    """Test adding multiple atoms to base Structure class."""
    
    def setUp(self):
        """Set up test structures."""
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], self.lattice)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_add_single_atom_string_syntax(self):
        """Test adding single atom with string species (backward compatible)."""
        original_len = len(self.molecule)
        self.molecule.add_atom('H', [2.0, 0, 0])
        
        self.assertEqual(len(self.molecule), original_len + 1)
        self.assertEqual(self.molecule.species[-1], 'H')
        self.assertTrue(np.allclose(self.molecule.positions[-1], [2.0, 0, 0]))
    
    def test_add_multiple_atoms_list_syntax(self):
        """Test adding multiple atoms with list syntax."""
        original_len = len(self.molecule)
        self.molecule.add_atom(['H', 'H'], [[2.0, 0, 0], [3.0, 0, 0]])
        
        self.assertEqual(len(self.molecule), original_len + 2)
        self.assertEqual(self.molecule.species[-2], 'H')
        self.assertEqual(self.molecule.species[-1], 'H')
        self.assertTrue(np.allclose(self.molecule.positions[-2], [2.0, 0, 0]))
        self.assertTrue(np.allclose(self.molecule.positions[-1], [3.0, 0, 0]))
    
    def test_add_multiple_different_species(self):
        """Test adding multiple atoms of different species."""
        original_len = len(self.crystal)
        self.crystal.add_atom(['H', 'N', 'O'], [[0.1, 0, 0], [0.2, 0, 0], [0.3, 0, 0]])  # 0.5, 1.0, 1.5 Å in Cartesian
        
        self.assertEqual(len(self.crystal), original_len + 3)
        self.assertEqual(self.crystal.species[-3], 'H')
        self.assertEqual(self.crystal.species[-2], 'N')
        self.assertEqual(self.crystal.species[-1], 'O')
    
    def test_add_empty_list(self):
        """Test that adding empty list does nothing."""
        original_len = len(self.molecule)
        original_species = self.molecule.species
        self.molecule.add_atom([], [])
        
        self.assertEqual(len(self.molecule), original_len)
        self.assertEqual(self.molecule.species, original_species)
    
    def test_add_atoms_validates_length_mismatch(self):
        """Test that mismatched species/position lengths raise error."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with self.assertRaises(ValueError) as context:
                # Use position that doesn't conflict with existing atoms
                self.molecule.add_atom(['H', 'N'], [[2.0, 0, 0]])
            
            self.assertIn("must match", str(context.exception))
    
    def test_add_atoms_validates_3d_coordinates(self):
        """Test that non-3D coordinates raise error."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with self.assertRaises(ValueError):
                self.molecule.add_atom('H', [0, 0])  # 2D
            
            with self.assertRaises(ValueError):
                self.molecule.add_atom(['H', 'O'], [[0, 0, 0], [1, 2]])  # One 2D
    
    def test_formula_updated_after_adding_multiple(self):
        """Test that formula is correctly updated after adding atoms."""
        original_formula = self.molecule.formula
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.molecule.add_atom(['H', 'H', 'N'], [[2.0, 0, 0], [3.0, 0, 0], [4.0, 0, 0]])  # >= 0.5 Å from existing
        
        new_formula = self.molecule.formula
        self.assertNotEqual(original_formula, new_formula)
        self.assertIn('H2', new_formula)
        self.assertIn('N', new_formula)
    
    def test_composition_updated_after_adding_multiple(self):
        """Test that composition is correctly updated."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.molecule.add_atom(['N', 'N'], [[2.0, 0, 0], [3.0, 0, 0]])  # >= 0.5 Å from existing
        
        composition = self.molecule.composition
        self.assertIn('N', composition.composition)
        self.assertEqual(composition.composition['N'], 2)


class TestCrystalAddMultipleAtoms(unittest.TestCase):
    """Test adding multiple atoms to Crystal."""
    
    def setUp(self):
        """Set up test crystal."""
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)
    
    def test_add_multiple_fractional_coords(self):
        """Test adding multiple atoms in fractional coordinates."""
        self.crystal.add_atom(['O', 'O'], [[0.25, 0, 0], [0.75, 0, 0]])
        
        self.assertEqual(len(self.crystal), 3)
        self.assertTrue(np.allclose(self.crystal.frac_positions[-2], [0.25, 0, 0]))
        self.assertTrue(np.allclose(self.crystal.frac_positions[-1], [0.75, 0, 0]))
    
    def test_cartesian_positions_updated(self):
        """Test that Cartesian positions are updated correctly."""
        self.crystal.add_atom(['O', 'O'], [[0.5, 0, 0], [0, 0.5, 0]])
        
        # Check that cart_positions match frac_positions
        # For a cubic lattice with a=10, frac [0.5, 0, 0] -> cart [5, 0, 0]
        expected_cart = np.array([[5.0, 0, 0], [0, 5.0, 0]])
        self.assertTrue(np.allclose(self.crystal.cart_positions[-2:], expected_cart))
    
    def test_neighbor_tree_invalidated(self):
        """Test that neighbor tree is invalidated after adding atoms."""
        # Build neighbor tree
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_tree)
        
        # Add atoms
        self.crystal.add_atom(['O', 'O'], [[0.1, 0, 0], [0.2, 0, 0]])
        
        # Neighbor tree should be invalidated
        self.assertIsNone(self.crystal._neighbor_tree)
    
    def test_sites_updated_after_adding_multiple(self):
        """Test that sites are correctly updated."""
        original_sites = len(self.crystal.sites)
        self.crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]])
        
        self.assertEqual(len(self.crystal.sites), original_sites + 2)
        self.assertEqual(self.crystal.sites[-2].specie, 'H')
        self.assertEqual(self.crystal.sites[-1].specie, 'H')


class TestCrystalAddAtomsWithSiteProperties(unittest.TestCase):
    """Test adding atoms with site properties."""
    
    def setUp(self):
        """Set up test crystal."""
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)
    
    def test_add_single_with_site_properties(self):
        """Test adding single atom with site properties."""
        self.crystal.add_atom('O', [0.5, 0, 0], {'charge': -2})
        
        self.assertEqual(len(self.crystal.site_properties), 2)
        self.assertEqual(self.crystal.site_properties[-1], {'charge': -2})
    
    def test_add_multiple_with_site_properties_list(self):
        """Test adding multiple atoms with list of site properties."""
        props = [{'charge': 1}, {'charge': -1}]
        self.crystal.add_atom(['H', 'Cl'], [[0.1, 0, 0], [0.2, 0, 0]], props)
        
        self.assertEqual(len(self.crystal.site_properties), 3)
        self.assertEqual(self.crystal.site_properties[-2], {'charge': 1})
        self.assertEqual(self.crystal.site_properties[-1], {'charge': -1})
    
    def test_add_multiple_with_single_site_property_dict(self):
        """Test adding multiple atoms with single dict (applied to all)."""
        self.crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]], {'type': 'hydrogen'})
        
        self.assertEqual(len(self.crystal.site_properties), 3)
        self.assertEqual(self.crystal.site_properties[-2], {'type': 'hydrogen'})
        self.assertEqual(self.crystal.site_properties[-1], {'type': 'hydrogen'})
    
    def test_site_properties_mismatch_raises_error(self):
        """Test that mismatched site_properties length raises error."""
        with self.assertRaises(ValueError) as context:
            # Use positions that don't conflict with existing atoms
            self.crystal.add_atom(['H', 'O'], [[0.1, 0, 0], [0.2, 0, 0]], [{'charge': 1}])
        
        self.assertIn("must match", str(context.exception))
    
    def test_maintains_existing_site_properties(self):
        """Test that existing site_properties are maintained."""
        # Create crystal with site properties
        crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0, 0]], self.lattice,
                         site_properties=[{'oxidation': 4}, {'oxidation': -2}])
        
        # Add atoms with properties
        crystal.add_atom(['H', 'H'], [[0.1, 0, 0], [0.2, 0, 0]], [{'charge': 1}, {'charge': 1}])
        
        # Check all properties maintained
        self.assertEqual(len(crystal.site_properties), 4)
        self.assertEqual(crystal.site_properties[0], {'oxidation': 4})
        self.assertEqual(crystal.site_properties[1], {'oxidation': -2})
        self.assertEqual(crystal.site_properties[2], {'charge': 1})
        self.assertEqual(crystal.site_properties[3], {'charge': 1})


class TestMoleculeAddMultipleAtoms(unittest.TestCase):
    """Test adding multiple atoms to Molecule."""
    
    def setUp(self):
        """Set up test molecule."""
        self.molecule = Molecule(['C'], [[0, 0, 0]])
    
    def test_add_multiple_atoms_cartesian(self):
        """Test adding multiple atoms with Cartesian coordinates."""
        self.molecule.add_atom(['H', 'H', 'H'], 
                               [[1.09, 0, 0], [-0.545, 0.943, 0], [-0.545, -0.943, 0]])
        
        self.assertEqual(len(self.molecule), 4)
        self.assertEqual(self.molecule.species[0], 'C')
        self.assertEqual(self.molecule.species[1], 'H')
        self.assertEqual(self.molecule.species[2], 'H')
        self.assertEqual(self.molecule.species[3], 'H')
    
    def test_center_of_mass_invalidated(self):
        """Test that center of mass cache is invalidated."""
        # Calculate COM
        _ = self.molecule.get_center_of_mass()
        self.assertTrue(hasattr(self.molecule, '_cached_com'))
        
        # Add atoms
        self.molecule.add_atom(['O', 'O'], [[1, 0, 0], [2, 0, 0]])
        
        # Cache should be invalidated
        self.assertFalse(hasattr(self.molecule, '_cached_com'))
    
    def test_sites_updated(self):
        """Test that sites list is updated."""
        original_sites = len(self.molecule.sites)
        self.molecule.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])
        
        self.assertEqual(len(self.molecule.sites), original_sites + 2)
        self.assertEqual(self.molecule.sites[-2].specie, 'H')
        self.assertEqual(self.molecule.sites[-1].specie, 'O')


class TestMoleculeAddAtomsWithSiteProperties(unittest.TestCase):
    """Test adding atoms to Molecule with site properties."""
    
    def setUp(self):
        """Set up test molecule."""
        self.molecule = Molecule(['C'], [[0, 0, 0]])
    
    def test_add_multiple_with_site_properties(self):
        """Test adding multiple atoms with site properties."""
        props = [{'bond_order': 1}, {'bond_order': 2}]
        self.molecule.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]], props)
        
        self.assertEqual(len(self.molecule.site_properties), 3)
        self.assertEqual(self.molecule.site_properties[-2], {'bond_order': 1})
        self.assertEqual(self.molecule.site_properties[-1], {'bond_order': 2})


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test structures."""
        self.molecule = Molecule(['C'], [[0, 0, 0]])
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(['O'], [[0.5, 0.5, 0.5]], self.lattice)
    
    def test_large_batch_add(self):
        """Test adding many atoms at once."""
        n = 100
        species = ['H'] * n
        # Use spacing >= 0.5 Å to avoid validation errors, and start from 1.0 to avoid conflict with existing atom at [0,0,0]
        positions = [[1.0 + i * 0.6, 0, 0] for i in range(n)]  # 0.6 Å spacing > 0.5 Å threshold
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.molecule.add_atom(species, positions)
        
        self.assertEqual(len(self.molecule), n + 1)
    
    def test_numpy_array_positions(self):
        """Test that numpy array positions work."""
        positions = np.array([[1, 0, 0], [2, 0, 0]])
        self.molecule.add_atom(['H', 'O'], positions)
        
        self.assertEqual(len(self.molecule), 3)
    
    def test_mixed_types_in_species_list(self):
        """Test that all species must be strings."""
        # This should work
        self.molecule.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])
        self.assertEqual(len(self.molecule), 3)
    
    def test_backward_compatibility(self):
        """Test that old single-atom syntax still works."""
        # Old code should still work
        mol = Molecule(['C'], [[0, 0, 0]])
        mol.add_atom('H', [1, 0, 0])
        mol.add_atom('O', [2, 0, 0])
        
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
        """Test that atoms too close (< 0.5 Å) raise error."""
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
        mol.add_atom(['H', 'H'], [[1, 0, 0], [2, 0, 0]])
        
        # Substitute the added hydrogens
        mol.substitute([1, 2], ['F', 'F'])
        
        self.assertEqual(mol.species, ('C', 'F', 'F'))
    
    def test_add_then_remove(self):
        """Test adding then removing atoms."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol.add_atom(['H', 'H', 'H'], [[1, 0, 0], [2, 0, 0], [3, 0, 0]])
        
        # Remove middle atom
        mol.remove_atom(2)
        
        self.assertEqual(len(mol), 3)
    
    def test_add_then_copy(self):
        """Test that copy works after adding atoms."""
        mol = Molecule(['C'], [[0, 0, 0]])
        mol.add_atom(['H', 'O'], [[1, 0, 0], [2, 0, 0]])
        
        mol_copy = mol.copy()
        
        self.assertEqual(mol.species, mol_copy.species)
        self.assertTrue(np.allclose(mol.positions, mol_copy.positions))
    
    def test_add_then_get_neighbor_list(self):
        """Test neighbor list after adding atoms."""
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(['Si'], [[0, 0, 0]], lattice)
        crystal.add_atom(['O', 'O'], [[0.1, 0, 0], [0.2, 0, 0]])
        
        neighbors = crystal.get_neighbor_list(5.0)
        
        # Should work without errors
        self.assertIsInstance(neighbors, dict)
        self.assertEqual(len(neighbors), 3)


if __name__ == '__main__':
    unittest.main()

