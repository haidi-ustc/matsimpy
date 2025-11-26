"""Tests for AtomSelection class."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.utils.selection import AtomSelection

class TestAtomSelectionBasic(unittest.TestCase):
    """Tests for basic AtomSelection functionality."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [5, 0, 0], [10, 0, 0], [15, 0, 0]],
            Lattice.cubic(20),
            coords_are_cartesian=True
        )
        self.molecule = Molecule(['C', 'O', 'C'], [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0]])
    
    def test_basic_selection(self):
        """Test basic selection."""
        sel = AtomSelection(self.crystal).by_species('Si')
        self.assertEqual(sorted(sel.indices), [0, 2])
    
    def test_chaining(self):
        """Test method chaining."""
        sel = AtomSelection(self.crystal).by_species('Si').near([0, 0, 0], 5.0)
        self.assertEqual(sel.indices, [0])
    
    def test_length(self):
        """Test len() method."""
        sel = AtomSelection(self.crystal).by_species('Si')
        self.assertEqual(len(sel), 2)
    
    def test_bool(self):
        """Test bool() method."""
        sel = AtomSelection(self.crystal).by_species('Si')
        self.assertTrue(sel)
        
        empty = AtomSelection(self.crystal).by_species('Ge')
        self.assertFalse(empty)
    
    def test_iteration(self):
        """Test iteration."""
        sel = AtomSelection(self.crystal).by_species('Si')
        indices = list(sel)
        self.assertEqual(indices, [0, 2])

class TestAtomSelectionOperations(unittest.TestCase):
    """Tests for AtomSelection operations."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [5, 0, 0], [10, 0, 0], [15, 0, 0]],
            Lattice.cubic(20),
            coords_are_cartesian=True
        )
    
    def test_intersection(self):
        """Test intersection operation (&)."""
        sel1 = AtomSelection(self.crystal).by_species('Si')
        sel2 = AtomSelection(self.crystal).near([0, 0, 0], 5.0)
        combined = sel1 & sel2
        self.assertEqual(combined.indices, [0])
    
    def test_union(self):
        """Test union operation (|)."""
        sel1 = AtomSelection(self.crystal).by_species('Si')
        sel2 = AtomSelection(self.crystal).by_species('O')
        combined = sel1 | sel2
        self.assertEqual(sorted(combined.indices), [0, 1, 2, 3])
    
    def test_difference(self):
        """Test difference operation (-)."""
        sel1 = AtomSelection(self.crystal).by_species('Si')
        sel2 = AtomSelection(self.crystal).near([0, 0, 0], 5.0)
        combined = sel1 - sel2
        self.assertEqual(combined.indices, [2])

class TestAtomSelectionWithSubstitution(unittest.TestCase):
    """Tests for AtomSelection used with substitution."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si'],
            [[0, 0, 0], [5, 0, 0], [10, 0, 0]],
            Lattice.cubic(20),
            coords_are_cartesian=True
        )
    
    def test_substitute_with_selection(self):
        """Test substitution using AtomSelection."""
        sel = AtomSelection(self.crystal).by_species('Si')
        self.crystal.substitute(sel, 'Ge')
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], 'O')
        self.assertEqual(self.crystal.species[2], 'Ge')
    
    def test_substitute_with_chained_selection(self):
        """Test substitution with chained selection."""
        sel = AtomSelection(self.crystal).by_species('Si').near([0, 0, 0], 5.0)
        self.crystal.substitute(sel, 'Ge')
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], 'O')
        self.assertEqual(self.crystal.species[2], 'Si')  # Not substituted
    
    def test_substitute_with_combined_selection(self):
        """Test substitution with combined selections."""
        sel1 = AtomSelection(self.crystal).by_species('Si')
        sel2 = AtomSelection(self.crystal).near([0, 0, 0], 5.0)
        combined = sel1 & sel2
        
        self.crystal.substitute(combined, 'Ge')
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[2], 'Si')  # Not substituted
    
    def test_substitute_wrong_structure(self):
        """Test that substitution with wrong structure raises error."""
        crystal2 = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(10))
        sel = AtomSelection(self.crystal).by_species('Si')
        
        with self.assertRaises(ValueError):
            crystal2.substitute(sel, 'Ge')

class TestAtomSelectionMethods(unittest.TestCase):
    """Tests for AtomSelection methods."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si'],
            [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
            Lattice.cubic(10),
            site_properties=[
                {'charge': 0},
                {'charge': -2},
                {'charge': 0}
            ]
        )
    
    def test_by_indices(self):
        """Test by_indices method."""
        sel = AtomSelection(self.crystal).by_indices([0, 2])
        self.assertEqual(sel.indices, [0, 2])
    
    def test_in_box(self):
        """Test in_box method."""
        sel = AtomSelection(self.crystal).in_box([0, 0, 0], [1, 1, 1], use_cartesian=False)
        self.assertIsInstance(sel, AtomSelection)
    
    def test_by_property(self):
        """Test by_property method."""
        sel = AtomSelection(self.crystal).by_property('charge', value=-2)
        self.assertEqual(sel.indices, [1])
    
    def test_by_custom(self):
        """Test by_custom method."""
        sel = AtomSelection(self.crystal).by_custom(lambda i: i % 2 == 0)
        self.assertEqual(sel.indices, [0, 2])

if __name__ == '__main__':
    unittest.main()

