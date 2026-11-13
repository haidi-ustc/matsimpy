"""Tests for matsimpy.transformation.lattice: strain, rotation, scaling, reduction.

Row-vector convention: a deformation gradient F maps lattice vectors as A' = A @ F.T.
"""

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Lattice
from matsimpy.transformation.lattice import (
    apply_deformation,
    apply_strain,
    get_niggli_reduced,
    optimize_lattice,
    perturb_lattice,
    rotate_lattice,
    scale_lattice,
    set_volume,
    standardize_cell,
    transform_lattice,
)


@pytest.fixture
def tric():
    lat = Lattice.from_parameters(3.0, 3.5, 4.0, 80, 100, 110)
    return Crystal(["Na", "Cl"], [[0.1, 0.2, 0.3], [0.6, 0.55, 0.8]], lat)


@pytest.fixture
def si():
    return from_prototype("diamond", "Si", 5.43)


# --------------------------------------------------------------------------
# Strain and deformation
# --------------------------------------------------------------------------


def test_apply_deformation_maps_lattice_and_atoms_by_f(tric):
    F = np.array([[1.05, 0.1, 0.0], [0.0, 0.98, 0.03], [0.02, 0.0, 1.01]])
    out = apply_deformation(tric, F)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ F.T, atol=1e-12)
    np.testing.assert_allclose(out.cart_positions, tric.cart_positions @ F.T, atol=1e-12)


def test_apply_deformation_without_positions_keeps_cartesian_positions(tric):
    F = [[1.1, 0, 0], [0, 1, 0], [0, 0, 1]]
    out = apply_deformation(tric, F, deform_positions=False)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ np.array(F).T, atol=1e-12)
    np.testing.assert_allclose(out.cart_positions, tric.cart_positions, atol=1e-12)


def test_apply_strain_is_deformation_by_identity_plus_strain(tric):
    strain = np.array([[0.01, 0.02, 0.0], [0.02, -0.01, 0.0], [0.0, 0.0, 0.03]])
    np.testing.assert_allclose(
        apply_strain(tric, strain).lattice.matrix,
        apply_deformation(tric, np.eye(3) + strain).lattice.matrix,
        atol=1e-12,
    )


def test_apply_strain_vector_is_the_diagonal(tric):
    np.testing.assert_allclose(
        apply_strain(tric, [0.01, 0.0, 0.02]).lattice.matrix,
        apply_strain(tric, np.diag([0.01, 0.0, 0.02])).lattice.matrix,
    )


@pytest.mark.parametrize("strain, error", [
    (0.01, ValueError),
    ([0.01, 0.0], ValueError),
    ([[0.01, 0, 0], [0, 0, 0]], ValueError),
    ([[True, 0, 0], [0, 0, 0], [0, 0, 0]], TypeError),
    ([-1.0, 0.0, 0.0], ValueError),  # det(I + e) = 0
])
def test_apply_strain_rejects_bad_input(tric, strain, error):
    with pytest.raises(error):
        apply_strain(tric, strain)


def test_perturb_lattice_keeps_fractional_coordinates_and_the_global_rng(si):
    np.random.seed(456)
    expected_next = np.random.random(3)
    np.random.seed(456)
    out = perturb_lattice(si, 0.1, seed=999)
    np.testing.assert_allclose(np.random.random(3), expected_next)
    np.testing.assert_allclose(out.frac_positions, si.frac_positions)
    assert not np.allclose(out.lattice.matrix, si.lattice.matrix)


# --------------------------------------------------------------------------
# Rotation and general transformation
# --------------------------------------------------------------------------


def test_rotate_lattice_rotates_lattice_and_atoms(tric):
    R = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    out = rotate_lattice(tric, R)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ R.T, atol=1e-12)
    np.testing.assert_allclose(out.cart_positions, tric.cart_positions @ R.T, atol=1e-12)
    kept = rotate_lattice(tric, R, rotate_atoms=False)
    np.testing.assert_allclose(kept.cart_positions, tric.cart_positions, atol=1e-12)


@pytest.mark.parametrize("R, match", [(np.diag([1.1, 1.0, 1.0]), "orthogonal"), (np.diag([-1.0, 1.0, 1.0]), "proper")])
def test_rotate_lattice_requires_a_proper_rotation(tric, R, match):
    with pytest.raises(ValueError, match=match):
        rotate_lattice(tric, R)


