"""Tests for the Lattice class: constructors, validation and immutability."""

import copy
import pickle

import numpy as np
import pytest

from matsimpy.core import Lattice


@pytest.mark.parametrize("arg, abc", [
    (5, (5.0, 5.0, 5.0)),
    (5.43, (5.43, 5.43, 5.43)),
    ([3, 4, 5], (3.0, 4.0, 5.0)),
    ([1, 10, 100], (1.0, 10.0, 100.0)),
])
def test_scalar_and_list_give_orthogonal_cells(arg, abc):
    lat = Lattice(arg)
    assert (lat.a, lat.b, lat.c) == pytest.approx(abc)
    assert (lat.alpha, lat.beta, lat.gamma) == pytest.approx((90.0, 90.0, 90.0))


@pytest.mark.parametrize("lat, abc, angles", [
    (Lattice.hexagonal(a=3.0, c=5.0), (3, 3, 5), (90, 90, 120)),
    (Lattice.monoclinic(a=5.0, b=6.0, c=7.0, beta=120.0), (5, 6, 7), (90, 120, 90)),
    (Lattice.triclinic(a=5.0, b=6.0, c=7.0, alpha=80.0, beta=90.0, gamma=100.0), (5, 6, 7), (80, 90, 100)),
])
def test_named_constructors(lat, abc, angles):
    assert (lat.a, lat.b, lat.c) == pytest.approx(abc)
    assert (lat.alpha, lat.beta, lat.gamma) == pytest.approx(angles)


@pytest.mark.parametrize("make", [
    lambda: Lattice(-5),
    lambda: Lattice([3, -4, 5]),
    lambda: Lattice.cubic(-3.0),  # used to give a left-handed cell with det -27
    lambda: Lattice.tetragonal(3.0, 0.0),
    lambda: Lattice.orthorhombic(3.0, 4.0, float("nan")),
    lambda: Lattice.hexagonal(-2.46, 10.0),
    lambda: Lattice.from_parameters(3.0, 3.0, float("inf"), 90, 90, 90),
])
def test_non_positive_or_non_finite_lengths_raise(make):
    with pytest.raises(ValueError, match="positive"):
        make()


@pytest.mark.parametrize("make", [
    lambda: Lattice("invalid"),
    lambda: Lattice({"a": 5}),
    lambda: Lattice(True),
    lambda: Lattice([True, True, True]),
    lambda: Lattice.from_parameters(3, 3, 3, 90, 90, True),
])
def test_wrong_types_raise(make):
    with pytest.raises(TypeError):
        make()


def test_non_3d_vectors_raise():
    with pytest.raises(ValueError):
        Lattice([[1, 0], [0, 1]])


def test_from_parameters_returns_float64_for_numpy_scalars():
    assert Lattice.from_parameters(np.float32(3), 3, 3, 90, 90, 120).matrix.dtype == np.float64


def test_copies_compare_equal():
    lat = Lattice.cubic(3.0)
    assert copy.deepcopy(lat) == lat
    assert pickle.loads(pickle.dumps(lat)) == lat


def test_repr():
    assert "Lattice" in repr(Lattice.cubic(10.0))


# --------------------------------------------------------------------------
# Minimum image
# --------------------------------------------------------------------------


def _brute_force_min_image(lattice, frac, pbc, basis=None):
    """Shortest image by enumerating every translation that could beat the rounded one.

    ``basis`` is an optional unimodular integer matrix written by hand for a nearly
    degenerate cell; its rows span the same periodic translations, so the enumeration
    stays small. The enumeration bound is R over the plane spacing on each axis.
    """
    u = np.eye(3) if basis is None else np.array(basis, dtype=float)
    vectors = u @ lattice.matrix
    coords = frac @ np.linalg.inv(u)          # same displacement in the ``vectors`` basis
    periodic = np.array(pbc)
    coords = np.where(periodic, coords - np.rint(coords), coords)
    radius = np.linalg.norm(coords @ vectors)
    reach = np.floor(radius * np.linalg.norm(np.linalg.inv(vectors), axis=0) + 0.5 + 1e-9).astype(int)
    steps = [np.arange(-n, n + 1) if p else np.array([0]) for n, p in zip(reach, pbc)]
    shifts = np.stack(np.meshgrid(*steps, indexing="ij"), axis=-1).reshape(-1, 3)
    return np.linalg.norm((coords + shifts) @ vectors, axis=1).min()


SKEWED = [
    (Lattice([[4, 0, 0], [16, 0.4, 0], [0, 0, 4]]), None),
    # b - 10a = (-0.01, 0.01, 0): enumerate in that basis
    (Lattice([[10, 0, 0], [99.99, 0.01, 0], [0, 0, 10]]), [[1, 0, 0], [-10, 1, 0], [0, 0, 1]]),
    (Lattice([[3.1, 0.2, 0.1], [7.9, 2.3, 0.4], [-5.2, 6.1, 1.7]]), None),
    (Lattice.from_parameters(3.0, 3.5, 4.0, 80, 100, 110), None),
]


@pytest.mark.parametrize("lattice, basis", SKEWED)
@pytest.mark.parametrize("pbc", [(True, True, True), (True, True, False)])
def test_min_image_vectors_are_exact_in_skewed_cells(lattice, basis, pbc):
    frac = np.random.default_rng(0).uniform(-3, 3, size=(20, 3))
    lengths = np.linalg.norm(lattice.get_min_image_vectors(frac, pbc), axis=1)
    expected = [_brute_force_min_image(lattice, f, pbc, basis) for f in frac]
    np.testing.assert_allclose(lengths, expected, atol=1e-10)


def test_min_image_vectors_match_pymatgen():
    pmg = pytest.importorskip("pymatgen.core")
    lattice = SKEWED[0][0]
    distance, _ = pmg.Lattice(lattice.matrix).get_distance_and_image([0, 0, 0], [0, 0.5, 0])
    assert np.linalg.norm(lattice.get_min_image_vectors([0, 0.5, 0])) == pytest.approx(distance)


def test_min_image_vectors_with_a_cutoff_are_exact_only_below_it():
    lattice = SKEWED[0][0]
    frac = np.array([[0, 0.5, 0], [0.5, 0.5, 0.5]])
    exact = np.linalg.norm(lattice.get_min_image_vectors(frac), axis=1)
    capped = np.linalg.norm(lattice.get_min_image_vectors(frac, cutoff=0.5), axis=1)
    assert capped[0] == pytest.approx(exact[0]) == pytest.approx(0.2)
    assert capped[1] >= exact[1] > 0.5


def test_min_image_vectors_leave_non_periodic_axes_alone():
    v = Lattice.cubic(4.0).get_min_image_vectors([0.9, 0.9, 0.9], pbc=(True, False, False))
    np.testing.assert_allclose(v, [-0.4, 3.6, 3.6])
