"""Comprehensive tests for optimization updates."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Lattice, Molecule, Structure

class TestBugFixes(unittest.TestCase):
    """Test bug fixes from optimizations."""
    
    def test_molecule_to_crystal_fix(self):
        """Test that Molecule.to_crystal() works correctly."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        
        molecule = Molecule(species, positions)
        crystal = molecule.to_crystal()
        
        # Should return Crystal, not Structure
        self.assertIsInstance(crystal, Crystal)
        self.assertEqual(len(crystal), 2)
        self.assertIsNotNone(crystal.lattice)
        self.assertEqual(crystal.species, ('C', 'O'))
    
    def test_structure_as_dict_without_lattice(self):
        """Test that as_dict() works for molecules (no lattice)."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        d = molecule.as_dict()
        self.assertIn('species', d)
        self.assertIn('positions', d)
        self.assertNotIn('lattice', d)  # Molecules don't have lattice
    
    def test_structure_from_dict_without_lattice(self):
        """Test that from_dict() works for molecules."""
        d = {
            "@module": "matsimpy.core.molecule",
            "@class": "Molecule",
            "species": ['C', 'O'],
            "positions": [[0, 0, 0], [1.4, 0, 0]]
        }
        molecule = Molecule.from_dict(d)
        self.assertIsInstance(molecule, Molecule)
        self.assertEqual(len(molecule), 2)

class TestPropertyCaching(unittest.TestCase):
    """Test property caching optimizations."""
    
    def test_formula_caching(self):
        """Test that formula is cached."""
        species = ['Si', 'O', 'O']
        positions = [[0, 0, 0], [1.5, 1.5, 1.5], [2.0, 2.0, 2.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        # First call computes
        formula1 = crystal.formula
        self.assertIsNotNone(formula1)

        # Second call should use cache
        formula2 = crystal.formula

        self.assertEqual(formula1, formula2)

    def test_composition_caching(self):
        """Test that composition is cached."""
        species = ['Si', 'O', 'O']
        positions = [[0, 0, 0], [1.5, 1.5, 1.5], [2.0, 2.0, 2.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        # First call computes
        comp1 = crystal.composition

        # Second call should use cache
        comp2 = crystal.composition

        self.assertEqual(comp1, comp2)
    
    def test_cache_invalidation_on_add_atom(self):
        """Test that cache is different on returned object after adding atom."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        # Get formula and composition
        formula1 = crystal.formula
        comp1 = crystal.composition

        # Add atom (returns new object)
        result = crystal.add_atom('O', [0.3, 0.3, 0.3])

        # Formula and composition should be different on the result
        formula2 = result.formula
        comp2 = result.composition

        self.assertNotEqual(formula1, formula2)
        self.assertNotEqual(comp1.formula, comp2.formula)

    def test_cache_invalidation_on_remove_atom(self):
        """Test that cache is different on returned object after removing atom."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1.0, 1.0, 1.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        formula1 = crystal.formula
        result = crystal.remove_atom(0)
        formula2 = result.formula

        self.assertNotEqual(formula1, formula2)

class TestSpeciesImmutability(unittest.TestCase):
    """Test species type consistency."""
    
    def test_species_is_tuple(self):
        """Test that species is always a tuple."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1.0, 1.0, 1.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertIsInstance(crystal.species, tuple)
        self.assertEqual(crystal.species, ('Si', 'O'))
    
    def test_species_immutability_after_add(self):
        """Test that species remains tuple after adding atom (on the returned object)."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        self.assertIsInstance(crystal.species, tuple)
        result = crystal.add_atom('O', [0.3, 0.3, 0.3])
        self.assertIsInstance(result.species, tuple)
        self.assertEqual(result.species, ('Si', 'O'))
        # Original unchanged
        self.assertEqual(crystal.species, ('Si',))

    def test_species_immutability_after_remove(self):
        """Test that species remains tuple after removing atom (on the returned object)."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1.0, 1.0, 1.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        self.assertIsInstance(crystal.species, tuple)
        result = crystal.remove_atom(0)
        self.assertIsInstance(result.species, tuple)
        self.assertEqual(result.species, ('O',))
        # Original unchanged
        self.assertEqual(crystal.species, ('Si', 'O'))

