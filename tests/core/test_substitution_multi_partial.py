"""Tests for multiple partial substitutions."""
import unittest

from matsimpy.core import Crystal, Lattice
from matsimpy.analysis.selection import AtomSelection

class TestMultiplePartialSubstitutions(unittest.TestCase):
    """Tests for multiple partial substitutions on different species."""

    def setUp(self):
        """Set up test structures."""
        # CaCO3-like structure: Ca, Ca, C, C, O, O, O
        self.crystal = Crystal(
            ['Ca', 'Ca', 'C', 'C', 'O', 'O', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0.25, 0, 0], [0.75, 0, 0],
             [0.125, 0.125, 0.125], [0.625, 0.625, 0.625], [0.875, 0.875, 0.875]],
            Lattice.cubic(10)
        )

    def test_combined_selection_partial_substitutions(self):
        """Test combined selection for multiple partial substitutions."""
        crystal = Crystal(
            ['Ca', 'Ca', 'C', 'C', 'O', 'O', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0.25, 0, 0], [0.75, 0, 0],
             [0.125, 0.125, 0.125], [0.625, 0.625, 0.625], [0.875, 0.875, 0.875]],
            Lattice.cubic(10)
        )

        # Select first Ca and first C
        sel_ca = AtomSelection(crystal).by_species('Ca').by_indices([0])
        sel_c = AtomSelection(crystal).by_species('C').by_indices([2])
        combined = sel_ca | sel_c

        # Substitute both with dict mapping
        result = crystal.substitute(combined, {'Ca': 'Ba', 'C': 'Si'})

        self.assertEqual(result.species[0], 'Ba')
        self.assertEqual(result.species[1], 'Ca')  # Not substituted
        self.assertEqual(result.species[2], 'Si')
        self.assertEqual(result.species[3], 'C')  # Not substituted


if __name__ == '__main__':
    unittest.main()
