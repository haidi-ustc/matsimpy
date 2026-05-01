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
        """Test make_supercell returns new object (previously inplace=True)."""
        original_len = len(self.crystal)
        original_lattice_a = self.crystal.lattice.a
        original_positions = self.crystal.positions.copy()

        # Create 2x2x2 supercell
        result = self.crystal.make_supercell([2, 2, 2])

        # Should return new object, original unchanged
        self.assertIsNot(result, self.crystal)
        self.assertEqual(len(self.crystal), original_len)
        self.assertAlmostEqual(self.crystal.lattice.a, original_lattice_a, places=5)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # Result should be supercell
        self.assertEqual(len(result), original_len * 8)  # 2^3 = 8
        self.assertAlmostEqual(result.lattice.a, original_lattice_a * 2, places=5)

    def test_make_supercell_not_inplace(self):
        """Test make_supercell with default behavior (returns new object)."""
        original_len = len(self.crystal)
        original_lattice_a = self.crystal.lattice.a

        # Create 2x2x2 supercell without modifying original (default behavior)
        new_crystal = self.crystal.make_supercell([2, 2, 2])

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
        original_positions = self.crystal.positions.copy()

        # Use matrix form
        scaling_matrix = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
        result = self.crystal.make_supercell(scaling_matrix)

        # Original should be unchanged
        self.assertEqual(len(self.crystal), original_len)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # Result should be supercell
        self.assertEqual(len(result), original_len * 8)

    def test_perturb_returns_new_object(self):
        """Test perturb returns new object (was inplace by default)."""
        original_positions = self.crystal.positions.copy()

        # Perturb with fixed seed
        result = self.crystal.perturb(0.1, seed=42)

        # Should return new object, original unchanged
        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # Result positions should have changed
        self.assertFalse(np.allclose(original_positions, result.positions))

    def test_perturb_specific_indices(self):
        """Test perturb with specific atom indices."""
        original_positions = self.crystal.positions.copy()

        # Perturb only first atom
        result = self.crystal.perturb(0.1, indices=[0], seed=42)

        # Original should be unchanged
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # First atom should be perturbed in result
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))

        # Other atoms should be unchanged
        self.assertTrue(np.allclose(original_positions[1:], result.positions[1:]))

    def test_perturb_reproducibility(self):
        """Test that perturb is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)

        # Perturb both with same seed
        result1 = crystal1.perturb(0.1, seed=42)
        result2 = crystal2.perturb(0.1, seed=42)

        # Should get same result
        self.assertTrue(np.allclose(result1.positions, result2.positions))

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
        result = crystal.perturb(0.1, indices=sel, seed=42)

        # Original should be unchanged
        self.assertTrue(np.allclose(crystal.positions, original_positions))

        # Si atoms should be perturbed in result
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))
        self.assertFalse(np.allclose(original_positions[2], result.positions[2]))

        # O atoms should be unchanged in result
        self.assertTrue(np.allclose(original_positions[1], result.positions[1]))
        self.assertTrue(np.allclose(original_positions[3], result.positions[3]))

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

        # Should return new object, original unchanged
        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.lattice.lattice_vectors, original_lattice))
        self.assertAlmostEqual(self.crystal.volume, original_volume, places=5)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # Lattice should have changed in result
        self.assertFalse(np.allclose(original_lattice, result.lattice.lattice_vectors))
        self.assertNotAlmostEqual(original_volume, result.volume, places=3)

        # Positions should be unchanged in result (fractional)
        self.assertTrue(np.allclose(original_positions, result.positions))

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

        # Should return new object, original unchanged
        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.lattice.lattice_vectors, original_lattice))
        self.assertAlmostEqual(self.crystal.volume, original_volume, places=5)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # Both should have changed in result
        self.assertFalse(np.allclose(original_lattice, result.lattice.lattice_vectors))
        self.assertFalse(np.allclose(original_positions, result.positions))
        self.assertNotAlmostEqual(original_volume, result.volume, places=3)

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

        # Should return new object, original unchanged
        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.lattice.lattice_vectors, original_lattice))
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))

        # Both should have changed in result
        self.assertFalse(np.allclose(original_lattice, result.lattice.lattice_vectors))
        self.assertFalse(np.allclose(original_positions, result.positions))

    def test_perturb_lattice_reproducibility(self):
        """Test that lattice perturbation is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)

        # Perturb lattice of both with same seed
        result1 = crystal1.perturb(0.1, perturb_positions=False, perturb_lattice=True, seed=42)
        result2 = crystal2.perturb(0.1, perturb_positions=False, perturb_lattice=True, seed=42)

        # Should get same result
        self.assertTrue(np.allclose(
            result1.lattice.lattice_vectors,
            result2.lattice.lattice_vectors
        ))

    def test_perturb_both_reproducibility(self):
        """Test that perturbing both is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)

        # Perturb both with same seed
        result1 = crystal1.perturb(0.1, perturb_lattice=True, seed=42)
        result2 = crystal2.perturb(0.1, perturb_lattice=True, seed=42)

        # Should get same result
        self.assertTrue(np.allclose(result1.positions, result2.positions))
        self.assertTrue(np.allclose(
            result1.lattice.lattice_vectors,
            result2.lattice.lattice_vectors
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

        # Should return new object
        self.assertIsNot(result, self.crystal)

        # Original should be unchanged
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))
        self.assertTrue(np.allclose(self.crystal.lattice.lattice_vectors, original_lattice))

        # Result positions should have changed
        self.assertFalse(np.allclose(original_positions, result.positions))

        # Result lattice should be unchanged
        self.assertTrue(np.allclose(original_lattice, result.lattice.lattice_vectors))


if __name__ == '__main__':
    unittest.main()
