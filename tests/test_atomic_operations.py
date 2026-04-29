"""Tests for atomic manipulation and organization operations."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule
from matsimpy.transformation.atomic import (
    move_atoms,
    swap_atoms,
    merge_atoms,
    split_atom,
    sort_atoms,
    center_structure,
    perturb_positions
)

class TestAtomicManipulation(unittest.TestCase):
    """Tests for atomic manipulation operations."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = make_simple_crystal()
        self.molecule = make_simple_molecule()
    
    def test_move_atoms_crystal_single(self):
        """Test moving single atom in crystal."""
        moved = move_atoms(self.crystal, 0, [0.1, 0, 0])
        
        # Should be new object
        self.assertIsNot(moved, self.crystal)
        # Original unchanged
        np.testing.assert_array_almost_equal(self.crystal.positions[0], [0, 0, 0])
        # New position changed
        self.assertNotEqual(moved.cart_positions[0, 0], self.crystal.cart_positions[0, 0])
    
    def test_move_atoms_crystal_multiple(self):
        """Test moving multiple atoms in crystal."""
        moved = move_atoms(self.crystal, [0, 1], [0.1, 0.1, 0])
        
        self.assertIsNot(moved, self.crystal)
        self.assertEqual(len(moved.species), 2)
    
    def test_move_atoms_molecule(self):
        """Test moving atoms in molecule."""
        moved = move_atoms(self.molecule, 0, [1, 0, 0])
        
        np.testing.assert_array_almost_equal(moved.positions[0], [1, 0, 0])
        self.assertIsNot(moved, self.molecule)
    
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
    
    def test_swap_atoms_molecule(self):
        """Test swapping atoms in molecule."""
        swapped = swap_atoms(self.molecule, 0, 1)
        
        self.assertEqual(swapped.species[0], 'O')
        self.assertEqual(swapped.species[1], 'C')
    
    def test_merge_atoms_default(self):
        """Test merging atoms at midpoint."""
        merged = merge_atoms(self.crystal, 0, 1)
        
        # Should have one less atom
        self.assertEqual(len(merged.species), 1)
    
    def test_merge_atoms_custom(self):
        """Test merging atoms with custom species and position."""
        merged = merge_atoms(self.crystal, 0, 1, species='C', position=[0.25, 0.25, 0.25])
        
        self.assertEqual(len(merged.species), 1)
        self.assertEqual(merged.species[0], 'C')
    
    def test_split_atom(self):
        """Test splitting one atom into two."""
        split = split_atom(self.crystal, 0, ['H', 'H'], [[0, 0, 0], [0.1, 0, 0]])
        
        # Should have one more atom
        self.assertEqual(len(split.species), 3)
        self.assertIn('H', split.species)

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
    
    def test_sort_atoms_by_species(self):
        """Test sorting by species (alphabetically)."""
        sorted_struct = sort_atoms(self.crystal, key='species')
        
        # C, O, Si alphabetically
        self.assertEqual(sorted_struct.species[0], 'C')
        self.assertEqual(sorted_struct.species[1], 'O')
        self.assertEqual(sorted_struct.species[2], 'Si')
    
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
    
    def test_sort_atoms_reverse(self):
        """Test reverse sorting."""
        sorted_struct = sort_atoms(self.crystal, key='species', reverse=True)
        
        # Si, O, C (reverse alphabetical)
        self.assertEqual(sorted_struct.species[0], 'Si')
    
    def test_sort_atoms_custom_function(self):
        """Test sorting with custom function."""
        def custom_key(structure, index):
            return structure.cart_positions[index][0]  # Sort by x coordinate
        
        sorted_struct = sort_atoms(self.crystal, key=custom_key)
        
        self.assertEqual(len(sorted_struct.species), 3)
    
    def test_sort_atoms_molecule(self):
        """Test sorting molecule."""
        sorted_mol = sort_atoms(self.molecule, key='species')
        
        self.assertEqual(sorted_mol.species[0], 'C')
        self.assertEqual(sorted_mol.species[1], 'H')
        self.assertEqual(sorted_mol.species[2], 'O')
    
    def test_center_structure_molecule(self):
        """Test centering molecule at origin."""
        # Move molecule away
        mol = Molecule(['C', 'O'], [[5, 5, 5], [6.2, 5, 5]])
        centered = center_structure(mol)
        
        # Check that structure is valid and is different object
        self.assertIsNot(centered, mol)
        self.assertEqual(len(centered.species), 2)
    
    def test_center_structure_custom_point(self):
        """Test centering at custom point."""
        centered = center_structure(self.molecule, center=[5, 5, 5])
        
        self.assertIsNot(centered, self.molecule)
    
    def test_perturb_positions_all(self):
        """Test perturbing all atoms."""
        perturbed = perturb_positions(self.crystal, amplitude=0.1, seed=42)
        
        # Positions should be different
        self.assertFalse(np.allclose(perturbed.positions, self.crystal.positions))
        self.assertIsNot(perturbed, self.crystal)
    
    def test_perturb_positions_specific(self):
        """Test perturbing specific atoms."""
        perturbed = perturb_positions(self.crystal, amplitude=0.1, indices=[0], seed=42)
        
        # First atom changed, second unchanged
        self.assertFalse(np.allclose(perturbed.positions[0], self.crystal.positions[0]))
        np.testing.assert_array_almost_equal(perturbed.positions[1], self.crystal.positions[1])
    
    def test_perturb_positions_molecule(self):
        """Test perturbing molecule."""
        perturbed = perturb_positions(self.molecule, amplitude=0.05, seed=42)
        
        self.assertIsNot(perturbed, self.molecule)
        self.assertEqual(len(perturbed.species), len(self.molecule.species))
    
    def test_perturb_positions_reproducible(self):
        """Test that same seed gives same result."""
        p1 = perturb_positions(self.crystal, amplitude=0.1, seed=42)
        p2 = perturb_positions(self.crystal, amplitude=0.1, seed=42)
        
        np.testing.assert_array_almost_equal(p1.positions, p2.positions)

