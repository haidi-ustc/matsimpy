"""Tests for Molecule enhancements: neighbor list optimization and chemical checks."""
import os
import sys
import unittest
import numpy as np
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Molecule


class TestMoleculeAddAtomChemicalChecks(unittest.TestCase):
    """Test chemical reasonableness checks in add_atom."""
    
    def test_add_atom_reasonable_distance_no_warning(self):
        """Test that reasonable distances don't trigger warning."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol.add_atom('O', [1.2, 0, 0])  # Typical C-O bond ~1.2 Å
            
            # Should not warn
            self.assertEqual(len(w), 0)
    
    def test_add_atom_small_distance_warns(self):
        """Test that very small distances trigger warning."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol.add_atom('O', [0.3, 0, 0])  # 0.3 Å is too close
            
            # Should warn
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, UserWarning))
            self.assertIn("small interatomic distance", str(w[0].message).lower())
            self.assertIn("0.3", str(w[0].message))
    
    def test_add_atom_at_boundary_warns(self):
        """Test warning at 0.5 Å boundary."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        # Just below threshold - should warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol.add_atom('O', [0.4, 0, 0])
            self.assertEqual(len(w), 1)
        
        # Just above threshold - should not warn
        mol2 = Molecule(['C'], [[0, 0, 0]])
        with warnings.catch_warnings(record=True) as w2:
            warnings.simplefilter("always")
            mol2.add_atom('O', [0.6, 0, 0])
            self.assertEqual(len(w2), 0)
    
    def test_add_multiple_atoms_checks_all(self):
        """Test that all new atoms are checked for distances."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Add two atoms, one too close
            mol.add_atom(['O', 'H'], [[0.3, 0, 0], [2.0, 0, 0]])
            
            # Should warn about the close one
            self.assertGreater(len(w), 0)
            self.assertIn("0.3", str(w[0].message))
    
    def test_add_atom_to_empty_molecule_no_warning(self):
        """Test that first atom doesn't trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol = Molecule(['C'], [[0, 0, 0]])
            mol.add_atom('O', [0.3, 0, 0])  # Second atom can be close
            
            # Only one warning (for second atom being close to first)
            self.assertEqual(len(w), 1)
    
    def test_warning_message_content(self):
        """Test that warning message is helpful."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol.add_atom('O', [0.2, 0, 0])
            
            msg = str(w[0].message)
            # Should mention distance
            self.assertIn("0.2", msg)
            # Should mention it's small
            self.assertIn("small", msg.lower())
            # Should suggest possible causes
            self.assertTrue("units" in msg.lower() or "overlapping" in msg.lower())


