"""Tests for the functional graph API on molecules and crystals."""
import numpy as np
import pytest

from matsimpy.core import Molecule, Crystal, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule
from matsimpy.analysis.graph import (
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

# Rows (1,0,0), (10,1,0), (0,0,8): volume 8, the same lattice as the 1 x 1 x 8 box, but
# the shortest image can lie several b-vectors (and ten a-vectors) away.
SHEARED = [[1, 0, 0], [10, 1, 0], [0, 0, 8]]


def test_crystal_adjacency_has_no_self_loops():
    crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice(10))
    adj = get_adjacency_matrix(crystal, cutoff=5.0)
    assert adj.shape == (2, 2)
    assert adj[0, 0] == 0


@pytest.mark.parametrize(
    "matrix, frac, expected",
    [
        ([[100, 0, 0], [0, 100, 0], [0, 0, 100]], [0.99, 0, 0], 1.0),
        # cart = (4, 0.4, 0); the a-shift (-4, 0, 0) gives 0.4
        (SHEARED, [0, 0.4, 0], 0.4),
        # cart = (dx + 0.5, 0.05, 0) with dx + 0.5 an integer, so the nearest image is 0.05 A
        # away; the old {-1, 0, 1} translation grid returned 1.00125 A at -2.5 and 2.0006 A at -3.5
        (SHEARED, [-0.5, 0.05, 0], 0.05),
        (SHEARED, [-1.5, 0.05, 0], 0.05),
        (SHEARED, [-2.5, 0.05, 0], 0.05),
        (SHEARED, [-3.5, 0.05, 0], 0.05),
    ],
)
def test_crystal_distance_matrix_uses_the_nearest_periodic_image(matrix, frac, expected):
    crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], frac], Lattice(matrix))
    dist = get_distance_matrix(crystal, use_pbc=True)
    assert dist[0, 1] == pytest.approx(expected, abs=1e-9)
    assert dist[1, 0] == dist[0, 1]


def test_crystal_distance_matrix_without_pbc_is_the_cartesian_distance():
    crystal = Crystal(['H', 'H'], [[0, 0, 0], [0.99, 0, 0]], Lattice.cubic(100))
    assert get_distance_matrix(crystal, use_pbc=False)[0, 1] == pytest.approx(99.0)


def test_edge_list_lists_bonded_pairs():
    assert get_edge_list(make_simple_molecule(), cutoff=2.0) == [(0, 1)]


def test_edge_list_with_distances():
    edges = get_edge_list(make_simple_molecule(), cutoff=2.0, include_distances=True)
    assert len(edges) == 1
    i, j, dist = edges[0]
    assert (i, j) == (0, 1)
    assert dist == pytest.approx(1.2, abs=1e-5)


def test_coordination_counts_every_neighbour():
    mol = Molecule(['C', 'H', 'H', 'H', 'H'],
                   [[0, 0, 0], [2, 0, 0], [-2, 0, 0], [0, 2, 0], [0, -2, 0]])
    coord = get_coordination_numbers(mol, cutoff=2.5)
    assert coord[0] == 4  # C has 4 neighbours
    assert coord[1] == 1  # each H has only C


def test_degree_distribution_counts_atoms_per_degree():
    mol = Molecule(['C', 'H', 'H'], [[0, 0, 0], [1, 0, 0], [-1, 0, 0]])
    dist = get_degree_distribution(mol, cutoff=1.5)
    assert dist[2] == 1
    assert dist[1] == 2


def test_is_connected_false_for_distant_atoms():
    mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
    assert not is_connected(mol, cutoff=2.0)


def test_shortest_path_is_none_without_a_path():
    mol = Molecule(['C', 'C'], [[0, 0, 0], [10, 0, 0]])
    assert get_shortest_path(mol, 0, 1, cutoff=2.0) is None


def test_shortest_path_to_the_same_atom():
    mol = Molecule(['C'], [[0, 0, 0]])
    assert get_shortest_path(mol, 0, 0, cutoff=2.0) == [0]


def test_shortest_path_rejects_an_index_out_of_range():
    with pytest.raises(IndexError):
        get_shortest_path(make_simple_molecule(), 0, 10, cutoff=2.0)


def test_diameter_of_a_single_atom_is_zero():
    mol = Molecule(['C'], [[0, 0, 0]])
    assert get_graph_diameter(mol, cutoff=2.0) == 0


def test_node_features_are_atomic_numbers():
    features = get_node_features(make_simple_molecule())
    assert features.shape == (2, 1)
    assert features[0, 0] == 6  # C
    assert features[1, 0] == 8  # O


def test_statistics_of_a_diatomic_molecule():
    stats = get_graph_statistics(make_simple_molecule(), cutoff=2.0)
    assert stats['num_nodes'] == 2
    assert stats['num_edges'] == 1
    assert stats['is_connected']
    assert stats['num_components'] == 1
    assert stats['diameter'] == 1
    assert stats['avg_coordination'] == pytest.approx(1.0)
    assert stats['max_coordination'] == 1
    assert stats['min_coordination'] == 1


def test_laplacian_rows_sum_to_zero():
    L = get_graph_laplacian(make_simple_molecule(), cutoff=2.0)
    assert L.shape == (2, 2)
    assert np.allclose(L.sum(axis=1), 0)


def test_normalized_laplacian_has_unit_diagonal():
    L = get_graph_laplacian(make_simple_molecule(), cutoff=2.0, normalized=True)
    assert L.shape == (2, 2)
    assert np.allclose(np.diag(L), 1.0)


def test_crystal_statistics_count_nodes():
    crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice(10))
    stats = get_graph_statistics(crystal, cutoff=5.0)
    assert stats['num_nodes'] == 2
    assert stats['num_edges'] >= 0


def test_single_atom_molecule_is_one_component():
    mol = Molecule(['C'], [[0, 0, 0]])
    assert get_adjacency_matrix(mol, cutoff=2.0).shape == (1, 1)
    assert is_connected(mol, cutoff=2.0)
    assert len(get_connected_components(mol, cutoff=2.0)) == 1


def test_linear_chain_diameter_and_path():
    mol = Molecule(['C'] * 5, [[i, 0, 0] for i in range(5)])
    assert get_graph_diameter(mol, cutoff=1.5) == 4
    assert len(get_shortest_path(mol, 0, 4, cutoff=1.5)) == 5


def test_crystal_full_workflow_reports_nodes():
    crystal = make_simple_crystal(Lattice(10))
    get_adjacency_matrix(crystal, cutoff=8.0)
    get_edge_list(crystal, cutoff=8.0)
    get_coordination_numbers(crystal, cutoff=8.0)
    stats = get_graph_statistics(crystal, cutoff=8.0)
    assert isinstance(stats, dict)
    assert stats['num_nodes'] == 2
