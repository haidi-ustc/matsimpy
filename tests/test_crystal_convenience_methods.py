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
    
    def test_perturb_atom_selection(self):
        """Test perturb with AtomSelection object."""
        from matsimpy.utils.selection import AtomSelection
        
        # Create crystal with multiple species
        crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5], [0.75, 0.75, 0.75]],
            Lattice.cubic(5.0)
        )
        original_positions = crystal.positions.copy()
        
        # Select Si atoms and perturb only them
        sel = AtomSelection(crystal).by_species('Si')
        crystal.perturb(0.1, indices=sel, seed=42)
        
        # Si atoms should be perturbed
        self.assertFalse(np.allclose(original_positions[0], crystal.positions[0]))
        self.assertFalse(np.allclose(original_positions[2], crystal.positions[2]))
        
        # O atoms should be unchanged
        self.assertTrue(np.allclose(original_positions[1], crystal.positions[1]))
        self.assertTrue(np.allclose(original_positions[3], crystal.positions[3]))
    
    def test_perturb_atom_selection_wrong_structure(self):
        """Test that AtomSelection from different structure raises error."""
        from matsimpy.utils.selection import AtomSelection
        
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)
        
        # Create selection from crystal1 but try to use on crystal2
        sel = AtomSelection(crystal1).by_species('Si')
        
        with self.assertRaises(ValueError):
            crystal2.perturb(0.1, indices=sel)
    
    def test_perturb_lattice_only(self):
        """Test perturbing lattice only."""
        original_lattice = self.crystal.lattice.lattice_vectors.copy()
        original_volume = self.crystal.volume
        original_positions = self.crystal.positions.copy()
        
        # Perturb lattice only
        result = self.crystal.perturb(
            0.1, 
            perturb_positions=False, 
            perturb_lattice=True, 
            seed=42
        )
        
        # Should modify in-place
        self.assertIs(result, self.crystal)
        
        # Lattice should have changed
        self.assertFalse(np.allclose(original_lattice, self.crystal.lattice.lattice_vectors))
        self.assertNotAlmostEqual(original_volume, self.crystal.volume, places=3)
        
        # Positions should be unchanged (fractional)
        self.assertTrue(np.allclose(original_positions, self.crystal.positions))
    
    def test_perturb_both_positions_and_lattice(self):
        """Test perturbing both positions and lattice."""
        original_lattice = self.crystal.lattice.lattice_vectors.copy()
        original_volume = self.crystal.volume
        original_positions = self.crystal.positions.copy()
        
        # Perturb both
        result = self.crystal.perturb(
            0.1, 
            perturb_positions=True, 
            perturb_lattice=True, 
            seed=42
        )
        
        # Should modify in-place
        self.assertIs(result, self.crystal)
        
        # Both should have changed
        self.assertFalse(np.allclose(original_lattice, self.crystal.lattice.lattice_vectors))
        self.assertFalse(np.allclose(original_positions, self.crystal.positions))
        self.assertNotAlmostEqual(original_volume, self.crystal.volume, places=3)
    
    def test_perturb_different_amplitudes(self):
        """Test using different amplitudes for positions and lattice."""
        original_lattice = self.crystal.lattice.lattice_vectors.copy()
        original_positions = self.crystal.positions.copy()
        
        # Perturb with different amplitudes
        result = self.crystal.perturb(
            0.1,  # amplitude for positions
            perturb_lattice=True,
            amplitude_lattice=0.05,  # smaller amplitude for lattice
            seed=42
        )
        
        # Should modify in-place
        self.assertIs(result, self.crystal)
        
        # Both should have changed
        self.assertFalse(np.allclose(original_lattice, self.crystal.lattice.lattice_vectors))
        self.assertFalse(np.allclose(original_positions, self.crystal.positions))
    
    def test_perturb_lattice_only_not_inplace(self):
        """Test perturbing lattice only with inplace=False."""
        original_lattice = self.crystal.lattice.lattice_vectors.copy()
        original_volume = self.crystal.volume
        
        # Perturb lattice without modifying original
        new_crystal = self.crystal.perturb(
            0.1,
            perturb_positions=False,
            perturb_lattice=True,
            seed=42,
            inplace=False
        )
        
        # Original should be unchanged
        self.assertTrue(np.allclose(original_lattice, self.crystal.lattice.lattice_vectors))
        self.assertAlmostEqual(original_volume, self.crystal.volume, places=5)
        
        # New crystal should be perturbed
        self.assertIsNot(new_crystal, self.crystal)
        self.assertFalse(np.allclose(original_lattice, new_crystal.lattice.lattice_vectors))
        self.assertNotAlmostEqual(original_volume, new_crystal.volume, places=3)
    
    def test_perturb_both_not_inplace(self):
        """Test perturbing both with inplace=False."""
        original_lattice = self.crystal.lattice.lattice_vectors.copy()
        original_positions = self.crystal.positions.copy()
        
        # Perturb both without modifying original
        new_crystal = self.crystal.perturb(
            0.1,
            perturb_positions=True,
            perturb_lattice=True,
            seed=42,
            inplace=False
        )
        
        # Original should be unchanged
        self.assertTrue(np.allclose(original_lattice, self.crystal.lattice.lattice_vectors))
        self.assertTrue(np.allclose(original_positions, self.crystal.positions))
        
        # New crystal should be perturbed
        self.assertIsNot(new_crystal, self.crystal)
        self.assertFalse(np.allclose(original_lattice, new_crystal.lattice.lattice_vectors))
        self.assertFalse(np.allclose(original_positions, new_crystal.positions))
    
    def test_perturb_lattice_reproducibility(self):
        """Test that lattice perturbation is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)
        
        # Perturb lattice of both with same seed
        crystal1.perturb(0.1, perturb_positions=False, perturb_lattice=True, seed=42)
        crystal2.perturb(0.1, perturb_positions=False, perturb_lattice=True, seed=42)
        
        # Should get same result
        self.assertTrue(np.allclose(
            crystal1.lattice.lattice_vectors, 
            crystal2.lattice.lattice_vectors
        ))
    
    def test_perturb_both_reproducibility(self):
        """Test that perturbing both is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)
        
        # Perturb both with same seed
        crystal1.perturb(0.1, perturb_lattice=True, seed=42)
        crystal2.perturb(0.1, perturb_lattice=True, seed=42)
        
        # Should get same result
        self.assertTrue(np.allclose(crystal1.positions, crystal2.positions))
        self.assertTrue(np.allclose(
            crystal1.lattice.lattice_vectors, 
            crystal2.lattice.lattice_vectors
        ))
    
    def test_perturb_error_both_false(self):
        """Test that ValueError is raised when both perturb options are False."""
        with self.assertRaises(ValueError) as context:
            self.crystal.perturb(
                0.1,
                perturb_positions=False,
                perturb_lattice=False
            )
        
        self.assertIn("At least one of perturb_positions or perturb_lattice must be True", 
                     str(context.exception))
    
    def test_perturb_backward_compatibility(self):
        """Test that default behavior (positions only) is backward compatible."""
        original_lattice = self.crystal.lattice.lattice_vectors.copy()
        original_positions = self.crystal.positions.copy()
        
        # Default call should only perturb positions (backward compatible)
        result = self.crystal.perturb(0.1, seed=42)
        
        # Should modify in-place
        self.assertIs(result, self.crystal)
        
        # Positions should have changed
        self.assertFalse(np.allclose(original_positions, self.crystal.positions))
        
        # Lattice should be unchanged
        self.assertTrue(np.allclose(original_lattice, self.crystal.lattice.lattice_vectors))

if __name__ == '__main__':
    unittest.main()

