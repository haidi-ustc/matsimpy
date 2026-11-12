"""Tests for Molecule enhancements: neighbor list optimization and chemical checks."""
import unittest

from matsimpy.core import Molecule


class TestMoleculeNeighborListOptimization(unittest.TestCase):
    """Test optimized get_all_neighbor_lists method."""
    
    
    
    
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
            single_neighbors_dict = mol.get_neighbor_list(cutoff=cutoff, atom_index=i)
            # Extract neighbor indices from tuples
            single_neighbors = [idx for idx, _ in single_neighbors_dict[i]]
            self.assertEqual(sorted(all_neighbors[i]), sorted(single_neighbors))
    
    

class TestMoleculeNeighborListSingle(unittest.TestCase):
    """Test get_neighbor_list improvements."""
    
    
    def test_get_neighbor_list_error_message(self):
        """Test that error message is helpful."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        with self.assertRaises(IndexError) as context:
            mol.get_neighbor_list(cutoff=2.0, atom_index=10)
        
        msg = str(context.exception)
        self.assertIn("10", msg)
        self.assertIn("out of range", msg.lower())


if __name__ == '__main__':
    unittest.main()
