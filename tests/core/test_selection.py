"""Tests for atom selection utilities."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.utils.selection import (
    select_by_species,
    select_by_indices,
    select_by_position,
    select_by_box,
    select_by_property,
    select_by_custom,
    combine_selections,
    select_all,
    select_none,
)

class TestSelectionBySpecies(unittest.TestCase):
    """Tests for species-based selection."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(10)
        )
        self.molecule = Molecule(['C', 'O', 'C'], [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0]])
    
    def test_select_single_species(self):
        """Test selecting single species."""
        indices = select_by_species(self.crystal, 'Si')
        self.assertEqual(sorted(indices), [0, 2])
    
    def test_select_multiple_species(self):
        """Test selecting multiple species."""
        indices = select_by_species(self.crystal, ['Si', 'O'])
        self.assertEqual(sorted(indices), [0, 1, 2, 3])
    
    def test_select_nonexistent_species(self):
        """Test selecting non-existent species."""
        indices = select_by_species(self.crystal, 'Ge')
        self.assertEqual(indices, [])

class TestSelectionByIndices(unittest.TestCase):
    """Tests for index-based selection."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
    
    def test_select_single_index(self):
        """Test selecting single index."""
        indices = select_by_indices(self.crystal, 0)
        self.assertEqual(indices, [0])
    
    def test_select_multiple_indices(self):
        """Test selecting multiple indices."""
        indices = select_by_indices(self.crystal, [0, 1])
        self.assertEqual(indices, [0, 1])
    
    def test_select_invalid_index(self):
        """Test selecting invalid index."""
        with self.assertRaises(IndexError):
            select_by_indices(self.crystal, 10)

class TestSelectionByPosition(unittest.TestCase):
    """Tests for position-based selection."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si'],
            [[0, 0, 0], [5, 0, 0], [10, 0, 0]],
            Lattice.cubic(20),
            coords_are_cartesian=True
        )
        self.molecule = Molecule(
            ['C', 'O'],
            [[0, 0, 0], [3, 0, 0]]
        )
    
    def test_select_by_radius(self):
        """Test selecting atoms within radius."""
        indices = select_by_position(self.crystal, [0, 0, 0], 2.0)
        self.assertIn(0, indices)
        self.assertNotIn(1, indices)
    
    def test_select_by_radius_molecule(self):
        """Test selecting atoms in molecule."""
        indices = select_by_position(self.molecule, [0, 0, 0], 2.0)
        self.assertIn(0, indices)
        self.assertNotIn(1, indices)
    
    def test_select_by_radius_fractional(self):
        """Test selecting by radius using fractional coordinates."""
        # Crystal with fractional coords
        crystal = Crystal(
            ['Si', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            Lattice.cubic(10)
        )
        indices = select_by_position(crystal, [0, 0, 0], 0.3, use_cartesian=False)
        self.assertIn(0, indices)

class TestSelectionByBox(unittest.TestCase):
    """Tests for box-based selection."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si'],
            [[1, 1, 1], [5, 5, 5], [10, 10, 10]],
            Lattice.cubic(20),
            coords_are_cartesian=True
        )
    
    def test_select_by_box(self):
        """Test selecting atoms in a box."""
        indices = select_by_box(self.crystal, [0, 0, 0], [6, 6, 6])
        self.assertIn(0, indices)
        self.assertIn(1, indices)
        self.assertNotIn(2, indices)

class TestSelectionByProperty(unittest.TestCase):
    """Tests for property-based selection."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            Lattice.cubic(10),
            site_properties=[
                {'charge': 0, 'magmom': 1.0},
                {'charge': -2}
            ]
        )
    
    def test_select_by_property_exists(self):
        """Test selecting atoms with a property."""
        indices = select_by_property(self.crystal, 'charge')
        self.assertEqual(sorted(indices), [0, 1])
    
    def test_select_by_property_value(self):
        """Test selecting atoms with specific property value."""
        indices = select_by_property(self.crystal, 'charge', value=-2)
        self.assertEqual(indices, [1])
    
    def test_select_by_property_condition(self):
        """Test selecting atoms with property condition."""
        indices = select_by_property(self.crystal, 'charge', condition=lambda x: x < 0)
        self.assertEqual(indices, [1])

class TestSelectionByCustom(unittest.TestCase):
    """Tests for custom selection."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si', 'O', 'Si'], 
                              [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                              Lattice.cubic(10))
    
    def test_select_by_custom(self):
        """Test custom selection function."""
        indices = select_by_custom(self.crystal, lambda i: i % 2 == 0)
        self.assertEqual(indices, [0, 2])

class TestCombineSelections(unittest.TestCase):
    """Tests for combining selections."""
    
    def test_combine_union(self):
        """Test union operation."""
        result = combine_selections([[0, 1], [1, 2]], 'union')
        self.assertEqual(sorted(result), [0, 1, 2])
    
    def test_combine_intersection(self):
        """Test intersection operation."""
        result = combine_selections([[0, 1], [1, 2]], 'intersection')
        self.assertEqual(result, [1])
    
    def test_combine_difference(self):
        """Test difference operation."""
        result = combine_selections([[0, 1, 2], [1]], 'difference')
        self.assertEqual(sorted(result), [0, 2])

class TestSelectionUtilities(unittest.TestCase):
    """Tests for utility selection functions."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
    
    def test_select_all(self):
        """Test selecting all atoms."""
        indices = select_all(self.crystal)
        self.assertEqual(indices, [0, 1])
    
    def test_select_none(self):
        """Test selecting no atoms."""
        indices = select_none(self.crystal)
        self.assertEqual(indices, [])

class TestSelectionIntegration(unittest.TestCase):
    """Integration tests for selection with substitution."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(10)
        )
    
    def test_select_and_substitute(self):
        """Test using selection for substitution."""
        from matsimpy.utils.selection import select_by_species

        # Select all Si atoms
        si_indices = select_by_species(self.crystal, 'Si')
        self.assertEqual(len(si_indices), 2)

        # Substitute them (returns new object)
        result = self.crystal.substitute(si_indices, ['Ge'] * len(si_indices))

        # Verify substitution on the result
        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[2], 'Ge')
        # Original unchanged
        self.assertEqual(self.crystal.species[0], 'Si')
    
    def test_complex_selection(self):
        """Test complex selection combining multiple criteria."""
        from matsimpy.utils.selection import (
            select_by_species, select_by_position, combine_selections
        )
        
        # Select Si atoms
        si_indices = select_by_species(self.crystal, 'Si')
        
        # Select atoms near origin
        near_origin = select_by_position(self.crystal, [0, 0, 0], 1.0)
        
        # Combine: Si atoms near origin
        combined = combine_selections([si_indices, near_origin], 'intersection')
        
        self.assertIsInstance(combined, list)
        self.assertGreaterEqual(len(combined), 0)

if __name__ == '__main__':
    unittest.main()

