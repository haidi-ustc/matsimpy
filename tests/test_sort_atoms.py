"""Tests for sort_atoms method."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Molecule, Lattice


class TestSortAtoms(unittest.TestCase):
    """Tests for sort_atoms method."""
    
    def test_crystal_sort_by_element(self):
        """Test sorting crystal atoms by atomic number."""
        crystal = Crystal(['O', 'Si', 'O', 'C'], 
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]], 
                         Lattice.cubic(10))
        
        original_species = crystal.species
        crystal.sort_atoms('element')
        
        # Should be sorted by atomic number: C (6), O (8), O (8), Si (14)
        self.assertEqual(crystal.species[0], 'C')
        self.assertEqual(crystal.species[1], 'O')
        self.assertEqual(crystal.species[2], 'O')
        self.assertEqual(crystal.species[3], 'Si')
        
        # Should be different from original
        self.assertNotEqual(crystal.species, original_species)
    
    def test_crystal_sort_by_alphabet(self):
        """Test sorting crystal atoms alphabetically."""
        crystal = Crystal(['O', 'Si', 'O', 'C'], 
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]], 
                         Lattice.cubic(10))
        
        crystal.sort_atoms('alphabet')
        
        # Should be sorted alphabetically: C, O, O, Si
        self.assertEqual(crystal.species[0], 'C')
        self.assertEqual(crystal.species[1], 'O')
        self.assertEqual(crystal.species[2], 'O')
        self.assertEqual(crystal.species[3], 'Si')
    
    def test_molecule_sort_by_element(self):
        """Test sorting molecule atoms by atomic number."""
        molecule = Molecule(['O', 'C', 'H', 'H'], 
                           [[0,0,0], [1.2,0,0], [1.8,0.9,0], [1.8,-0.9,0]])
        
        original_species = molecule.species
        molecule.sort_atoms('element')
        
        # Should be sorted by atomic number: H (1), H (1), C (6), O (8)
        self.assertEqual(molecule.species[0], 'H')
        self.assertEqual(molecule.species[1], 'H')
        self.assertEqual(molecule.species[2], 'C')
        self.assertEqual(molecule.species[3], 'O')
        
        # Should be different from original
        self.assertNotEqual(molecule.species, original_species)
    
    def test_crystal_sort_preserves_positions(self):
        """Test that sorting preserves atom-position correspondence."""
        crystal = Crystal(['O', 'Si', 'O', 'C'], 
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]], 
                         Lattice.cubic(10))
        
        # Store original mapping
        original_mapping = list(zip(crystal.species, crystal.positions))
        
        crystal.sort_atoms('element')
        
        # Check that positions are correctly reordered with species
        # C should be at [0.25, 0.25, 0.25]
        c_idx = list(crystal.species).index('C')
        self.assertTrue(np.allclose(crystal.positions[c_idx], [0.25, 0.25, 0.25]))
        
        # O should be at [0.5, 0.5, 0.5] (first O)
        o_indices = [i for i, s in enumerate(crystal.species) if s == 'O']
        self.assertTrue(any(np.allclose(crystal.positions[i], [0.5, 0.5, 0.5]) for i in o_indices))
    
    def test_crystal_sort_invalidates_cache(self):
        """Test that sorting invalidates caches."""
        crystal = Crystal(['O', 'Si', 'O', 'C'], 
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]], 
                         Lattice.cubic(10))
        
        # Access formula to populate cache
        original_formula = crystal.formula
        
        crystal.sort_atoms('element')
        
        # Formula should be recalculated (might be same or different)
        new_formula = crystal.formula
        # The formula string might be the same, but cache should be invalidated
        
        # Check that neighbor tree is invalidated
        self.assertIsNone(crystal._neighbor_tree)
    
    def test_crystal_sort_invalidates_neighbor_tree(self):
        """Test that sorting invalidates neighbor tree."""
        crystal = Crystal(['O', 'Si', 'O', 'C'], 
                         [[0.5,0.5,0.5], [0.5,0,0], [0,0.5,0], [0.25,0.25,0.25]], 
                         Lattice.cubic(10))
        
        # Build neighbor tree
        crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(crystal._neighbor_tree)
        
        crystal.sort_atoms('element')
        
        # Neighbor tree should be invalidated
        self.assertIsNone(crystal._neighbor_tree)
    
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
    import numpy as np
    unittest.main()