def test_transform_lattice_moves_atoms_with_the_cell_by_default(tric):
    T = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.1]])
    out = transform_lattice(tric, T)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ T.T, atol=1e-12)
    np.testing.assert_allclose(out.frac_positions, tric.frac_positions, atol=1e-12)


# --------------------------------------------------------------------------
# Scaling
# --------------------------------------------------------------------------


def test_scale_lattice(si):
    assert scale_lattice(si, 1.1).lattice.a == pytest.approx(si.lattice.a * 1.1)


@pytest.mark.parametrize("factor, error", [
    (0, ValueError), (-1, ValueError), (float("nan"), ValueError),
    ([1, 1], ValueError), ([1, -1, 1], ValueError), ([1, float("inf"), 1], ValueError),
    (True, TypeError), ([True, 1.0, 1.0], TypeError),
])
def test_scale_lattice_rejects_bad_factors(si, factor, error):
    with pytest.raises(error):
        scale_lattice(si, factor)


def test_set_volume_rejects_non_positive_volume(si):
    with pytest.raises(ValueError, match="target_volume"):
        set_volume(si, -100)


def test_optimize_lattice_reaches_the_target(si):
    assert optimize_lattice(si, target_volume=200.0).volume == pytest.approx(200.0)
    assert optimize_lattice(si, target_density=2.33).density == pytest.approx(2.33)


@pytest.mark.parametrize("kwargs, match", [
    ({}, None),
    ({"target_density": 2.0, "target_volume": 50.0}, "only one"),
    ({"target_volume": 50.0, "preserve_angles": False}, "preserve_angles"),
])
def test_optimize_lattice_rejects_bad_targets(si, kwargs, match):
    with pytest.raises(ValueError, match=match):
        optimize_lattice(si, **kwargs)


# --------------------------------------------------------------------------
# Niggli reduction and standardization
# --------------------------------------------------------------------------


def test_get_niggli_reduced_keeps_atoms_and_metadata():
    pytest.importorskip("spglib")
    crystal = Crystal(["He"], [[0.25, 0.25, 0.25]],
                      Lattice([[2.0, 0.1, 0.0], [0.0, 1.9, 0.2], [0.1, 0.0, 2.1]]),
                      site_properties=[{"tag": "kept"}])
    reduced = get_niggli_reduced(crystal)
    assert reduced.species == crystal.species
    assert reduced.pbc == crystal.pbc
    assert reduced.site_properties == crystal.site_properties
    np.testing.assert_allclose(reduced.cart_positions, crystal.cart_positions, atol=1e-10)


def test_standardize_cell_to_primitive(si):
    pytest.importorskip("spglib")
    conventional = standardize_cell(si)
    assert len(conventional) == 8
    assert len(standardize_cell(conventional, to_primitive=True)) == 2


def test_standardize_cell_reorders_site_properties_with_the_sites(monkeypatch):
    spglib = pytest.importorskip("spglib")
    crystal = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64),
                      site_properties=[{"id": "Na"}, {"id": "Cl"}])

    def swapped(cell):
        lattice, positions, numbers = cell
        return lattice, positions[[1, 0]], np.array(numbers)[[1, 0]]

    monkeypatch.setattr(spglib, "standardize_cell", swapped)
    out = standardize_cell(crystal)
    assert out.species == ("Cl", "Na")
    assert out.site_properties == ({"id": "Cl"}, {"id": "Na"})


def test_standardize_cell_raises_when_site_properties_cannot_follow():
    pytest.importorskip("spglib")
    fcc_prim = Crystal(["Cu"], [[0, 0, 0]], Lattice([[0, 1.8, 1.8], [1.8, 0, 1.8], [1.8, 1.8, 0]]),
                       site_properties=[{"magmom": 1.0}])
    with pytest.raises(ValueError, match="site properties"):
        standardize_cell(fcc_prim)  # 1 atom -> 4 atoms


def test_standardize_cell_requires_full_periodicity():
    pytest.importorskip("spglib")
    slab = Crystal(["Cu"], [[0, 0, 0]], Lattice.cubic(3.0), pbc=[True, True, False])
    with pytest.raises(ValueError, match="periodic"):
        standardize_cell(slab)