class TestAtomicAlwaysReturnsNew(unittest.TestCase):
    """Tests that atomic transformation functions always return new objects."""
    
    def setUp(self):
        """Set up test structure."""
        self.crystal = make_simple_crystal()
    
    def test_move_atoms_always_new(self):
        """Test that move_atoms always returns a new object."""
        original_id = id(self.crystal)
        original_pos = self.crystal.positions[0].copy()
        result = move_atoms(self.crystal, 0, [0.1, 0, 0])
        
        # Should be different object
        self.assertNotEqual(id(result), original_id)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.crystal.positions[0], original_pos)
    
    def test_swap_atoms_always_new(self):
        """Test that swap_atoms always returns a new object."""
        original_species = list(self.crystal.species)
        result = swap_atoms(self.crystal, 0, 1)
        
        # Should be different object
        self.assertIsNot(result, self.crystal)
        # Original should be unchanged
        self.assertEqual(list(self.crystal.species), original_species)
        # Result should be swapped
        self.assertNotEqual(list(result.species), original_species)
    
    def test_sort_atoms_always_new(self):
        """Test that sort_atoms always returns a new object."""
        crystal = Crystal(['O', 'Si'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
        original_species = list(crystal.species)
        result = sort_atoms(crystal, key='species')
        
        # Should be different object
        self.assertIsNot(result, crystal)
        # Original should be unchanged
        self.assertEqual(list(crystal.species), original_species)
        # Result should be sorted
        self.assertEqual(result.species[0], 'O')
    
    def test_center_structure_always_new(self):
        """Test that center_structure always returns a new object."""
        mol = Molecule(['C', 'O'], [[5, 5, 5], [6.2, 5, 5]])
        original_pos = mol.positions[0].copy()
        result = center_structure(mol)
        
        # Should be different object
        self.assertIsNot(result, mol)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(mol.positions[0], original_pos)
    
    def test_perturb_positions_always_new(self):
        """Test that perturb_positions always returns a new object."""
        original_pos = self.crystal.positions.copy()
        result = perturb_positions(self.crystal, amplitude=0.1, seed=42)
        
        # Should be different object
        self.assertIsNot(result, self.crystal)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.crystal.positions, original_pos)
        # Result should be perturbed
        self.assertFalse(np.allclose(result.positions, original_pos))

if __name__ == '__main__':
    unittest.main()
