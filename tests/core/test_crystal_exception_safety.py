"""Tests for exception safety and rollback in Crystal operations."""
import unittest
from unittest.mock import patch
import numpy as np

from matsimpy.core import Crystal, Lattice

class TestCrystalExceptionSafety(unittest.TestCase):
    """Test exception safety and complete rollback in Crystal operations."""

    def setUp(self):
        self.lattice = Lattice.cubic(5.0)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)

    def test_add_atom_rollback(self):
        """Test that add_atom completely rolls back on error."""
        original_len = len(self.crystal)
        original_species = self.crystal.species
        original_positions = self.crystal.positions.copy()
        original_frac = self.crystal.frac_positions.copy()
        original_cart = self.crystal.cart_positions.copy()
        original_sites = len(self.crystal.sites)
        original_formula = self.crystal.formula

        # Should rollback completely on error
        with self.assertRaises(ValueError):
            self.crystal.add_atom(['H', 'O'], [[0, 0, 0], [0, 0, 0]])  # Duplicate

        # Verify complete rollback
        self.assertEqual(len(self.crystal), original_len)
        self.assertEqual(self.crystal.species, original_species)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))
        self.assertTrue(np.allclose(self.crystal.frac_positions, original_frac))
        self.assertTrue(np.allclose(self.crystal.cart_positions, original_cart))
        self.assertEqual(len(self.crystal.sites), original_sites)
        self.assertEqual(self.crystal.formula, original_formula)

    def test_add_atom_rollback_site_properties_error(self):
        """Test rollback when site_properties length mismatch."""
        original_len = len(self.crystal)
        original_species = self.crystal.species

        # Should rollback on site_properties error
        with self.assertRaises(ValueError):
            self.crystal.add_atom('O', [0.5, 0.5, 0.5], 
                                 site_properties=[{'charge': 1}, {'charge': 2}])  # Wrong length

        # Verify rollback
        self.assertEqual(len(self.crystal), original_len)
        self.assertEqual(self.crystal.species, original_species)

    def test_pbc_distance_checking(self):
        """Test PBC-aware distance checking detects duplicates across boundaries."""
        lattice = Lattice.cubic(5.0)
        crystal = Crystal(['Si'], [[0, 0, 0]], lattice)

        # Should detect duplicate across PBC boundary (1.0 fractional = 0.0 with PBC)
        with self.assertRaises(ValueError) as context:
            crystal.add_atom('Si', [1.0, 0.0, 0.0])  # Equivalent to [0,0,0] with PBC

        self.assertIn("already exists", str(context.exception).lower())

    def test_large_supercell_warning(self):
        """Test that large periodic image cache triggers warning."""
        with patch(
            "matsimpy.core.crystal._MAX_PERIODIC_IMAGE_CACHE_ATOMS", 1
        ):
            with self.assertWarnsRegex(UserWarning, "Large periodic image cache"):
                images = self.crystal._get_periodic_images(5.0)

        self.assertGreater(len(images), 1)


if __name__ == '__main__':
    unittest.main()
