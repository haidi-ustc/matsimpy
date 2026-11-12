"""Tests for atomic manipulation and organization operations."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule
from matsimpy.transformation.atomic import (
    move_atoms,
    swap_atoms,
    merge_atoms,
    sort_atoms,
    center_structure
)

class TestAtomicManipulation(unittest.TestCase):
    """Tests for atomic manipulation operations."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = make_simple_crystal()
        self.molecule = make_simple_molecule()
    
    
    def test_move_atoms_crystal_multiple(self):
        """Test moving multiple atoms in crystal."""
        moved = move_atoms(self.crystal, [0, 1], [0.1, 0.1, 0])
        
        self.assertIsNot(moved, self.crystal)
        self.assertEqual(len(moved.species), 2)
    
    
    def test_move_atoms_always_returns_new(self):
        """Test that move_atoms always returns a new object."""
        original_pos = self.crystal.positions[0].copy()
        result = move_atoms(self.crystal, 0, [0.1, 0, 0])
        
        # Should be different object
        self.assertIsNot(result, self.crystal)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.crystal.positions[0], original_pos)
        # Result should be modified
        self.assertNotEqual(result.cart_positions[0, 0], self.crystal.cart_positions[0, 0])
    
    def test_swap_atoms_crystal(self):
        """Test swapping atoms in crystal."""
        swapped = swap_atoms(self.crystal, 0, 1)
        
        # Species should be swapped
        self.assertEqual(swapped.species[0], 'O')
        self.assertEqual(swapped.species[1], 'Si')
        # Positions should be swapped
        np.testing.assert_array_almost_equal(
            swapped.positions[0], self.crystal.positions[1]
        )
    
    
    
    def test_merge_atoms_custom(self):
        """Test merging atoms with custom species and position."""
        merged = merge_atoms(self.crystal, 0, 1, species='C', position=[0.25, 0.25, 0.25])
        
        self.assertEqual(len(merged.species), 1)
        self.assertEqual(merged.species[0], 'C')
    

class TestAtomicOrganization(unittest.TestCase):
    """Tests for atomic organization operations."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['O', 'Si', 'C'], 
            [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], 
            Lattice.cubic(10)
        )
        self.molecule = Molecule(['O', 'C', 'H'], [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0]])
    
    
    def test_sort_atoms_by_z(self):
        """Test sorting by atomic number."""
        sorted_struct = sort_atoms(self.crystal, key='z')
        
        # H(1) < C(6) < O(8) < Si(14)
        self.assertEqual(sorted_struct.species[0], 'C')  # Z=6
        self.assertEqual(sorted_struct.species[1], 'O')  # Z=8
        self.assertEqual(sorted_struct.species[2], 'Si') # Z=14
    
    def test_sort_atoms_by_mass(self):
        """Test sorting by atomic mass."""
        sorted_struct = sort_atoms(self.crystal, key='mass')
        
        # Should sort by mass
        self.assertIsNotNone(sorted_struct)
    
    def test_sort_atoms_by_distance(self):
        """Test sorting by distance from origin."""
        sorted_struct = sort_atoms(self.crystal, key='distance')
        
        self.assertEqual(len(sorted_struct.species), 3)
    
    
    def test_sort_atoms_custom_function(self):
        """Test sorting with custom function."""
        def custom_key(structure, index):
            return structure.cart_positions[index][0]  # Sort by x coordinate
        
        sorted_struct = sort_atoms(self.crystal, key=custom_key)
        
        self.assertEqual(len(sorted_struct.species), 3)
    
    
    
    def test_center_structure_custom_point(self):
        """Test centering at custom point."""
        centered = center_structure(self.molecule, center=[5, 5, 5])
        
        self.assertIsNot(centered, self.molecule)
    
    
    
    


if __name__ == '__main__':
    unittest.main()
