"""Tests for Molecule neighbour lists."""

import pytest

from matsimpy.core import Molecule


@pytest.mark.parametrize("cutoff, error", [(-1.0, ValueError), (float("nan"), ValueError), (True, TypeError)])
def test_all_neighbor_lists_reject_bad_cutoffs(cutoff, error):
    with pytest.raises(error):
        Molecule(["C"], [[0, 0, 0]]).get_all_neighbor_lists(cutoff)


def test_all_neighbor_lists_include_the_cutoff_distance():
    m = Molecule(["H", "H"], [[0, 0, 0], [1, 0, 0]])
    assert m.get_all_neighbor_lists(1.0) == [[1], [0]]
    assert Molecule(["C"], [[0, 0, 0]]).get_all_neighbor_lists(5.0) == [[]]


def test_all_neighbor_lists_match_single_atom_queries():
    mol = Molecule(["C", "O", "H", "N"], [[0, 0, 0], [1.2, 0, 0], [2.5, 0, 0], [0.5, 0.5, 0]])
    all_neighbors = mol.get_all_neighbor_lists(2.0)
    for i in range(len(mol)):
        single = mol.get_neighbor_list(cutoff=2.0, atom_index=i)[i]
        assert sorted(all_neighbors[i]) == sorted(j for j, _ in single)


def test_neighbor_list_out_of_range_index_names_the_index():
    mol = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])
    with pytest.raises(IndexError, match="10.*out of range|out of range.*10"):
        mol.get_neighbor_list(cutoff=2.0, atom_index=10)