class TestLatticeOptimizations(unittest.TestCase):
    """Test lattice optimizations."""
    
    def test_inverse_matrix_caching(self):
        """Test that inverse matrix is cached."""
        lattice = Lattice.cubic(10.0)
        
        # First call computes
        inv1 = lattice.inv_matrix
        self.assertIsNotNone(lattice._inv_matrix)
        
        # Second call should use cache
        inv2 = lattice.inv_matrix
        
        np.testing.assert_array_almost_equal(inv1, inv2)
        self.assertIs(lattice._inv_matrix, inv2)
    
    def test_inverse_matrix_correctness(self):
        """Test that cached inverse is correct."""
        lattice = Lattice.cubic(10.0)
        inv = lattice.inv_matrix
        matrix = lattice.matrix
        
        # Matrix * inverse should be identity
        result = np.dot(matrix, inv)
        identity = np.eye(3)
        np.testing.assert_array_almost_equal(result, identity)
    
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
    
    def test_neighbor_list_returns_dict(self):
        """Test that neighbor list returns correct format."""
        species = ['Si'] * 8
        positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
                     [1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        neighbors = crystal.get_neighbor_list(2.0)
        
        self.assertIsInstance(neighbors, dict)
        self.assertEqual(len(neighbors), 8)
        
        # Check format: dict[int, List[Tuple[int, float]]]
        for atom_idx, neighbor_list in neighbors.items():
            self.assertIsInstance(atom_idx, int)
            self.assertIsInstance(neighbor_list, list)
            for neighbor_idx, distance in neighbor_list:
                self.assertIsInstance(neighbor_idx, int)
                self.assertIsInstance(distance, float)
                self.assertGreaterEqual(distance, 0)
    
    def test_neighbor_list_larger_structure(self):
        """Test neighbor finding with a larger deterministic structure."""
        # Create larger structure
        size = 100
        species = ['Si'] * size
        positions = [[i % 10, (i // 10) % 10, i // 100] for i in range(size)]
        lattice = Lattice.cubic(20.0)
        crystal = Crystal(species, positions, lattice)
        
        neighbors = crystal.get_neighbor_list(5.0)
        
        self.assertIsInstance(neighbors, dict)
        self.assertEqual(len(neighbors), size)
    
    def test_neighbor_list_caching(self):
        """Test that neighbor tree is cached."""
        species = ['Si'] * 10
        positions = [[i * 0.3, 0, 0] for i in range(10)]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        # First call builds tree
        neighbors1 = crystal.get_neighbor_list(3.0)
        self.assertIsNotNone(crystal._neighbor_cache)
        self.assertEqual(crystal._neighbor_cache.cutoff, 3.0)
        
        # Second call with same cutoff should use cache
        neighbors2 = crystal.get_neighbor_list(3.0)
        
        self.assertIsNotNone(crystal._neighbor_cache)
        self.assertEqual(len(neighbors1), len(neighbors2))
    
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
    
    def test_full_workflow(self):
        """Test complete workflow with all optimizations."""
        # Create structure
        species = ['Si', 'O', 'O']
        positions = [[0, 0, 0], [1.5, 1.5, 1.5], [2.0, 2.0, 2.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        # Test caching
        formula1 = crystal.formula
        formula2 = crystal.formula
        self.assertEqual(formula1, formula2)

        # Test neighbor finding
        neighbors = crystal.get_neighbor_list(5.0)
        self.assertIsInstance(neighbors, dict)

        # Test adding atom (returns new object)
        crystal2 = crystal.add_atom('N', [0.3, 0.3, 0.3])
        formula3 = crystal2.formula
        self.assertNotEqual(formula1, formula3)

        # Test neighbor finding again on the new object (should build tree)
        neighbors2 = crystal2.get_neighbor_list(5.0)
        self.assertEqual(len(neighbors2), 4)
    
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
