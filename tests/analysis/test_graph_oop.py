"""Tests for OOP graph API (MoleculeGraph and CrystalGraph)."""
import unittest
import numpy as np

from matsimpy.core import Molecule, Crystal, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule
from matsimpy.analysis.graph import (
    MoleculeGraph,
    CrystalGraph,
    create_structure_graph,
    StructureGraph,
    get_shortest_path,
)


class TestMoleculeGraph(unittest.TestCase):
    def setUp(self):
        self.mol = make_simple_molecule()
        self.graph = MoleculeGraph(self.mol, cutoff=2.0)

    def test_initialization(self):
        self.assertIsInstance(self.graph, MoleculeGraph)
        self.assertIsInstance(self.graph, StructureGraph)
        self.assertEqual(self.graph.cutoff, 2.0)
        self.assertIs(self.graph.structure, self.mol)

    def test_num_nodes(self):
        self.assertEqual(self.graph.num_nodes, 2)

    def test_adjacency_matrix(self):
        adj = self.graph.adjacency_matrix
        self.assertEqual(adj.shape, (2, 2))
        self.assertEqual(adj[0, 1], 1)
        self.assertEqual(adj[1, 0], 1)
        self.assertEqual(adj[0, 0], 0)

    def test_adjacency_matrix_cached(self):
        adj1 = self.graph.adjacency_matrix
        adj2 = self.graph.adjacency_matrix
        self.assertIs(adj1, adj2)

    def test_distance_matrix(self):
        dist = self.graph.distance_matrix
        self.assertEqual(dist.shape, (2, 2))
        self.assertAlmostEqual(dist[0, 1], 1.2)
        self.assertAlmostEqual(dist[1, 0], 1.2)
        self.assertAlmostEqual(dist[0, 0], 0.0)

    def test_edge_list(self):
        edges = self.graph.edge_list
        self.assertEqual(len(edges), 1)
        i, j, dist = edges[0]
        self.assertEqual(i, 0)
        self.assertEqual(j, 1)
        self.assertAlmostEqual(dist, 1.2, places=5)

    def test_num_edges(self):
        self.assertEqual(self.graph.num_edges, 1)

    def test_coordination_numbers(self):
        coord = self.graph.coordination_numbers
        self.assertEqual(coord[0], 1)
        self.assertEqual(coord[1], 1)

    def test_degree_distribution(self):
        dist = self.graph.degree_distribution
        self.assertEqual(dist[1], 2)

    def test_is_connected(self):
        self.assertTrue(self.graph.is_connected)

    def test_connected_components(self):
        components = self.graph.connected_components
        self.assertEqual(len(components), 1)
        self.assertEqual(sorted(components[0]), [0, 1])

    def test_shortest_path(self):
        path = self.graph.get_shortest_path(0, 1)
        self.assertEqual(path, [0, 1])

    def test_diameter(self):
        self.assertEqual(self.graph.diameter, 1)

    def test_node_features(self):
        features = self.graph.node_features
        self.assertEqual(features.shape, (2, 1))
        self.assertEqual(features[0, 0], 6)
        self.assertEqual(features[1, 0], 8)

    def test_laplacian(self):
        L = self.graph.laplacian
        self.assertEqual(L.shape, (2, 2))
        self.assertTrue(np.allclose(L.sum(axis=1), 0))

    def test_normalized_laplacian(self):
        L_norm = self.graph.get_normalized_laplacian()
        self.assertEqual(L_norm.shape, (2, 2))
        self.assertTrue(np.allclose(np.diag(L_norm), 1.0))

    def test_statistics(self):
        stats = self.graph.statistics
        self.assertEqual(stats['num_nodes'], 2)
        self.assertEqual(stats['num_edges'], 1)
        self.assertTrue(stats['is_connected'])
        self.assertEqual(stats['diameter'], 1)

    def test_repr(self):
        repr_str = repr(self.graph)
        self.assertIn('MoleculeGraph', repr_str)
        self.assertIn('nodes=2', repr_str)
        self.assertIn('edges=1', repr_str)


