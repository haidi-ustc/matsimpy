"""Tests for multiple partial substitutions."""
import unittest

from matsimpy.core import Crystal, Lattice
from matsimpy.utils.selection import AtomSelection

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

    def test_sequential_partial_substitutions(self):
        """Test sequential partial substitutions (Ca->Ba, then C->Si)."""
        # Select first Ca
        sel_ca = AtomSelection(self.crystal).by_species('Ca').by_indices([0])
        result = self.crystal.substitute(sel_ca, {'Ca': 'Ba'})

        self.assertEqual(result.species[0], 'Ba')
        self.assertEqual(result.species[1], 'Ca')  # Not substituted

        # Select first C on the result
        sel_c = AtomSelection(result).by_species('C').by_indices([2])
        result2 = result.substitute(sel_c, {'C': 'Si'})

        self.assertEqual(result2.species[2], 'Si')
        self.assertEqual(result2.species[3], 'C')  # Not substituted

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

    def test_partial_substitution_with_position(self):
        """Test partial substitution based on position."""
        crystal = Crystal(
            ['Ca', 'Ca', 'C', 'C', 'O', 'O', 'O'],
            [[0, 0, 0], [5, 0, 0], [2.5, 0, 0], [7.5, 0, 0],
             [1.25, 1.25, 1.25], [6.25, 6.25, 6.25], [8.75, 8.75, 8.75]],
            Lattice.cubic(10),
            coords_are_cartesian=True
        )

        # Select Ca atoms near origin
        sel_ca = AtomSelection(crystal).by_species('Ca').near([0, 0, 0], 3.0)
        result = crystal.substitute(sel_ca, {'Ca': 'Ba'})

        self.assertEqual(result.species[0], 'Ba')
        self.assertEqual(result.species[1], 'Ca')  # Too far

        # Select C atoms near origin on the result
        sel_c = AtomSelection(result).by_species('C').near([0, 0, 0], 3.0)
        result2 = result.substitute(sel_c, {'C': 'Si'})

        self.assertEqual(result2.species[2], 'Si')
        self.assertEqual(result2.species[3], 'C')  # Too far

    def test_multiple_substitutions_same_species(self):
        """Test multiple partial substitutions of the same species."""
        crystal = Crystal(
            ['Ca', 'Ca', 'Ca', 'C', 'O', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0.25, 0, 0], [0.75, 0, 0],
             [0.125, 0.125, 0.125], [0.625, 0.625, 0.625]],
            Lattice.cubic(10)
        )

        # Select first two Ca
        sel_ca = AtomSelection(crystal).by_species('Ca').by_indices([0, 1])
        result = crystal.substitute(sel_ca, {'Ca': 'Ba'})

        self.assertEqual(result.species[0], 'Ba')
        self.assertEqual(result.species[1], 'Ba')
        self.assertEqual(result.species[2], 'Ca')  # Not substituted

if __name__ == '__main__':
    unittest.main()
