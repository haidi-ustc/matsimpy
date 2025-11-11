"""Tests for enhanced graph.py module with molecule and crystal support."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Molecule, Crystal, Lattice
from matsimpy.core.graph import (
    get_adjacency_matrix,
    get_distance_matrix,
    get_edge_list,
    get_coordination_numbers,
    get_degree_distribution,
    is_connected,
    get_connected_components,
    get_shortest_path,
    get_graph_diameter,
    get_node_features,
    get_graph_statistics,
    get_graph_laplacian,
)


class TestAdjacencyMatrix(unittest.TestCase):
    """Test adjacency matrix computation."""
    
    def test_molecule_adjacency_basic(self):
        """Test basic adjacency matrix for molecule."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        adj = get_adjacency_matrix(mol, cutoff=2.0)
        
        self.assertEqual(adj.shape, (2, 2))
        self.assertEqual(adj[0, 1], 1)  # Connected
        self.assertEqual(adj[1, 0], 1)  # Symmetric
        self.assertEqual(adj[0, 0], 0)  # No self-loops
    
    def test_molecule_adjacency_disconnected(self):
        """Test adjacency for disconnected atoms."""
        mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
        adj = get_adjacency_matrix(mol, cutoff=2.0)
        
        self.assertEqual(adj[0, 1], 0)  # Not connected
        self.assertEqual(adj[1, 0], 0)
    
    def test_crystal_adjacency(self):
        """Test adjacency matrix for crystal."""
        lat = Lattice(10)
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], lat)
        adj = get_adjacency_matrix(crystal, cutoff=5.0)
        
        self.assertEqual(adj.shape, (2, 2))
        self.assertEqual(adj[0, 0], 0)  # No self-loops


class TestDistanceMatrix(unittest.TestCase):
    """Test distance matrix computation."""
    
    def test_molecule_distance_matrix(self):
        """Test distance matrix for molecule."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        dist = get_distance_matrix(mol)
        
        self.assertEqual(dist.shape, (2, 2))
        self.assertAlmostEqual(dist[0, 1], 1.2)
        self.assertAlmostEqual(dist[1, 0], 1.2)
        self.assertAlmostEqual(dist[0, 0], 0.0)
    
    def test_distance_matrix_symmetric(self):
        """Test that distance matrix is symmetric."""
        mol = Molecule(['C', 'O', 'H'], [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        dist = get_distance_matrix(mol)
        
        self.assertTrue(np.allclose(dist, dist.T))


class TestEdgeList(unittest.TestCase):
    """Test edge list generation."""
    
    def test_edge_list_basic(self):
        """Test basic edge list."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        edges = get_edge_list(mol, cutoff=2.0)
        
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0], (0, 1))
    
    def test_edge_list_with_distances(self):
        """Test edge list with distances."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        edges = get_edge_list(mol, cutoff=2.0, include_distances=True)
        
        self.assertEqual(len(edges), 1)
        i, j, dist = edges[0]
        self.assertEqual(i, 0)
        self.assertEqual(j, 1)
        self.assertAlmostEqual(dist, 1.2, places=5)
    
    def test_edge_list_multiple_edges(self):
        """Test edge list with multiple edges."""
        mol = Molecule(['C', 'C', 'C'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        edges = get_edge_list(mol, cutoff=1.5)
        
        self.assertEqual(len(edges), 2)  # (0,1) and (1,2)


class TestCoordinationNumbers(unittest.TestCase):
    """Test coordination number computation."""
    
    def test_coordination_single_bond(self):
        """Test coordination for simple bond."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        coord = get_coordination_numbers(mol, cutoff=2.0)
        
        self.assertEqual(coord[0], 1)
        self.assertEqual(coord[1], 1)
    
    def test_coordination_multiple_neighbors(self):
        """Test coordination with multiple neighbors."""
        mol = Molecule(['C', 'H', 'H', 'H', 'H'], 
                      [[0, 0, 0], [2, 0, 0], [-2, 0, 0], [0, 2, 0], [0, -2, 0]])
        coord = get_coordination_numbers(mol, cutoff=2.5)
        
        self.assertEqual(coord[0], 4)  # C has 4 neighbors
        self.assertEqual(coord[1], 1)  # Each H has 1 neighbor (only C)


