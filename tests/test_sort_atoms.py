"""Tests for sort_atoms method."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice

class TestSortAtoms(unittest.TestCase):
    """Tests for sort_atoms method."""
    
    def test_crystal_sort_by_element(self):
        """Test sorting crystal atoms by atomic number."""
        crystal = Crystal(['O', 'Si', 'O', 'C'],
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]],
                         Lattice.cubic(10))

        original_species = crystal.species
        result = crystal.sort_atoms('element')

        # Should be sorted by atomic number: C (6), O (8), O (8), Si (14)
        self.assertEqual(result.species[0], 'C')
        self.assertEqual(result.species[1], 'O')
        self.assertEqual(result.species[2], 'O')
        self.assertEqual(result.species[3], 'Si')

        # Result should be different from original
        self.assertNotEqual(result.species, original_species)
        # Original unchanged
        self.assertEqual(crystal.species, original_species)

    def test_crystal_sort_by_alphabet(self):
        """Test sorting crystal atoms alphabetically."""
        crystal = Crystal(['O', 'Si', 'O', 'C'],
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]],
                         Lattice.cubic(10))

        result = crystal.sort_atoms('alphabet')

        # Should be sorted alphabetically: C, O, O, Si
        self.assertEqual(result.species[0], 'C')
        self.assertEqual(result.species[1], 'O')
        self.assertEqual(result.species[2], 'O')
        self.assertEqual(result.species[3], 'Si')

    def test_molecule_sort_by_element(self):
        """Test sorting molecule atoms by atomic number."""
        molecule = Molecule(['O', 'C', 'H', 'H'],
                           [[0,0,0], [1.2,0,0], [1.8,0.9,0], [1.8,-0.9,0]])

        original_species = molecule.species
        result = molecule.sort_atoms('element')

        # Should be sorted by atomic number: H (1), H (1), C (6), O (8)
        self.assertEqual(result.species[0], 'H')
        self.assertEqual(result.species[1], 'H')
        self.assertEqual(result.species[2], 'C')
        self.assertEqual(result.species[3], 'O')

        # Result should be different from original
        self.assertNotEqual(result.species, original_species)
        # Original unchanged
        self.assertEqual(molecule.species, original_species)

    def test_crystal_sort_preserves_positions(self):
        """Test that sorting preserves atom-position correspondence."""
        crystal = Crystal(['O', 'Si', 'O', 'C'],
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]],
                         Lattice.cubic(10))

        result = crystal.sort_atoms('element')

        # Check that fractional positions are correctly reordered with species
        # C should be at fractional [0.25, 0.25, 0.25]
        c_idx = list(result.species).index('C')
        self.assertTrue(np.allclose(result.frac_positions[c_idx], [0.25, 0.25, 0.25]))

        # O should be at fractional [0.5, 0.5, 0.5] (first O)
        o_indices = [i for i, s in enumerate(result.species) if s == 'O']
        self.assertTrue(any(np.allclose(result.frac_positions[i], [0.5, 0.5, 0.5]) for i in o_indices))

    def test_crystal_sort_invalidates_cache(self):
        """Test that sorting returns a fresh object with no cached neighbor tree."""
        crystal = Crystal(['O', 'Si', 'O', 'C'],
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]],
                         Lattice.cubic(10))

        result = crystal.sort_atoms('element')

        # Check that neighbor tree is not present on new object
        self.assertIsNone(result._neighbor_cache)

    def test_crystal_sort_invalidates_neighbor_cache(self):
        """Test that sorting returns a fresh object with no neighbor tree."""
        crystal = Crystal(['O', 'Si', 'O', 'C'],
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]],
                         Lattice.cubic(10))

        # Build neighbor tree on original
        crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(crystal._neighbor_cache)

        result = crystal.sort_atoms('element')

        # Result should have no neighbor tree (fresh copy)
        self.assertIsNone(result._neighbor_cache)
        # Original should still have neighbor tree
        self.assertIsNotNone(crystal._neighbor_cache)
    
    def test_sort_atoms_invalid_sort_by(self):
        """Test that invalid sort_by raises ValueError."""
        crystal = Crystal(['O', 'Si'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(10))
        
        with self.assertRaises(ValueError):
            crystal.sort_atoms('invalid')
    
    def test_sort_atoms_idempotent(self):
        """Test that sorting twice gives same result."""
        crystal = Crystal(['O', 'Si', 'O', 'C'], 
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]], 
                         Lattice.cubic(10))
        
        crystal.sort_atoms('element')
        first_sort = crystal.species
        
        crystal.sort_atoms('element')
        second_sort = crystal.species
        
        self.assertEqual(first_sort, second_sort)

if __name__ == '__main__':
    unittest.main()

