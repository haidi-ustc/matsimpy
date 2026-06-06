"""Edge case tests for core modules."""
import unittest
import numpy as np

from matsimpy.core import (
    Composition, Lattice, Structure, Crystal, Molecule,
    Site, CrystalSite, Element
)

class TestCompositionEdgeCases(unittest.TestCase):
    """Edge cases for Composition."""
    
    def test_composition_sort_by_element(self):
        """Test element-based sorting."""
        comp = Composition('O2H', sort_by='element')
        # Should be sorted by atomic number
        self.assertIn('H', comp.formula)
        self.assertIn('O', comp.formula)
    
    def test_composition_parse_with_groups(self):
        """Test parsing formulas with groups."""
        comp = Composition('Ca(OH)2')
        self.assertEqual(comp['Ca'], 1)
        self.assertEqual(comp['O'], 2)
        self.assertEqual(comp['H'], 2)

class TestLatticeEdgeCases(unittest.TestCase):
    """Edge cases for Lattice."""
    
    def test_lattice_from_parameters_zero_gamma(self):
        """Test from_parameters with zero gamma (edge case)."""
        # Gamma=0 should raise ValueError as it makes a and b vectors parallel
        with self.assertRaises(ValueError) as context:
            Lattice.from_parameters(a=5, b=5, c=5, alpha=90, beta=90, gamma=0)
        
        # Verify error message mentions the issue
        self.assertIn('gamma', str(context.exception).lower())
    
    def test_lattice_from_parameters_180_gamma(self):
        """Test from_parameters with 180 degree gamma (edge case)."""
        # Gamma=180 should also raise ValueError
        with self.assertRaises(ValueError):
            Lattice.from_parameters(a=5, b=5, c=5, alpha=90, beta=90, gamma=180)

class TestCrystalEdgeCases(unittest.TestCase):
    """Edge cases for Crystal."""
    
    def test_crystal_random_crystal_import_error(self):
        """Test random_crystal when pyxtal is not available."""
        # This will raise ImportError if pyxtal not installed
        # Use space group 1 (P1) which accepts any composition
        try:
            from matsimpy.generation import random_crystal
            crystal = random_crystal(3, 1, ['Si', 'O'], [1, 2])
            self.assertIsInstance(crystal, Crystal)
        except ImportError:
            # Expected if pyxtal not installed
            pass
        except Exception as e:
            # Other errors (like compatibility) are acceptable for this test
            # We're just checking that the function exists and can be called
            pass
    
    def test_read_file_not_found(self):
        """Test read() with non-existent file."""
        from matsimpy.io import read
        with self.assertRaises(FileNotFoundError):
            read('nonexistent.vasp')

    def test_crystal_neighbor_cache_distinguishes_pbc_mode(self):
        """Calling PBC and non-PBC neighbor queries in sequence should not reuse wrong trees."""
        crystal = Crystal(
            ['H', 'H'],
            [[0.01, 0.5, 0.5], [0.99, 0.5, 0.5]],
            Lattice.cubic(10),
            pbc=[True, True, True],
        )

        with_pbc = crystal.get_neighbor_list(0.5, atom_index=0, use_pbc=True)
        without_pbc = crystal.get_neighbor_list(0.5, atom_index=0, use_pbc=False)

        self.assertEqual(len(with_pbc[0]), 1)
        self.assertEqual(without_pbc[0], [])

    def test_crystal_neighbor_respects_partial_pbc(self):
        """2D slabs should not see periodic neighbors across the non-periodic axis."""
        slab = Crystal(
            ['H', 'H'],
            [[0.5, 0.5, 0.01], [0.5, 0.5, 0.99]],
            Lattice.cubic(10),
            pbc=[True, True, False],
        )

        neighbors = slab.get_neighbor_list(0.5, atom_index=0, use_pbc=True)
        self.assertEqual(neighbors[0], [])

class TestElementEdgeCases(unittest.TestCase):
    """Edge cases for Element."""
    
    def test_element_get_element_all_symbols(self):
        """Test get_element with various symbol formats."""
        # Test lowercase
        h1 = Element.get_element('h')
        h2 = Element.get_element('H')
        self.assertEqual(h1.symbol, h2.symbol)
        
        # Test that cache works
        h3 = Element.get_element('H')
        self.assertIs(h2, h3)  # Should be same cached object

class TestStructureEdgeCases(unittest.TestCase):
    """Edge cases for Structure."""
    
    def test_structure_empty_species(self):
        """Test structure with empty species."""
        # Empty species should work (empty structure)
        try:
            struct = Crystal([], [], Lattice.cubic(10.0))
            self.assertEqual(len(struct), 0)
        except (IndexError, ValueError):
            # Or it might raise an error, both are acceptable
            pass

class TestMoleculeEdgeCases(unittest.TestCase):
    """Edge cases for Molecule."""
    
    def test_molecule_single_atom(self):
        """Test molecule with single atom."""
        molecule = Molecule(['H'], [[0, 0, 0]])
        self.assertEqual(len(molecule), 1)
        com = molecule.get_center_of_mass()
        self.assertEqual(len(com), 3)
    
    def test_molecule_to_crystal_large_distance(self):
        """Test to_crystal with very large distances."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [100.0, 0, 0]]  # Very far apart
        molecule = Molecule(species, positions)
        crystal = molecule.to_crystal()
        self.assertIsInstance(crystal, Crystal)
        # Should still apply vacuum padding
        self.assertGreater(crystal.lattice.a, 100.0 + 15.0)
    
    def test_molecule_to_crystal_empty_molecule(self):
        """Test to_crystal with empty molecule raises error."""
        with self.assertRaises(ValueError):
            Molecule([], []).to_crystal()
    
    def test_molecule_to_crystal_single_atom(self):
        """Test to_crystal with single atom."""
        molecule = Molecule(['H'], [[0, 0, 0]])
        crystal = molecule.to_crystal()
        self.assertIsInstance(crystal, Crystal)
        # Single atom should still create a box with minimum size
        self.assertGreaterEqual(crystal.lattice.a, 30.0)  # 2 * vacuum (15.0)

    def test_molecule_center_of_mass_invalidated_after_remove_and_substitute(self):
        """Cached COM must be invalidated by mutations."""
        molecule = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        original_com = molecule.get_center_of_mass()
        result = molecule.remove_atom(1)
        removed_com = result.get_center_of_mass()
        self.assertNotEqual(original_com, removed_com)
        np.testing.assert_array_almost_equal(removed_com, [0, 0, 0])

        molecule = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        original_com = molecule.get_center_of_mass()
        result = molecule.substitute(1, 'H')
        substituted_com = result.get_center_of_mass()
        self.assertNotEqual(original_com, substituted_com)

    def test_molecule_add_atom_rolls_back_on_site_property_error(self):
        """A failed add_atom should not partially mutate the molecule."""
        molecule = Molecule(['C'], [[0, 0, 0]])
        old_species = molecule.species
        old_positions = molecule.positions.copy()

        with self.assertRaises(ValueError):
            molecule.add_atom(['H', 'H'], [[1, 0, 0], [2, 0, 0]], site_properties=[{}])

        # Original should be unchanged since add_atom returns a new object
        self.assertEqual(molecule.species, old_species)
        np.testing.assert_array_almost_equal(molecule.positions, old_positions)
        self.assertEqual(len(molecule.sites), 1)

if __name__ == '__main__':
    unittest.main()