class TestDegreeDistribution(unittest.TestCase):
    """Test degree distribution."""
    
    def test_degree_distribution_basic(self):
        """Test basic degree distribution."""
        mol = Molecule(['C', 'H', 'H'], [[0, 0, 0], [1, 0, 0], [-1, 0, 0]])
        dist = get_degree_distribution(mol, cutoff=1.5)
        
        # One atom with degree 2, two atoms with degree 1
        self.assertEqual(dist[2], 1)
        self.assertEqual(dist[1], 2)


class TestConnectivity(unittest.TestCase):
    """Test graph connectivity functions."""
    
    def test_is_connected_true(self):
        """Test connected graph."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        self.assertTrue(is_connected(mol, cutoff=2.0))
    
    def test_is_connected_false(self):
        """Test disconnected graph."""
        mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
        self.assertFalse(is_connected(mol, cutoff=2.0))
    
    def test_is_connected_single_atom(self):
        """Test single atom is considered connected."""
        mol = Molecule(['C'], [[0, 0, 0]])
        self.assertTrue(is_connected(mol, cutoff=2.0))
    
    def test_connected_components_single(self):
        """Test connected components for connected graph."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        components = get_connected_components(mol, cutoff=2.0)
        
        self.assertEqual(len(components), 1)
        self.assertEqual(sorted(components[0]), [0, 1])
    
    def test_connected_components_multiple(self):
        """Test connected components for disconnected graph."""
        mol = Molecule(['C', 'O', 'N', 'H'], 
                      [[0, 0, 0], [1.2, 0, 0], [10, 0, 0], [11, 0, 0]])
        components = get_connected_components(mol, cutoff=2.0)
        
        self.assertEqual(len(components), 2)


class TestShortestPath(unittest.TestCase):
    """Test shortest path finding."""
    
    def test_shortest_path_direct(self):
        """Test shortest path for directly connected atoms."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        path = get_shortest_path(mol, 0, 1, cutoff=2.0)
        
        self.assertEqual(path, [0, 1])
    
    def test_shortest_path_indirect(self):
        """Test shortest path through intermediate atoms."""
        mol = Molecule(['C', 'C', 'C'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        path = get_shortest_path(mol, 0, 2, cutoff=1.5)
        
        self.assertEqual(path, [0, 1, 2])
    
    def test_shortest_path_no_path(self):
        """Test when no path exists."""
        mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
        path = get_shortest_path(mol, 0, 1, cutoff=2.0)
        
        self.assertIsNone(path)
    
    def test_shortest_path_same_atom(self):
        """Test path to same atom."""
        mol = Molecule(['C'], [[0, 0, 0]])
        path = get_shortest_path(mol, 0, 0, cutoff=2.0)
        
        self.assertEqual(path, [0])
    
    def test_shortest_path_index_validation(self):
        """Test index validation."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        with self.assertRaises(IndexError):
            get_shortest_path(mol, 0, 10, cutoff=2.0)


