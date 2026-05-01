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
        """Test perturb returns new object (immutable)."""
        original_positions = self.molecule.positions.copy()

        # Perturb with fixed seed
        result = self.molecule.perturb(0.1, seed=42)

        # Should return a new object
        self.assertIsNot(result, self.molecule)
        # Original positions should be unchanged
        self.assertTrue(np.allclose(original_positions, self.molecule.positions))
        # Result positions should have changed
        self.assertFalse(np.allclose(original_positions, result.positions))
    
    def test_perturb_specific_indices(self):
        """Test perturb with specific atom indices."""
        original_positions = self.molecule.positions.copy()

        # Perturb only first atom
        result = self.molecule.perturb(0.1, indices=[0], seed=42)

        # Original should be unchanged
        self.assertTrue(np.allclose(original_positions, self.molecule.positions))

        # First atom should be perturbed in result
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))

        # Other atoms should be unchanged in result
        self.assertTrue(np.allclose(original_positions[1:], result.positions[1:]))
    
    def test_perturb_reproducibility(self):
        """Test that perturb is reproducible with same seed."""
        molecule1 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        molecule2 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])

        # Perturb both with same seed, capturing results
        result1 = molecule1.perturb(0.1, seed=42)
        result2 = molecule2.perturb(0.1, seed=42)

        # Should get same result
        self.assertTrue(np.allclose(result1.positions, result2.positions))

        # Originals should be unchanged
        self.assertTrue(np.allclose(molecule1.positions, [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]]))
        self.assertTrue(np.allclose(molecule2.positions, [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]]))
    
    def test_perturb_atom_selection(self):
        """Test perturb with AtomSelection object."""
        from matsimpy.utils.selection import AtomSelection

        # Create molecule with multiple species
        molecule = Molecule(
            ['H', 'O', 'H', 'C'],
            [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0], [1.5, 0, 0]]
        )
        original_positions = molecule.positions.copy()

        # Select H atoms and perturb only them
        sel = AtomSelection(molecule).by_species('H')
        result = molecule.perturb(0.1, indices=sel, seed=42)

        # Original should be unchanged
        self.assertTrue(np.allclose(original_positions, molecule.positions))

        # H atoms should be perturbed in result
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))
        self.assertFalse(np.allclose(original_positions[2], result.positions[2]))

        # O and C atoms should be unchanged in result
        self.assertTrue(np.allclose(original_positions[1], result.positions[1]))
        self.assertTrue(np.allclose(original_positions[3], result.positions[3]))
    
    def test_perturb_atom_selection_wrong_structure(self):
        """Test that AtomSelection from different structure raises error."""
        from matsimpy.utils.selection import AtomSelection
        
        molecule1 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        molecule2 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        
        # Create selection from molecule1 but try to use on molecule2
        sel = AtomSelection(molecule1).by_species('H')
        
        with self.assertRaises(ValueError):
            molecule2.perturb(0.1, indices=sel)

if __name__ == '__main__':
    unittest.main()

