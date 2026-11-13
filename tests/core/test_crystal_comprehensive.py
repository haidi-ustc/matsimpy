"""Tests for the Crystal class: reading, wrapping, neighbours and serialization."""

from pathlib import Path

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.io import read


def test_from_file_reads_poscar():
    # real pymatgen test file (tests/calculator/fixtures/vasp/PROVENANCE.md)
    poscar = Path(__file__).parents[1] / "calculator" / "fixtures" / "vasp" / "POSCAR_C2"
    crystal = read(str(poscar))
    assert isinstance(crystal, Crystal)
    assert crystal.species == ("C", "C")
    assert crystal.lattice.volume == pytest.approx(2 * 1.786855**3)


def test_wrap_moves_positions_into_the_cell():
    crystal = Crystal(["Fe", "O"], [[1.5, -0.3, 2.5], [0.2, 0.2, 0.2]], Lattice.cubic(10.0))
    wrapped = crystal.wrap()
    np.testing.assert_allclose(wrapped.frac_positions, [[0.5, 0.7, 0.5], [0.2, 0.2, 0.2]])
    np.testing.assert_allclose(wrapped.sites[0].frac_position, [0.5, 0.7, 0.5])


def test_wrap_leaves_non_periodic_axes_alone():
    c = Crystal(["C"], [[1.5, -0.25, 1.3]], Lattice.cubic(5.0), pbc=[True, True, False])
    np.testing.assert_allclose(c.wrap().frac_positions, [[0.5, 0.75, 1.3]])


def test_neighbor_list_finds_neighbours_of_atoms_stored_outside_the_cell():
    # Cl stored three cells away is 1.5 Å from Na through the boundary
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [3.375, -2, 1]], Lattice.cubic(4.0))
    nl = c.get_neighbor_list(2.5)
    assert nl[0] == [(1, pytest.approx(1.5))]
    assert nl == c.wrap().get_neighbor_list(2.5)


def test_neighbor_search_in_a_very_skewed_cell_finds_close_images():
    # the reciprocal height bounds the image search, not the lattice vector length
    c = Crystal(["H", "H"], [[0, 0, 0], [0, 0.5, 0]], Lattice([[10, 0, 0], [99.99, 0.01, 0], [0, 0, 10]]))
    distances = dict(c.get_neighbor_list(0.02, atom_index=0, use_pbc=True)[0])
    assert distances[1] == pytest.approx(np.hypot(0.005, 0.005))


def test_single_atom_neighbor_list_includes_the_cutoff_distance():
    c = Crystal(["Cu", "Cu"], [[0, 0, 0], [0.5, 0, 0]], Lattice.cubic(3.0), pbc=[False] * 3)
    assert c.get_neighbor_list(1.5, atom_index=0, use_pbc=False) == {0: [(1, 1.5)]}


def test_add_atom_checks_distances_through_periodic_boundaries_only():
    c = Crystal(["Si"], [[0.01, 0.5, 0.5]], Lattice.cubic(5.0))
    with pytest.raises(ValueError, match="too close"):
        c.add_atom("Si", [0.99, 0.5, 0.5])  # 0.1 Å apart through the boundary
    assert len(c.set_pbc([False, True, True]).add_atom("Si", [0.99, 0.5, 0.5])) == 2  # 4.9 Å apart


def test_add_atom_uses_the_true_minimum_image_in_a_skewed_cell():
    c = Crystal(["H"], [[0, 0, 0]], Lattice([[1, 0, 0], [0.9, 0.3, 0], [0, 0, 10]]))
    # the closest image is ~0.19 Å away; rounding fractional differences gives 1.3 Å
    with pytest.raises(ValueError, match="too close"):
        c.add_atom("H", [0.6, 0.6, 0.0])


def test_from_dict_rejects_cart_positions_that_disagree_with_frac_positions():
    d = Crystal(["Fe"], [[0.1, 0.2, 0.3]], Lattice.cubic(2.87)).as_dict()
    d["cart_positions"] = [[1.0, 1.0, 1.0]]
    with pytest.raises(ValueError, match="inconsistent"):
        Crystal.from_dict(d)


@pytest.mark.parametrize("pbc", [np.array([True, True, False]), [np.bool_(True), np.bool_(True), np.bool_(False)]])
def test_pbc_accepts_numpy_bools(pbc):
    c = Crystal(["H"], [[0, 0, 0]], Lattice.cubic(5.0), pbc=pbc)
    assert c.pbc == (True, True, False)
    assert c.set_pbc(pbc).pbc == (True, True, False)


@pytest.mark.parametrize("make", [
    lambda: Crystal(["Si"], [[0, 0, 0]], None),
    lambda: Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5), pbc=[True, False]),
    lambda: Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5)).set_pbc([True, False]),
    lambda: Crystal.from_dict({"species": ["Si"], "positions": [[0, 0, 0]], "lattice": None, "pbc": [True] * 3}),
    lambda: Crystal.from_dict({"species": ["Si"], "positions": [[0, 0, 0]],
                               "lattice": Lattice.cubic(5).as_dict(), "pbc": [True, "yes", True]}),
])
def test_invalid_lattice_or_pbc_raise(make):
    with pytest.raises(ValueError):
        make()
