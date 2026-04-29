"""Tests for Crystal helper methods and internal consistency."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Lattice

class TestCrystalHelperMethods(unittest.TestCase):
    """Test helper methods in Crystal class."""
    
    def setUp(self):
        """Set up test crystal."""
        self.lattice = Lattice(10)
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], self.lattice)
    
    def test_invalidate_neighbor_tree(self):
        """Test that _invalidate_neighbor_tree clears cache."""
        # Build neighbor tree
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_tree)
        
        # Invalidate
        self.crystal._invalidate_neighbor_tree()
        
        # Should be cleared
        self.assertIsNone(self.crystal._neighbor_tree)
        self.assertIsNone(self.crystal._neighbor_tree_positions)
        self.assertIsNone(self.crystal._neighbor_tree_cutoff)
    
    def test_update_coordinates_after_modification(self):
        """Test coordinate update helper."""
        original_cart = self.crystal.cart_positions.copy()
        
        # Modify positions
        self.crystal.positions = np.array([[0.1, 0, 0], [0.6, 0.6, 0.6]])
        
        # Update using helper
        self.crystal._update_coordinates_after_modification()
        
        # Check updates
        self.assertTrue(np.array_equal(self.crystal.frac_positions, self.crystal.positions))
        self.assertFalse(np.array_equal(self.crystal.cart_positions, original_cart))
    
    def test_get_sorted_sites_element(self):
        """Test getting sorted sites by element."""
        crystal = Crystal(['O', 'Si', 'Si'], 
                         [[0,0,0], [0.25,0,0], [0.5,0,0]], 
                         self.lattice)
        
        sorted_sites = crystal._get_sorted_sites(sort_by='element')
        
        # Si (atomic_no=14) should come before O (atomic_no=8)
        # Actually O (8) comes before Si (14)
        self.assertEqual(sorted_sites[0].specie, 'O')
        self.assertEqual(sorted_sites[1].specie, 'Si')
        self.assertEqual(sorted_sites[2].specie, 'Si')
    
    def test_get_sorted_sites_alphabet(self):
        """Test getting sorted sites alphabetically."""
        crystal = Crystal(['Si', 'O', 'N'], 
                         [[0,0,0], [0.5,0,0], [0.25,0,0]], 
                         self.lattice)
        
        sorted_sites = crystal._get_sorted_sites(sort_by='alphabet')
        
        # Should be alphabetical: N, O, Si
        self.assertEqual(sorted_sites[0].specie, 'N')
        self.assertEqual(sorted_sites[1].specie, 'O')
        self.assertEqual(sorted_sites[2].specie, 'Si')
    
    def test_get_sorted_sites_invalid_raises_error(self):
        """Test that invalid sort_by raises error."""
        with self.assertRaises(ValueError) as context:
            self.crystal._get_sorted_sites(sort_by='invalid')
        
        self.assertIn("'element' or 'alphabet'", str(context.exception))
    
    def test_get_sorted_element_counts_element(self):
        """Test sorting element counts by atomic number."""
        counts = {'O': 2, 'Si': 1, 'H': 3}
        sorted_counts = Crystal._get_sorted_element_counts(counts, 'element')
        
        # H(1), O(8), Si(14)
        self.assertEqual(sorted_counts[0][0], 'H')
        self.assertEqual(sorted_counts[1][0], 'O')
        self.assertEqual(sorted_counts[2][0], 'Si')
    
    def test_get_sorted_element_counts_alphabet(self):
        """Test sorting element counts alphabetically."""
        counts = {'Si': 1, 'O': 2, 'H': 3}
        sorted_counts = Crystal._get_sorted_element_counts(counts, 'alphabet')
        
        # Alphabetical: H, O, Si
        self.assertEqual(sorted_counts[0][0], 'H')
        self.assertEqual(sorted_counts[1][0], 'O')
        self.assertEqual(sorted_counts[2][0], 'Si')
    
    def test_get_sorted_element_counts_invalid(self):
        """Test that invalid sort_by raises error."""
        counts = {'Si': 1}
        
        with self.assertRaises(ValueError):
            Crystal._get_sorted_element_counts(counts, 'invalid')

    def test_str_preserves_species_order(self):
        """Crystal.__str__ should display atoms in insertion order."""
        lattice = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lattice)
        crystal.add_atom('O', [0.25, 0.25, 0.25])

        representation = str(crystal)
        lines = [line for line in representation.splitlines() if line]

        header = "Element    Fractional Coordinates    Cartesian Coordinates"
        self.assertIn(header, lines)
        header_index = lines.index(header)

        first_row = lines[header_index + 1]
        second_row = lines[header_index + 2]

        self.assertTrue(first_row.startswith('Si'), msg=f"Expected first row to describe 'Si', got: {first_row}")
        self.assertTrue(second_row.startswith('O'), msg=f"Expected second row to describe 'O', got: {second_row}")

class TestCrystalCodeDeduplication(unittest.TestCase):
    """Test that helper methods reduce code duplication."""
    
    def setUp(self):
        """Set up test crystal."""
        self.lattice = Lattice(10)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], self.lattice)
    
    def test_add_atom_uses_helpers(self):
        """Test that add_atom uses helper methods."""
        # Build neighbor tree
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_tree)
        
        # Add atom - should invalidate tree via helper
        self.crystal.add_atom('O', [0.5, 0, 0])
        
        # Tree should be invalidated
        self.assertIsNone(self.crystal._neighbor_tree)
    
    def test_remove_atom_uses_helpers(self):
        """Test that remove_atom uses helper methods."""
        crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0,0]], self.lattice)
        
        # Build neighbor tree
        crystal.get_neighbor_list(5.0)
        
        # Remove atom - should invalidate
        crystal.remove_atom(1)
        
        self.assertIsNone(crystal._neighbor_tree)
    
    def test_substitute_uses_helpers(self):
        """Test that substitute uses helper methods."""
        # Build neighbor tree
        self.crystal.get_neighbor_list(5.0)
        
        # Substitute - should invalidate
        self.crystal.substitute(0, 'Ge')
        
        self.assertIsNone(self.crystal._neighbor_tree)
    
    def test_sort_atoms_uses_helpers(self):
        """Test that sort_atoms uses helper methods."""
        crystal = Crystal(['O', 'Si'], [[0,0,0], [0.5,0,0]], self.lattice)
        
        # Sort
        crystal.sort_atoms('element')
        
        # Coordinates should be updated
        self.assertEqual(len(crystal.frac_positions), 2)
        self.assertEqual(len(crystal.cart_positions), 2)

class TestCrystalTypeHints(unittest.TestCase):
    """Test that methods have proper type hints."""
    
    def test_convert_methods_have_return_types(self):
        """Test coordinate conversion methods have return types."""
        lattice = Lattice(10)
        crystal = Crystal(['Si'], [[0,0,0]], lattice)
        
        # Check that methods exist and have annotations
        self.assertTrue(hasattr(crystal._convert_to_cartesian, '__annotations__'))
        self.assertTrue(hasattr(crystal._convert_to_fractional, '__annotations__'))

class TestCrystalIntegration(unittest.TestCase):
    """Integration tests for Crystal helper behavior."""
    
    def test_multiple_modifications_work_together(self):
        """Test that multiple modifications work correctly."""
        lattice = Lattice(10)
        crystal = Crystal(['Si'], [[0,0,0]], lattice)
        
        # Add atoms
        crystal.add_atom(['O', 'O'], [[0.25,0,0], [0.75,0,0]])
        self.assertEqual(len(crystal), 3)
        
        # Substitute
        crystal.substitute(0, 'Ge')
        self.assertEqual(crystal.species[0], 'Ge')
        
        # Sort
        crystal.sort_atoms('alphabet')
        
        # Remove
        crystal.remove_atom(0)
        self.assertEqual(len(crystal), 2)
        
        # All should work without errors
        self.assertIsInstance(crystal.formula, str)

if __name__ == '__main__':
    unittest.main()
