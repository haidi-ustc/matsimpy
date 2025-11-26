"""Tests for OOP graph API (MoleculeGraph and CrystalGraph)."""
import unittest
import numpy as np

from matsimpy.core import Molecule, Crystal, Lattice
from matsimpy.core.graph import (
    MoleculeGraph,
    CrystalGraph,
    create_structure_graph,
    StructureGraph,
)

class TestMoleculeGraph(unittest.TestCase):
    """Test MoleculeGraph class."""
    
    def setUp(self):
        """Set up test molecules."""
        self.mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        self.graph = MoleculeGraph(self.mol, cutoff=2.0)
    
    def test_initialization(self):
        """Test graph initialization."""
        self.assertIsInstance(self.graph, MoleculeGraph)
        self.assertIsInstance(self.graph, StructureGraph)
        self.assertEqual(self.graph.cutoff, 2.0)
        self.assertIs(self.graph.structure, self.mol)
    
    def test_num_nodes(self):
        """Test num_nodes property."""
        self.assertEqual(self.graph.num_nodes, 2)
    
    def test_adjacency_matrix(self):
        """Test adjacency matrix."""
        adj = self.graph.adjacency_matrix
        
        self.assertEqual(adj.shape, (2, 2))
        self.assertEqual(adj[0, 1], 1)
        self.assertEqual(adj[1, 0], 1)
        self.assertEqual(adj[0, 0], 0)
    
    def test_adjacency_matrix_cached(self):
        """Test that adjacency matrix is cached."""
        adj1 = self.graph.adjacency_matrix
        adj2 = self.graph.adjacency_matrix
        
        self.assertIs(adj1, adj2)  # Same object (cached)
    
    def test_distance_matrix(self):
        """Test distance matrix."""
        dist = self.graph.distance_matrix
        
        self.assertEqual(dist.shape, (2, 2))
        self.assertAlmostEqual(dist[0, 1], 1.2)
        self.assertAlmostEqual(dist[1, 0], 1.2)
        self.assertAlmostEqual(dist[0, 0], 0.0)
    
    def test_edge_list(self):
        """Test edge list."""
        edges = self.graph.edge_list
        
        self.assertEqual(len(edges), 1)
        i, j, dist = edges[0]
        self.assertEqual(i, 0)
        self.assertEqual(j, 1)
        self.assertAlmostEqual(dist, 1.2, places=5)
    
    def test_num_edges(self):
        """Test num_edges property."""
        self.assertEqual(self.graph.num_edges, 1)
    
    def test_coordination_numbers(self):
        """Test coordination numbers."""
        coord = self.graph.coordination_numbers
        
        self.assertEqual(coord[0], 1)
        self.assertEqual(coord[1], 1)
    
    def test_degree_distribution(self):
        """Test degree distribution."""
        dist = self.graph.degree_distribution
        
        self.assertEqual(dist[1], 2)  # Two atoms with degree 1
    
    def test_is_connected(self):
        """Test connectivity check."""
        self.assertTrue(self.graph.is_connected)
    
    def test_connected_components(self):
        """Test connected components."""
        components = self.graph.connected_components
        
        self.assertEqual(len(components), 1)
        self.assertEqual(sorted(components[0]), [0, 1])
    
    def test_shortest_path(self):
        """Test shortest path."""
        path = self.graph.get_shortest_path(0, 1)
        
        self.assertEqual(path, [0, 1])
    
    def test_diameter(self):
        """Test graph diameter."""
        self.assertEqual(self.graph.diameter, 1)
    
    def test_node_features(self):
        """Test node features."""
        features = self.graph.node_features
        
        self.assertEqual(features.shape, (2, 1))
        self.assertEqual(features[0, 0], 6)  # Carbon
        self.assertEqual(features[1, 0], 8)  # Oxygen
    
    def test_laplacian(self):
        """Test Laplacian matrix."""
        L = self.graph.laplacian
        
        self.assertEqual(L.shape, (2, 2))
        # Laplacian should have zero row sums
        self.assertTrue(np.allclose(L.sum(axis=1), 0))
    
    def test_normalized_laplacian(self):
        """Test normalized Laplacian."""
        L_norm = self.graph.get_normalized_laplacian()
        
        self.assertEqual(L_norm.shape, (2, 2))
        self.assertTrue(np.allclose(np.diag(L_norm), 1.0))
    
    def test_statistics(self):
        """Test statistics property."""
        stats = self.graph.statistics
        
        self.assertEqual(stats['num_nodes'], 2)
        self.assertEqual(stats['num_edges'], 1)
        self.assertTrue(stats['is_connected'])
        self.assertEqual(stats['diameter'], 1)
    
    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.graph)
        
        self.assertIn('MoleculeGraph', repr_str)
        self.assertIn('nodes=2', repr_str)
        self.assertIn('edges=1', repr_str)