class TestGraphDiameter(unittest.TestCase):
    """Test graph diameter computation."""
    
    def test_diameter_linear_molecule(self):
        """Test diameter for linear molecule."""
        mol = Molecule(['C', 'C', 'C'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        diameter = get_graph_diameter(mol, cutoff=1.5)
        
        self.assertEqual(diameter, 2)
    
    def test_diameter_single_atom(self):
        """Test diameter for single atom."""
        mol = Molecule(['C'], [[0, 0, 0]])
        diameter = get_graph_diameter(mol, cutoff=2.0)
        
        self.assertEqual(diameter, 0)
    
    def test_diameter_disconnected(self):
        """Test diameter for disconnected graph."""
        mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
        diameter = get_graph_diameter(mol, cutoff=2.0)
        
        self.assertIsNone(diameter)


class TestNodeFeatures(unittest.TestCase):
    """Test node feature extraction."""
    
    def test_node_features_basic(self):
        """Test basic node features."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        features = get_node_features(mol)
        
        self.assertEqual(features.shape, (2, 1))
        self.assertEqual(features[0, 0], 6)  # Carbon atomic number
        self.assertEqual(features[1, 0], 8)  # Oxygen atomic number


class TestGraphStatistics(unittest.TestCase):
    """Test comprehensive graph statistics."""
    
    def test_statistics_basic(self):
        """Test basic graph statistics."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        stats = get_graph_statistics(mol, cutoff=2.0)
        
        self.assertEqual(stats['num_nodes'], 2)
        self.assertEqual(stats['num_edges'], 1)
        self.assertTrue(stats['is_connected'])
        self.assertEqual(stats['num_components'], 1)
        self.assertEqual(stats['diameter'], 1)
        self.assertAlmostEqual(stats['avg_coordination'], 1.0)
        self.assertEqual(stats['max_coordination'], 1)
        self.assertEqual(stats['min_coordination'], 1)
    
    def test_statistics_complex_molecule(self):
        """Test statistics for complex molecule."""
        mol = Molecule(['C', 'H', 'H', 'H'], 
                      [[0, 0, 0], [2, 0, 0], [-2, 0, 0], [0, 2, 0]])
        stats = get_graph_statistics(mol, cutoff=2.5)
        
        self.assertEqual(stats['num_nodes'], 4)
        self.assertEqual(stats['num_edges'], 3)  # 3 C-H bonds
        self.assertTrue(stats['is_connected'])


class TestGraphLaplacian(unittest.TestCase):
    """Test graph Laplacian computation."""
    
    def test_laplacian_basic(self):
        """Test basic Laplacian."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        L = get_graph_laplacian(mol, cutoff=2.0)
        
        self.assertEqual(L.shape, (2, 2))
        # Laplacian should have zero row sums
        self.assertTrue(np.allclose(L.sum(axis=1), 0))
    
    def test_laplacian_normalized(self):
        """Test normalized Laplacian."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        L = get_graph_laplacian(mol, cutoff=2.0, normalized=True)
        
        self.assertEqual(L.shape, (2, 2))
        # Diagonal should be 1 for normalized Laplacian
        self.assertTrue(np.allclose(np.diag(L), 1.0))


class TestCrystalGraphMethods(unittest.TestCase):
    """Test graph methods with Crystal structures."""
    
    def setUp(self):
        """Set up test crystal."""
        self.lattice = Lattice(10)
        self.crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], self.lattice)
    
    def test_crystal_adjacency(self):
        """Test adjacency matrix for crystal."""
        adj = get_adjacency_matrix(self.crystal, cutoff=5.0)
        self.assertEqual(adj.shape, (2, 2))
    
    def test_crystal_coordination(self):
        """Test coordination numbers for crystal."""
        coord = get_coordination_numbers(self.crystal, cutoff=5.0)
        self.assertIn(0, coord)
        self.assertIn(1, coord)
    
    def test_crystal_statistics(self):
        """Test graph statistics for crystal."""
        stats = get_graph_statistics(self.crystal, cutoff=5.0)
        
        self.assertEqual(stats['num_nodes'], 2)
        self.assertGreaterEqual(stats['num_edges'], 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_single_atom_molecule(self):
        """Test single atom molecule."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        adj = get_adjacency_matrix(mol, cutoff=2.0)
        self.assertEqual(adj.shape, (1, 1))
        
        self.assertTrue(is_connected(mol, cutoff=2.0))
        
        components = get_connected_components(mol, cutoff=2.0)
        self.assertEqual(len(components), 1)
    
    def test_linear_chain(self):
        """Test linear chain of atoms."""
        mol = Molecule(['C'] * 5, [[i, 0, 0] for i in range(5)])
        
        diameter = get_graph_diameter(mol, cutoff=1.5)
        self.assertEqual(diameter, 4)  # Length of chain - 1
        
        path = get_shortest_path(mol, 0, 4, cutoff=1.5)
        self.assertEqual(len(path), 5)  # All atoms in chain


class TestGraphIntegration(unittest.TestCase):
    """Integration tests combining multiple methods."""
    
    def test_molecule_full_workflow(self):
        """Test complete workflow with molecule."""
        mol = Molecule(['C', 'O', 'H'], [[0, 0, 0], [1.2, 0, 0], [2.5, 0, 0]])
        
        # Get adjacency
        adj = get_adjacency_matrix(mol, cutoff=1.5)
        
        # Get edge list
        edges = get_edge_list(mol, cutoff=1.5)
        
        # Get coordination
        coord = get_coordination_numbers(mol, cutoff=1.5)
        
        # Get statistics
        stats = get_graph_statistics(mol, cutoff=1.5)
        
        # Verify consistency
        self.assertEqual(stats['num_nodes'], len(mol))
        self.assertEqual(stats['num_edges'], len(edges))
    
    def test_crystal_full_workflow(self):
        """Test complete workflow with crystal."""
        lat = Lattice(10)
        crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], lat)
        
        adj = get_adjacency_matrix(crystal, cutoff=8.0)
        edges = get_edge_list(crystal, cutoff=8.0)
        coord = get_coordination_numbers(crystal, cutoff=8.0)
        stats = get_graph_statistics(crystal, cutoff=8.0)
        
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['num_nodes'], 2)


if __name__ == '__main__':
    unittest.main()

