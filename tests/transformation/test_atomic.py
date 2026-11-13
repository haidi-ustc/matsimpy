"""Tests for matsimpy.transformation.atomic: move, swap, merge, split, sort, center, perturb."""

import numpy as np
import pytest

from matsimpy.analysis.selection import AtomSelection
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation.atomic import (
    center_structure,
    merge_atoms,
    move_atoms,
    perturb_positions,
    sort_atoms,
    split_atom,
    swap_atoms,
)


@pytest.fixture
def sio():
    return Crystal(["Si", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10.0))


@pytest.fixture
def hoh():
    return Molecule(["H", "O", "H"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
                    site_properties=[{"id": 0}, {"id": 1}, {"id": 2}])


# --------------------------------------------------------------------------
# Index validation (shared by all atomic operations)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("call, error", [
    (lambda m: move_atoms(m, [0, 0], [1.0, 0, 0]), ValueError),
    (lambda m: move_atoms(m, True, [1.0, 0, 0]), TypeError),
    (lambda m: move_atoms(m, 0, 1.0), ValueError),  # used to broadcast to [1, 1, 1]
    (lambda m: swap_atoms(m, 1, 1), ValueError),
    (lambda m: merge_atoms(m, 0, 0), ValueError),
    (lambda m: perturb_positions(m, 0.1, indices=[0, 0], seed=1), ValueError),
])
def test_invalid_indices_and_vectors_raise(hoh, call, error):
    with pytest.raises(error):
        call(hoh)


# --------------------------------------------------------------------------
# move / swap
# --------------------------------------------------------------------------


def test_move_atoms_moves_only_the_selected_atoms(sio):
    moved = move_atoms(sio, [1], [1.0, 0, 0])
    np.testing.assert_allclose(moved.cart_positions, [[0, 0, 0], [6, 5, 5]])
    moved_frac = move_atoms(sio, np.int64(0), [0.1, 0, 0], cartesian=False)
    np.testing.assert_allclose(moved_frac.frac_positions[0], [0.1, 0, 0])


def test_swap_atoms_exchanges_species_positions_and_site_properties(hoh):
    swapped = swap_atoms(hoh, 0, 1)
    assert swapped.species == ("O", "H", "H")
    np.testing.assert_allclose(swapped.positions[0], [1, 0, 0])
    assert swapped.site_properties[:2] == ({"id": 1}, {"id": 0})


# --------------------------------------------------------------------------
# merge / split
# --------------------------------------------------------------------------


def test_merge_atoms_keeps_the_first_atom_site_properties(hoh):
    merged = merge_atoms(hoh, 0, 1)
    assert merged.species == ("H", "H")
    np.testing.assert_allclose(merged.positions[0], [0.5, 0, 0])
    assert merged.site_properties == ({"id": 0}, {"id": 2})


def test_merge_atoms_with_custom_species_and_position(sio):
    merged = merge_atoms(sio, 0, 1, species="C", position=[0.25, 0.25, 0.25])
    assert merged.species == ("C",)
    np.testing.assert_allclose(merged.frac_positions[0], [0.25, 0.25, 0.25])


def test_merge_atoms_uses_the_minimum_image_midpoint():
    c = Crystal(["H", "H"], [[0.05, 0.5, 0.5], [0.95, 0.5, 0.5]], Lattice.cubic(5.0))
    x = merge_atoms(c, 0, 1).frac_positions[0, 0] % 1.0
    assert min(x, 1.0 - x) == pytest.approx(0.0, abs=1e-12)


def test_split_atom_copies_the_source_site_properties():
    m = Molecule(["O", "He"], [[0, 0, 0], [3, 0, 0]], site_properties=[{"role": "split"}, {"role": "kept"}])
    split = split_atom(m, 0, ["H", "H"], [[-0.5, 0, 0], [0.5, 0, 0]])
    assert split.species == ("He", "H", "H")
    assert split.site_properties == ({"role": "kept"}, {"role": "split"}, {"role": "split"})


def test_split_atom_needs_one_position_per_species():
    with pytest.raises(ValueError, match="same length"):
        split_atom(Molecule(["O"], [[0, 0, 0]]), 0, ["H", "H"], [[0, 0, 0]])


# --------------------------------------------------------------------------
# sort / center
# --------------------------------------------------------------------------


@pytest.mark.parametrize("key, order", [
    ("species", ("C", "O", "Si")),
    ("z", ("C", "O", "Si")),
    ("mass", ("C", "O", "Si")),
    ("distance", ("O", "C", "Si")),
    (lambda s, i: -s.cart_positions[i][0], ("Si", "C", "O")),
])
def test_sort_atoms(key, order):
    c = Crystal(["O", "Si", "C"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], Lattice.cubic(10))
    assert sort_atoms(c, key=key).species == order


def test_sort_atoms_reorders_site_properties():
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64),
                site_properties=[{"label": "Na-site"}, {"label": "Cl-site"}])
    assert sort_atoms(c, key="species").site_properties == ({"label": "Cl-site"}, {"label": "Na-site"})


def test_center_structure_moves_the_center_of_mass():
    m = Molecule(["O", "C", "H"], [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0]])
    np.testing.assert_allclose(center_structure(m, center=[5, 5, 5]).get_center_of_mass(), [5, 5, 5])


# --------------------------------------------------------------------------
# perturb_positions
# --------------------------------------------------------------------------


@pytest.mark.parametrize("structure", [
    Crystal(["Si", "O", "Si", "O"], [[0, 0, 0], [0.25] * 3, [0.5] * 3, [0.75] * 3], Lattice.cubic(5.0)),
    Molecule(["H", "O", "H", "C"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0], [1.5, 0, 0]]),
])
def test_perturb_positions_moves_only_the_selected_atoms(structure):
    target = structure.species[0]
    selection = AtomSelection(structure).by_species(target)
    result = perturb_positions(structure, 0.1, indices=selection, seed=42)
    moved = ~np.all(np.isclose(result.positions, structure.positions), axis=1)
    assert moved.tolist() == [s == target for s in structure.species]


def test_perturb_positions_rejects_a_selection_from_another_structure():
    a, b = (from_prototype("diamond", "Si", 5.43) for _ in range(2))
    with pytest.raises(ValueError):
        perturb_positions(b, 0.1, indices=AtomSelection(a).by_species("Si"))


def test_perturb_positions_keeps_pbc_and_does_not_touch_the_global_rng():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(1.0), pbc=[True, False, True])
    np.random.seed(123)
    expected_next = np.random.random(3)
    np.random.seed(123)
    perturbed = perturb_positions(crystal, 0.1, seed=999)
    np.testing.assert_allclose(np.random.random(3), expected_next)
    assert perturbed.pbc == (True, False, True)