class TestCrystalGraph(unittest.TestCase):
    """Test CrystalGraph class."""
    
    def setUp(self):
        """Set up test crystal."""
        self.lattice = Lattice(10)
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], self.lattice)
        self.graph = CrystalGraph(self.crystal, cutoff=8.0, use_pbc=True)
    
    def test_initialization(self):
        """Test graph initialization."""
        self.assertIsInstance(self.graph, CrystalGraph)
        self.assertIsInstance(self.graph, StructureGraph)
        self.assertTrue(self.graph.use_pbc)
    
    def test_num_nodes(self):
        """Test num_nodes property."""
        self.assertEqual(self.graph.num_nodes, 2)
    
    def test_adjacency_matrix(self):
        """Test adjacency matrix with PBC."""
        adj = self.graph.adjacency_matrix
        
        self.assertEqual(adj.shape, (2, 2))
        self.assertIsInstance(adj, np.ndarray)
    
    def test_distance_matrix(self):
        """Test distance matrix with PBC."""
        dist = self.graph.distance_matrix
        
        self.assertEqual(dist.shape, (2, 2))
        self.assertEqual(dist[0, 0], 0.0)
    
    def test_coordination_numbers(self):
        """Test coordination numbers for crystal."""
        coord = self.graph.coordination_numbers
        
        self.assertIn(0, coord)
        self.assertIn(1, coord)
        self.assertIsInstance(coord[0], int)
    
    def test_statistics(self):
        """Test statistics for crystal."""
        stats = self.graph.statistics
        
        self.assertEqual(stats['num_nodes'], 2)
        self.assertIsInstance(stats['num_edges'], int)
    
    def test_pbc_false(self):
        """Test crystal graph without PBC."""
        graph_no_pbc = CrystalGraph(self.crystal, cutoff=8.0, use_pbc=False)
        
        self.assertFalse(graph_no_pbc.use_pbc)
        adj = graph_no_pbc.adjacency_matrix
        self.assertEqual(adj.shape, (2, 2))

