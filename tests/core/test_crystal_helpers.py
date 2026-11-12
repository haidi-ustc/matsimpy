"""Tests for Crystal helper methods and internal consistency."""
import unittest

from matsimpy.core import Crystal, Lattice

class TestCrystalIntegration(unittest.TestCase):
    """Integration tests for Crystal helper behavior."""

    def test_multiple_modifications_work_together(self):
        """Test that multiple modifications work correctly."""
        lattice = Lattice(10)
        crystal = Crystal(['Si'], [[0,0,0]], lattice)

        # Add atoms (returns new object)
        crystal = crystal.add_atom(['O', 'O'], [[0.25,0,0], [0.75,0,0]])
        self.assertEqual(len(crystal), 3)

        # Substitute (returns new object)
        crystal = crystal.substitute(0, 'Ge')
        self.assertEqual(crystal.species[0], 'Ge')

        # Sort (returns new object)
        crystal = crystal.sort_atoms('alphabet')

        # Remove (returns new object)
        crystal = crystal.remove_atom(0)
        self.assertEqual(len(crystal), 2)

        # All should work without errors
        self.assertIsInstance(crystal.formula, str)

if __name__ == '__main__':
    unittest.main()
