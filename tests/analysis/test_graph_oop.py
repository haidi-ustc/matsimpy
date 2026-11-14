"""Tests for OOP graph API (MoleculeGraph and CrystalGraph)."""
import numpy as np
import pytest

from matsimpy.analysis.graph import (
    CrystalGraph,
    MoleculeGraph,
    create_structure_graph,
    get_coordination_numbers,
    get_degree_distribution,
)
from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.io import read
from tests.conftest import make_simple_crystal, make_simple_molecule, require_path


def _vasp_fixture(name):
    return read(require_path("tests", "calculator", "fixtures", "vasp", name))


def test_molecule_graph_repr_reports_nodes_and_edges():
    graph = MoleculeGraph(make_simple_molecule(), cutoff=2.0)
    text = repr(graph)
    assert "MoleculeGraph" in text
    assert "nodes=2" in text
    assert "edges=1" in text


def test_crystal_graph_distance_matrix_has_zero_diagonal():
    graph = CrystalGraph(make_simple_crystal(Lattice(10)), cutoff=8.0, use_pbc=True)
    dist = graph.distance_matrix
    assert dist.shape == (2, 2)
    assert dist[0, 0] == 0.0


def test_crystal_graph_without_pbc_keeps_flag_and_shape():
    graph = CrystalGraph(make_simple_crystal(Lattice(10)), cutoff=8.0, use_pbc=False)
    assert graph.use_pbc is False
    assert graph.adjacency_matrix.shape == (2, 2)


# POSCAR_MnO: primitive rocksalt, each atom has 6 neighbours at 2.26 A, then 12 at 3.20 A.
# POSCAR_bcc: conventional bcc (a = 1), each atom has 8 neighbours at 0.866 A, then 6 at 1.0 A.
@pytest.mark.parametrize(
    "fixture, cutoff, expected",
    [
        ("POSCAR_MnO", 2.5, {0: 6, 1: 6}),
        ("POSCAR_MnO", 3.5, {0: 18, 1: 18}),
        ("POSCAR_bcc", 0.9, {0: 8, 1: 8}),
    ],
)
def test_periodic_coordination_numbers_count_every_image(fixture, cutoff, expected):
    crystal = _vasp_fixture(fixture)
    assert get_coordination_numbers(crystal, cutoff=cutoff) == expected


def test_periodic_degree_distribution_counts_every_image():
    crystal = _vasp_fixture("POSCAR_MnO")
    assert get_degree_distribution(crystal, cutoff=2.5) == {6: 2}


def test_periodic_adjacency_matrix_carries_no_multiplicity():
    graph = CrystalGraph(_vasp_fixture("POSCAR_MnO"), cutoff=2.5, use_pbc=True)
    np.testing.assert_array_equal(graph.adjacency_matrix, [[0, 1], [1, 0]])


def test_coordination_numbers_without_pbc_count_in_cell_neighbours_only():
    # O and Mn are 3.917 A apart inside the cell; images are ignored.
    graph = CrystalGraph(_vasp_fixture("POSCAR_MnO"), cutoff=4.0, use_pbc=False)
    assert graph.coordination_numbers == {0: 1, 1: 1}


def test_create_structure_graph_defaults_to_pbc_for_crystal():
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice(10))
    graph = create_structure_graph(crystal, cutoff=5.0)
    assert isinstance(graph, CrystalGraph)
    assert graph.use_pbc is True


def test_create_structure_graph_rejects_non_structure():
    with pytest.raises(TypeError):
        create_structure_graph("invalid", cutoff=3.0)


def test_molecule_graph_rejects_crystal():
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice(10))
    with pytest.raises(TypeError):
        MoleculeGraph(crystal, cutoff=3.0)


def test_crystal_graph_rejects_molecule():
    with pytest.raises(TypeError):
        CrystalGraph(Molecule(["C"], [[0, 0, 0]]), cutoff=3.0)