class TestCrystalGraph(unittest.TestCase):
    def setUp(self):
        self.lattice = Lattice(10)
        self.crystal = make_simple_crystal(self.lattice)
        self.graph = CrystalGraph(self.crystal, cutoff=8.0, use_pbc=True)

    def test_initialization(self):
        self.assertIsInstance(self.graph, CrystalGraph)
        self.assertIsInstance(self.graph, StructureGraph)
        self.assertTrue(self.graph.use_pbc)

    def test_num_nodes(self):
        self.assertEqual(self.graph.num_nodes, 2)
        self.assertTrue(self.graph.use_pbc)

    def test_adjacency_matrix(self):
        adj = self.graph.adjacency_matrix
        self.assertEqual(adj.shape, (2, 2))
        self.assertIsInstance(adj, np.ndarray)

    def test_distance_matrix(self):
        dist = self.graph.distance_matrix
        self.assertEqual(dist.shape, (2, 2))
        self.assertEqual(dist[0, 0], 0.0)

    def test_distance_matrix_not_limited_by_neighbor_cutoff(self):
        crystal = Crystal(
            ['H', 'H'],
            [[0, 0, 0], [0.5, 0, 0]],
            Lattice.cubic(100),
        )
        graph = CrystalGraph(crystal, cutoff=1.0, use_pbc=True)
        dist = graph.distance_matrix
        self.assertTrue(np.isfinite(dist[0, 1]))
        self.assertAlmostEqual(dist[0, 1], 50.0)

    def test_coordination_numbers(self):
        coord = self.graph.coordination_numbers
        self.assertIn(0, coord)
        self.assertIn(1, coord)
        self.assertIsInstance(coord[0], int)

    def test_statistics(self):
        stats = self.graph.statistics
        self.assertEqual(stats['num_nodes'], 2)
        self.assertIsInstance(stats['num_edges'], int)

    def test_pbc_false(self):
        graph_no_pbc = CrystalGraph(self.crystal, cutoff=8.0, use_pbc=False)
        self.assertFalse(graph_no_pbc.use_pbc)
        adj = graph_no_pbc.adjacency_matrix
        self.assertEqual(adj.shape, (2, 2))


class TestFactoryFunction(unittest.TestCase):
    def test_create_molecule_graph(self):
        mol = make_simple_molecule()
        graph = create_structure_graph(mol, cutoff=2.0)
        self.assertIsInstance(graph, MoleculeGraph)

    def test_create_crystal_graph(self):
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        graph = create_structure_graph(crystal, cutoff=5.0)
        self.assertIsInstance(graph, CrystalGraph)
        self.assertTrue(graph.use_pbc)

    def test_create_crystal_graph_no_pbc(self):
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        graph = create_structure_graph(crystal, cutoff=5.0, use_pbc=False)
        self.assertIsInstance(graph, CrystalGraph)
        self.assertFalse(graph.use_pbc)

    def test_invalid_structure_raises_error(self):
        with self.assertRaises(TypeError):
            create_structure_graph("invalid", cutoff=3.0)


class TestOOPvsFunctionalEquivalence(unittest.TestCase):
    def setUp(self):
        self.mol = Molecule(['C', 'O', 'H'], [[0, 0, 0], [1.2, 0, 0], [2.5, 0, 0]])
        self.cutoff = 1.5

    def test_adjacency_equivalence(self):
        from matsimpy.analysis.graph import get_adjacency_matrix
        graph = MoleculeGraph(self.mol, self.cutoff)
        adj_oop = graph.adjacency_matrix
        adj_func = get_adjacency_matrix(self.mol, self.cutoff)
        self.assertTrue(np.array_equal(adj_oop, adj_func))

    def test_coordination_equivalence(self):
        from matsimpy.analysis.graph import get_coordination_numbers
        graph = MoleculeGraph(self.mol, self.cutoff)
        coord_oop = graph.coordination_numbers
        coord_func = get_coordination_numbers(self.mol, self.cutoff)
        self.assertEqual(coord_oop, coord_func)

    def test_statistics_equivalence(self):
        from matsimpy.analysis.graph import get_graph_statistics
        graph = MoleculeGraph(self.mol, self.cutoff)
        stats_oop = graph.statistics
        stats_func = get_graph_statistics(self.mol, self.cutoff)
        self.assertEqual(stats_oop, stats_func)

    def test_shortest_path_equivalence(self):
        graph = MoleculeGraph(self.mol, self.cutoff)
        path_oop = graph.get_shortest_path(0, 2)
        path_func = get_shortest_path(self.mol, 0, 2, self.cutoff)
        self.assertEqual(path_oop, path_func)


class TestGraphEdgeCases(unittest.TestCase):
    def test_single_atom_graph(self):
        mol = Molecule(['C'], [[0, 0, 0]])
        graph = MoleculeGraph(mol, cutoff=2.0)
        self.assertEqual(graph.num_nodes, 1)
        self.assertEqual(graph.num_edges, 0)
        self.assertTrue(graph.is_connected)
        self.assertEqual(graph.diameter, 0)

    def test_type_validation_molecule_graph(self):
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        with self.assertRaises(TypeError):
            MoleculeGraph(crystal, cutoff=3.0)

    def test_type_validation_crystal_graph(self):
        mol = Molecule(['C'], [[0, 0, 0]])
        with self.assertRaises(TypeError):
            CrystalGraph(mol, cutoff=3.0)


if __name__ == '__main__':
    unittest.main()
