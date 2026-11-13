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


def test_attributes_cannot_be_reassigned_but_copies_work():
    lat = Lattice.cubic(3.0)
    with pytest.raises(AttributeError):
        lat._matrix = np.eye(3)
    assert copy.deepcopy(lat) == lat
    assert pickle.loads(pickle.dumps(lat)) == lat


def test_repr():
    assert "Lattice" in repr(Lattice.cubic(10.0))
