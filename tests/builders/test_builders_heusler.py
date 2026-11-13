"""Tests for Heusler alloy builders."""
import numpy as np
import pytest

from matsimpy.builders.alloy.heusler import (
    build_full_heusler,
    build_half_heusler,
    build_heusler,
    build_inverse_heusler,
    build_quaternary_heusler,
)

spglib = pytest.importorskip("spglib")


def _space_group(crystal):
    numbers = {element: i for i, element in enumerate(dict.fromkeys(crystal.species))}
    cell = (crystal.lattice.matrix, crystal.frac_positions, [numbers[s] for s in crystal.species])
    return spglib.get_symmetry_dataset(cell, symprec=1e-4).number


def _nearest_distance(crystal):
    cart = crystal.cart_positions
    images = np.array([[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]) @ crystal.lattice.matrix
    d = np.linalg.norm(cart[:, None, None] - cart[None, :, None] - images[None, None], axis=-1).min(axis=-1)
    np.fill_diagonal(d, np.inf)
    return d


@pytest.mark.parametrize("builder,args,formula,number", [
    # the old builders gave F-43m, R3m (3 atoms), Cmmm and I-4m2 respectively
    (build_full_heusler, ("Cu", "Mn", "Al"), "Cu8Mn4Al4", 225),
    (build_half_heusler, ("Ni", "Mn", "Sb"), "Ni4Mn4Sb4", 216),
    (build_inverse_heusler, ("Mn", "Co", "Al"), "Mn8Co4Al4", 216),
    (build_quaternary_heusler, ("Co", "Fe", "Mn", "Si"), "Co4Fe4Mn4Si4", 216),
])
def test_space_group_and_bond_length(builder, args, formula, number):
    crystal = builder(*args, 5.8)
    assert crystal.formula == formula
    assert _space_group(crystal) == number
    assert np.isclose(_nearest_distance(crystal).min(), np.sqrt(3) / 4 * 5.8)


def test_full_heusler_x_forms_simple_cubic_sublattice():
    crystal = build_full_heusler("Cu", "Mn", "Al", 5.95)
    d = _nearest_distance(crystal)
    x = np.array(crystal.species) == "Cu"
    # each Cu has 4 Mn and 4 Al nearest neighbours, Cu-Cu is a/2
    assert np.isclose(d[np.ix_(x, x)].min(), 5.95 / 2)


def test_inverse_heusler_x_atoms_are_nearest_neighbours():
    crystal = build_inverse_heusler("Mn", "Co", "Al", 5.8)
    d = _nearest_distance(crystal)
    x = np.array(crystal.species) == "Mn"
    assert np.isclose(d[np.ix_(x, x)].min(), np.sqrt(3) / 4 * 5.8)


def test_build_heusler_dispatches():
    assert build_heusler("Co", "Ti", "Sb", 5.90, "half").formula == "Co4Ti4Sb4"
    assert build_heusler("Mn", "V", "Al", 5.80, "Inverse").formula == "Mn8V4Al4"
    assert _space_group(build_heusler("Co", "Mn", "Si", 5.65)) == 225


def test_invalid_inputs():
    with pytest.raises(ValueError, match="Unknown Heusler type"):
        build_heusler("Cu", "Mn", "Al", 5.95, "invalid")
    with pytest.raises(ValueError, match="lattice_constant"):
        build_full_heusler("Cu", "Mn", "Al", 0.0)
    with pytest.raises(TypeError):
        build_full_heusler("Cu", "Mn", "Al", 5.95, extra=1)
