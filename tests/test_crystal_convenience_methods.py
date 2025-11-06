"""
Tests for convenience methods in Crystal class.

Tests make_supercell() and perturb() methods that call transformation modules.
"""

import numpy as np
import unittest
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype


class TestCrystalConvenienceMethods(unittest.TestCase):
    """Test convenience methods in Crystal class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    def test_make_supercell_inplace(self):
        """Test make_supercell with inplace=True (default)."""
        original_len = len(self.crystal)
        original_lattice_a = self.crystal.lattice.a
        
        # Create 2x2x2 supercell
        result = self.crystal.make_supercell([2, 2, 2])
        
        # Should modify in-place
        self.assertIs(result, self.crystal)
        self.assertEqual(len(self.crystal), original_len * 8)  # 2^3 = 8
        self.assertAlmostEqual(self.crystal.lattice.a, original_lattice_a * 2, places=5)
    
    def test_make_supercell_not_inplace(self):
        """Test make_supercell with inplace=False."""
        original_len = len(self.crystal)
        original_lattice_a = self.crystal.lattice.a
        
        # Create 2x2x2 supercell without modifying original
        new_crystal = self.crystal.make_supercell([2, 2, 2], inplace=False)
        
        # Original should be unchanged
        self.assertEqual(len(self.crystal), original_len)
        self.assertAlmostEqual(self.crystal.lattice.a, original_lattice_a, places=5)
        
        # New crystal should be supercell
        self.assertIsNot(new_crystal, self.crystal)
        self.assertEqual(len(new_crystal), original_len * 8)
        self.assertAlmostEqual(new_crystal.lattice.a, original_lattice_a * 2, places=5)
    
    def test_make_supercell_matrix(self):
        """Test make_supercell with matrix scaling."""
        original_len = len(self.crystal)
        
        # Use matrix form
        scaling_matrix = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
        self.crystal.make_supercell(scaling_matrix)
        
        self.assertEqual(len(self.crystal), original_len * 8)
    
    def test_perturb_inplace(self):
        """Test perturb with inplace=True (default)."""
        original_positions = self.crystal.positions.copy()
        
        # Perturb with fixed seed
        result = self.crystal.perturb(0.1, seed=42)
        
        # Should modify in-place
        self.assertIs(result, self.crystal)
        # Positions should have changed
        self.assertFalse(np.allclose(original_positions, self.crystal.positions))
    
    def test_perturb_not_inplace(self):
        """Test perturb with inplace=False."""
        original_positions = self.crystal.positions.copy()
        
        # Perturb without modifying original
        new_crystal = self.crystal.perturb(0.1, seed=42, inplace=False)
        
        # Original should be unchanged
        self.assertTrue(np.allclose(original_positions, self.crystal.positions))
        
        # New crystal should be perturbed
        self.assertIsNot(new_crystal, self.crystal)
        self.assertFalse(np.allclose(original_positions, new_crystal.positions))
    
    def test_perturb_specific_indices(self):
        """Test perturb with specific atom indices."""
        original_positions = self.crystal.positions.copy()
        
        # Perturb only first atom
        self.crystal.perturb(0.1, indices=[0], seed=42)
        
        # First atom should be perturbed
        self.assertFalse(np.allclose(original_positions[0], self.crystal.positions[0]))
        
        # Other atoms should be unchanged
        self.assertTrue(np.allclose(original_positions[1:], self.crystal.positions[1:]))
    
    def test_perturb_reproducibility(self):
        """Test that perturb is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)
        
        # Perturb both with same seed
        crystal1.perturb(0.1, seed=42)
        crystal2.perturb(0.1, seed=42)
        
        # Should get same result
        self.assertTrue(np.allclose(crystal1.positions, crystal2.positions))


if __name__ == '__main__':
    unittest.main()