class TestMoleculeNeighborListOptimization(unittest.TestCase):
    """Test optimized get_all_neighbor_lists method."""
    
    def test_get_all_neighbor_lists_basic(self):
        """Test basic functionality of optimized method."""
        mol = Molecule(['C', 'O', 'H'], [[0, 0, 0], [1.2, 0, 0], [2.5, 0, 0]])
        neighbors = mol.get_all_neighbor_lists(2.0)
        
        # C has O as neighbor (1.2 Å away)
        self.assertIn(1, neighbors[0])
        # O has C and H as neighbors (1.2 and 1.3 Å away)
        self.assertIn(0, neighbors[1])
        # H has O as neighbor (1.3 Å away)
        self.assertIn(1, neighbors[2])
    
    def test_get_all_neighbor_lists_returns_correct_length(self):
        """Test that result has correct length."""
        mol = Molecule(['C', 'O', 'H', 'N'], [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]])
        neighbors = mol.get_all_neighbor_lists(5.0)
        
        self.assertEqual(len(neighbors), 4)
    
    def test_get_all_neighbor_lists_no_self_in_list(self):
        """Test that atoms don't appear in their own neighbor list."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [0.5, 0, 0]])
        neighbors = mol.get_all_neighbor_lists(10.0)  # Large cutoff
        
        # Atom 0 should not be in its own list
        self.assertNotIn(0, neighbors[0])
        # Atom 1 should not be in its own list
        self.assertNotIn(1, neighbors[1])
    
    def test_get_all_neighbor_lists_cutoff_validation(self):
        """Test that negative cutoff raises error."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with self.assertRaises(ValueError) as context:
            mol.get_all_neighbor_lists(-1.0)
        
        self.assertIn("negative", str(context.exception).lower())
    
    def test_get_all_neighbor_lists_single_atom(self):
        """Test with single atom (no neighbors possible)."""
        mol = Molecule(['C'], [[0, 0, 0]])
        neighbors = mol.get_all_neighbor_lists(5.0)
        
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0], [])
    
    def test_get_all_neighbor_lists_consistency_with_single(self):
        """Test that results match get_neighbor_list for each atom."""
        mol = Molecule(['C', 'O', 'H', 'N'], 
                      [[0, 0, 0], [1.2, 0, 0], [2.5, 0, 0], [0.5, 0.5, 0]])
        cutoff = 2.0
        
        all_neighbors = mol.get_all_neighbor_lists(cutoff)
        
        for i in range(len(mol)):
            single_neighbors_dict = mol.get_neighbor_list(i, cutoff)
            # Extract neighbor indices from tuples
            single_neighbors = [idx for idx, _ in single_neighbors_dict[i]]
            self.assertEqual(sorted(all_neighbors[i]), sorted(single_neighbors))
    
    def test_get_all_neighbor_lists_large_cutoff(self):
        """Test with large cutoff (all atoms are neighbors)."""
        mol = Molecule(['C', 'O', 'H'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        neighbors = mol.get_all_neighbor_lists(100.0)
        
        # Each atom should have 2 neighbors
        self.assertEqual(len(neighbors[0]), 2)
        self.assertEqual(len(neighbors[1]), 2)
        self.assertEqual(len(neighbors[2]), 2)
    
    def test_get_all_neighbor_lists_performance(self):
        """Test that vectorized version works with larger molecules."""
        import time
        
        # Create a moderately sized molecule
        n = 50
        positions = [[i * 0.5, 0, 0] for i in range(n)]
        species = ['C'] * n
        mol = Molecule(species, positions)
        
        # Should complete quickly (< 1 second for 50 atoms)
        start = time.time()
        neighbors = mol.get_all_neighbor_lists(2.0)
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(neighbors), n)


class TestMoleculeNeighborListSingle(unittest.TestCase):
    """Test get_neighbor_list improvements."""
    
    def test_get_neighbor_list_index_validation(self):
        """Test that invalid index raises error."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        with self.assertRaises(IndexError):
            mol.get_neighbor_list(5, 2.0)
        
        with self.assertRaises(IndexError):
            mol.get_neighbor_list(-3, 2.0)
    
    def test_get_neighbor_list_error_message(self):
        """Test that error message is helpful."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        with self.assertRaises(IndexError) as context:
            mol.get_neighbor_list(10, 2.0)
        
        msg = str(context.exception)
        self.assertIn("10", msg)
        self.assertIn("out of range", msg.lower())


class TestMoleculeIntegration(unittest.TestCase):
    """Integration tests combining multiple enhancements."""
    
    def test_add_atom_then_get_neighbors(self):
        """Test that added atoms are included in neighbor lists."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        # Add atom with reasonable distance
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol.add_atom('O', [1.2, 0, 0])
            self.assertEqual(len(w), 0)  # No warning
        
        # Check neighbors
        neighbors = mol.get_all_neighbor_lists(2.0)
        self.assertEqual(len(neighbors), 2)
        self.assertIn(1, neighbors[0])
        self.assertIn(0, neighbors[1])
    
    def test_add_close_atom_and_verify(self):
        """Test adding close atom with warning, then verify distance."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mol.add_atom('O', [0.3, 0, 0])
            self.assertEqual(len(w), 1)
        
        # Verify actual distance
        from scipy.spatial.distance import cdist
        dist = cdist([mol.positions[0]], [mol.positions[1]])[0][0]
        self.assertAlmostEqual(dist, 0.3, places=5)
    
    def test_multiple_operations_consistency(self):
        """Test consistency across multiple operations."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        # Get initial neighbors
        neighbors1 = mol.get_all_neighbor_lists(2.0)
        
        # Add atom
        mol.add_atom('H', [2.5, 0, 0])
        
        # Get new neighbors
        neighbors2 = mol.get_all_neighbor_lists(2.0)
        
        # Should have one more list
        self.assertEqual(len(neighbors2), len(neighbors1) + 1)


class TestMoleculeDocstringsAndTypes(unittest.TestCase):
    """Test that methods have proper type hints and documentation."""
    
    def test_get_center_of_mass_has_return_type(self):
        """Test that method has return type annotation."""
        mol = Molecule(['C'], [[0, 0, 0]])
        method = mol.get_center_of_mass
        
        # Check annotations exist
        self.assertIn('return', method.__annotations__)
    
    def test_methods_have_docstrings(self):
        """Test that key methods have docstrings."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        methods = [
            'get_center_of_mass',
            'translate',
            'rotate',
            'add_atom',
            'get_neighbor_list',
            'get_all_neighbor_lists'
        ]
        
        for method_name in methods:
            method = getattr(mol, method_name)
            self.assertIsNotNone(method.__doc__, 
                               f"{method_name} should have docstring")
            self.assertGreater(len(method.__doc__), 20,
                             f"{method_name} docstring should be substantial")


if __name__ == '__main__':
    unittest.main()