class TestFactoryFunction(unittest.TestCase):
    """Test create_structure_graph factory function."""
    
    def test_create_molecule_graph(self):
        """Test creating MoleculeGraph via factory."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        graph = create_structure_graph(mol, cutoff=2.0)
        
        self.assertIsInstance(graph, MoleculeGraph)
    
    def test_create_crystal_graph(self):
        """Test creating CrystalGraph via factory."""
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        graph = create_structure_graph(crystal, cutoff=5.0)
        
        self.assertIsInstance(graph, CrystalGraph)
        self.assertTrue(graph.use_pbc)  # Default
    
    def test_create_crystal_graph_no_pbc(self):
        """Test creating CrystalGraph without PBC via factory."""
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        graph = create_structure_graph(crystal, cutoff=5.0, use_pbc=False)
        
        self.assertIsInstance(graph, CrystalGraph)
        self.assertFalse(graph.use_pbc)
    
    def test_invalid_structure_raises_error(self):
        """Test that invalid structure raises error."""
        with self.assertRaises(TypeError):
            create_structure_graph("invalid", cutoff=3.0)

class TestBackwardCompatibility(unittest.TestCase):
    """Test that functional API still works (backward compatibility)."""
    
    def test_get_adjacency_matrix_molecule(self):
        """Test functional get_adjacency_matrix."""
        from matsimpy.core.graph import get_adjacency_matrix
        
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        adj = get_adjacency_matrix(mol, cutoff=2.0)
        
        self.assertEqual(adj.shape, (2, 2))
        self.assertEqual(adj[0, 1], 1)
    
    def test_get_coordination_numbers_functional(self):
        """Test functional get_coordination_numbers."""
        from matsimpy.core.graph import get_coordination_numbers
        
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        coord = get_coordination_numbers(mol, cutoff=2.0)
        
        self.assertEqual(coord[0], 1)
        self.assertEqual(coord[1], 1)
    
    def test_is_connected_functional(self):
        """Test functional is_connected."""
        from matsimpy.core.graph import is_connected
        
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        self.assertTrue(is_connected(mol, cutoff=2.0))
    
    def test_get_graph_statistics_functional(self):
        """Test functional get_graph_statistics."""
        from matsimpy.core.graph import get_graph_statistics
        
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        stats = get_graph_statistics(mol, cutoff=2.0)
        
        self.assertEqual(stats['num_nodes'], 2)
        self.assertEqual(stats['num_edges'], 1)

class TestOOPvsFunctionalEquivalence(unittest.TestCase):
    """Test that OOP and functional APIs give same results."""
    
    def setUp(self):
        """Set up test structure."""
        self.mol = Molecule(['C', 'O', 'H'], [[0, 0, 0], [1.2, 0, 0], [2.5, 0, 0]])
        self.cutoff = 1.5
    
    def test_adjacency_equivalence(self):
        """Test adjacency matrix equivalence."""
        from matsimpy.core.graph import get_adjacency_matrix
        
        # OOP API
        graph = MoleculeGraph(self.mol, self.cutoff)
        adj_oop = graph.adjacency_matrix
        
        # Functional API
        adj_func = get_adjacency_matrix(self.mol, self.cutoff)
        
        self.assertTrue(np.array_equal(adj_oop, adj_func))
    
    def test_coordination_equivalence(self):
        """Test coordination numbers equivalence."""
        from matsimpy.core.graph import get_coordination_numbers
        
        graph = MoleculeGraph(self.mol, self.cutoff)
        coord_oop = graph.coordination_numbers
        coord_func = get_coordination_numbers(self.mol, self.cutoff)
        
        self.assertEqual(coord_oop, coord_func)
    
    def test_statistics_equivalence(self):
        """Test statistics equivalence."""
        from matsimpy.core.graph import get_graph_statistics
        
        graph = MoleculeGraph(self.mol, self.cutoff)
        stats_oop = graph.statistics
        stats_func = get_graph_statistics(self.mol, self.cutoff)
        
        self.assertEqual(stats_oop, stats_func)

class TestGraphComplexMolecule(unittest.TestCase):
    """Test with complex molecules."""
    
    def test_linear_chain(self):
        """Test linear chain molecule."""
        mol = Molecule(['C'] * 5, [[i, 0, 0] for i in range(5)])
        graph = MoleculeGraph(mol, cutoff=1.5)
        
        self.assertEqual(graph.num_nodes, 5)
        self.assertEqual(graph.num_edges, 4)
        self.assertTrue(graph.is_connected)
        self.assertEqual(graph.diameter, 4)
    
    def test_disconnected_molecules(self):
        """Test disconnected molecules."""
        mol = Molecule(['C', 'O', 'N', 'H'], 
                      [[0, 0, 0], [1.2, 0, 0], [10, 0, 0], [11, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=2.0)
        
        self.assertFalse(graph.is_connected)
        components = graph.connected_components
        self.assertEqual(len(components), 2)
    
    def test_star_topology(self):
        """Test star-shaped molecule."""
        mol = Molecule(['C', 'H', 'H', 'H', 'H'], 
                      [[0, 0, 0], [2, 0, 0], [-2, 0, 0], [0, 2, 0], [0, -2, 0]])
        graph = MoleculeGraph(mol, cutoff=2.5)
        
        coord = graph.coordination_numbers
        self.assertEqual(coord[0], 4)  # Center C
        self.assertEqual(coord[1], 1)  # Each H
        
        self.assertEqual(graph.diameter, 2)  # H to opposite H

class TestGraphCrystal(unittest.TestCase):
    """Test with crystal structures."""
    
    def test_simple_crystal(self):
        """Test simple crystal."""
        lat = Lattice(10)
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], lat)
        graph = CrystalGraph(crystal, cutoff=5.0, use_pbc=True)
        
        self.assertEqual(graph.num_nodes, 2)
        self.assertGreaterEqual(graph.num_edges, 0)
    
    def test_crystal_without_pbc(self):
        """Test crystal graph without PBC."""
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        graph = CrystalGraph(crystal, cutoff=5.0, use_pbc=False)
        
        self.assertEqual(graph.num_nodes, 1)
        self.assertEqual(graph.num_edges, 0)

class TestGraphMethods(unittest.TestCase):
    """Test specific graph methods."""
    
    def test_shortest_path_found(self):
        """Test shortest path when path exists."""
        mol = Molecule(['C', 'C', 'C'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=1.5)
        
        path = graph.get_shortest_path(0, 2)
        self.assertEqual(path, [0, 1, 2])
    
    def test_shortest_path_not_found(self):
        """Test shortest path when no path exists."""
        mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=2.0)
        
        path = graph.get_shortest_path(0, 1)
        self.assertIsNone(path)
    
    def test_shortest_path_same_atom(self):
        """Test shortest path to same atom."""
        mol = Molecule(['C'], [[0, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=2.0)
        
        path = graph.get_shortest_path(0, 0)
        self.assertEqual(path, [0])
    
    def test_shortest_path_invalid_index(self):
        """Test shortest path with invalid indices."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=2.0)
        
        with self.assertRaises(IndexError):
            graph.get_shortest_path(0, 10)

class TestGraphEdgeCases(unittest.TestCase):
    """Test edge cases."""
    
    def test_single_atom_graph(self):
        """Test graph with single atom."""
        mol = Molecule(['C'], [[0, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=2.0)
        
        self.assertEqual(graph.num_nodes, 1)
        self.assertEqual(graph.num_edges, 0)
        self.assertTrue(graph.is_connected)
        self.assertEqual(graph.diameter, 0)
    
    def test_type_validation_molecule_graph(self):
        """Test that MoleculeGraph validates input type."""
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        
        with self.assertRaises(TypeError):
            MoleculeGraph(crystal, cutoff=3.0)
    
    def test_type_validation_crystal_graph(self):
        """Test that CrystalGraph validates input type."""
        mol = Molecule(['C'], [[0, 0, 0]])
        
        with self.assertRaises(TypeError):
            CrystalGraph(mol, cutoff=3.0)

if __name__ == '__main__':
    unittest.main()

