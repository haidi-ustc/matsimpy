"""Tests for the Molecule class: geometry operations, conversion and serialization."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Molecule


@pytest.fixture
def co():
    return Molecule(["C", "O"], [[0, 0, 0], [1.4, 0, 0]])


@pytest.mark.parametrize("vector", [[1], [1, 2], [[1, 2, 3], [1, 2, 3]]])
def test_translate_requires_a_3_vector(co, vector):
    with pytest.raises(ValueError):
        co.translate(vector)


def test_rotate_keeps_the_original_cache(co):
    com = co.get_center_of_mass()
    co.rotate(90, [0, 0, 1])
    assert co.get_center_of_mass() == com


def test_to_crystal_pads_with_vacuum_and_keeps_site_properties():
    m = Molecule(["C", "O"], [[0, 0, 0], [1.4, 0, 0]], site_properties=[{"q": -1}, {"q": 1}])
    crystal = m.to_crystal()
    assert isinstance(crystal, Crystal)
    assert crystal.lattice.a > 1.4 + 15.0
    assert crystal.pbc == (False, False, False)
    assert crystal.site_properties == ({"q": -1}, {"q": 1})


@pytest.mark.parametrize("vacuum, error", [(-1.0, ValueError), (float("nan"), ValueError), (True, TypeError)])
def test_to_crystal_rejects_bad_vacuum(co, vacuum, error):
    with pytest.raises(error):
        co.to_crystal(vacuum)


def test_moment_of_inertia_is_symmetric(co):
    moment = co.get_moment_of_inertia()
    assert moment.shape == (3, 3)
    np.testing.assert_allclose(moment, moment.T)


def test_as_dict_keeps_site_properties():
    m = Molecule(["C", "O"], [[0, 0, 0], [1.4, 0, 0]], site_properties=[{"charge": 0}, {"charge": -1}])
    assert Molecule.from_dict(m.as_dict()).site_properties == m.site_properties


def test_repr(co):
    assert "Molecule" in repr(co)


@pytest.mark.parametrize("make", [
    lambda: Molecule(["H"], [[True, 0, 0]]),
    lambda: Molecule(["H"], [[0, 0, 0]]).add_atom("H", [True, 0, 3]),
])
def test_bool_coordinates_are_rejected(make):
    with pytest.raises(TypeError):
        make()
