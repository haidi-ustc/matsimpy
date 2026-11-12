"""Comprehensive tests for optimization updates."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Lattice, Molecule


class TestLatticeOptimizations(unittest.TestCase):
    """Test lattice optimizations."""
    
    
    
    def test_coordinate_conversion_uses_cached_inverse(self):
        """Test that coordinate conversion uses cached inverse."""
        species = ['Si']
        positions = [[0.5, 0.5, 0.5]]  # Fractional coordinates
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        # Convert to cartesian
        cart = crystal.cart_positions
        
        # Convert back to fractional (should use cached inverse)
        frac = crystal._convert_to_fractional()
        
        np.testing.assert_array_almost_equal(positions, frac, decimal=6)

class TestNeighborFinding(unittest.TestCase):
    """Test optimized neighbor finding."""
    
    
    
    
    def test_neighbor_list_with_pbc(self):
        """Test neighbor finding with periodic boundary conditions."""
        species = ['Si'] * 4
        positions = [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5]]
        lattice = Lattice.cubic(5.0)
        crystal = Crystal(species, positions, lattice)
        
        neighbors = crystal.get_neighbor_list(3.0, use_pbc=True)
        
        # Should find neighbors across periodic boundaries
        self.assertIsInstance(neighbors, dict)
        self.assertGreater(len(neighbors[0]), 0)  # Should have neighbors
    
    def test_neighbor_list_without_pbc(self):
        """Test neighbor finding without periodic boundary conditions."""
        species = ['Si'] * 4
        positions = [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5]]
        lattice = Lattice.cubic(5.0)
        crystal = Crystal(species, positions, lattice)
        
        neighbors = crystal.get_neighbor_list(3.0, use_pbc=False)
        
        self.assertIsInstance(neighbors, dict)

class TestIntegration(unittest.TestCase):
    """Integration tests for all optimizations."""
    
    
    def test_molecule_to_crystal_workflow(self):
        """Test molecule to crystal conversion workflow."""
        # Create molecule
        species = ['C', 'O', 'O']
        positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        molecule = Molecule(species, positions)
        
        # Convert to crystal
        crystal = molecule.to_crystal()
        
        # Verify it's a Crystal
        self.assertIsInstance(crystal, Crystal)
        self.assertIsNotNone(crystal.lattice)
        
        # Test operations work
        formula = crystal.formula
        self.assertIsNotNone(formula)
        
        neighbors = crystal.get_neighbor_list(5.0)
        self.assertIsInstance(neighbors, dict)

if __name__ == '__main__':
    unittest.main()
