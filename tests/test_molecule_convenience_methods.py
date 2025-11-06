"""
Tests for convenience methods in Molecule class.

Tests perturb() method that calls transformation modules.
"""

import numpy as np
import unittest
from matsimpy.core import Molecule


class TestMoleculeConvenienceMethods(unittest.TestCase):
    """Test convenience methods in Molecule class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.molecule = Molecule(
            ['H', 'O', 'H'],
            [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]]
        )
    
    def test_perturb_inplace(self):
        """Test perturb with inplace=True (default)."""
        original_positions = self.molecule.positions.copy()
        
        # Perturb with fixed seed
        result = self.molecule.perturb(0.1, seed=42)
        
        # Should modify in-place
        self.assertIs(result, self.molecule)
        # Positions should have changed
        self.assertFalse(np.allclose(original_positions, self.molecule.positions))
    
    def test_perturb_not_inplace(self):
        """Test perturb with inplace=False."""
        original_positions = self.molecule.positions.copy()
        
        # Perturb without modifying original
        new_molecule = self.molecule.perturb(0.1, seed=42, inplace=False)
        
        # Original should be unchanged
        self.assertTrue(np.allclose(original_positions, self.molecule.positions))
        
        # New molecule should be perturbed
        self.assertIsNot(new_molecule, self.molecule)
        self.assertFalse(np.allclose(original_positions, new_molecule.positions))
    
    def test_perturb_specific_indices(self):
        """Test perturb with specific atom indices."""
        original_positions = self.molecule.positions.copy()
        
        # Perturb only first atom
        self.molecule.perturb(0.1, indices=[0], seed=42)
        
        # First atom should be perturbed
        self.assertFalse(np.allclose(original_positions[0], self.molecule.positions[0]))
        
        # Other atoms should be unchanged
        self.assertTrue(np.allclose(original_positions[1:], self.molecule.positions[1:]))
    
    def test_perturb_reproducibility(self):
        """Test that perturb is reproducible with same seed."""
        molecule1 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        molecule2 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        
        # Perturb both with same seed
        molecule1.perturb(0.1, seed=42)
        molecule2.perturb(0.1, seed=42)
        
        # Should get same result
        self.assertTrue(np.allclose(molecule1.positions, molecule2.positions))


if __name__ == '__main__':
    unittest.main()

