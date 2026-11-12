"""Tests for OOP graph API (MoleculeGraph and CrystalGraph)."""
import unittest

from matsimpy.core import Molecule, Crystal, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule
from matsimpy.analysis.graph import (
    MoleculeGraph,
    CrystalGraph,
    create_structure_graph,
)


class TestMoleculeGraph(unittest.TestCase):
    def setUp(self):
        self.mol = make_simple_molecule()
        self.graph = MoleculeGraph(self.mol, cutoff=2.0)

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

    def test_distance_matrix(self):
        dist = self.graph.distance_matrix
        self.assertEqual(dist.shape, (2, 2))
        self.assertEqual(dist[0, 0], 0.0)

    def test_pbc_false(self):
        graph_no_pbc = CrystalGraph(self.crystal, cutoff=8.0, use_pbc=False)
        self.assertFalse(graph_no_pbc.use_pbc)
        adj = graph_no_pbc.adjacency_matrix
        self.assertEqual(adj.shape, (2, 2))


class TestFactoryFunction(unittest.TestCase):

    def test_create_crystal_graph(self):
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        graph = create_structure_graph(crystal, cutoff=5.0)
        self.assertIsInstance(graph, CrystalGraph)
        self.assertTrue(graph.use_pbc)

    def test_invalid_structure_raises_error(self):
        with self.assertRaises(TypeError):
            create_structure_graph("invalid", cutoff=3.0)


class TestGraphEdgeCases(unittest.TestCase):

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
