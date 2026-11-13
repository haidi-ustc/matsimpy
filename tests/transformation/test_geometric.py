"""Tests for matsimpy.transformation.geometric: translate, rotate, translate_to_origin."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation import rotate, translate
from matsimpy.transformation.geometric import translate_to_origin


@pytest.fixture
def co():
    return Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])


def test_translate_molecule(co):
    out = translate(co, [1, 1, 1])
    assert out is not co
    np.testing.assert_allclose(out.positions, [[1, 1, 1], [2.2, 1, 1]])
    np.testing.assert_allclose(co.positions, [[0, 0, 0], [1.2, 0, 0]])


def test_translate_crystal_keeps_sites_in_sync():
    out = translate(Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(10)), [1, 1, 1])
    np.testing.assert_allclose(out.cart_positions[0], [1, 1, 1])
    np.testing.assert_allclose(out.sites[0].frac_position, out.frac_positions[0])


def test_translate_requires_a_3_vector(co):
    with pytest.raises(ValueError):
        translate(co, [1, 1])


def test_rotate_molecule_about_a_point(co):
    out = rotate(co, angle=90, axis=[0, 0, 1], center=[0, 0, 0])
    np.testing.assert_allclose(out.positions[1], [0, 1.2, 0], atol=1e-12)
    np.testing.assert_allclose(co.positions[1], [1.2, 0, 0])


def test_rotate_crystal_keeps_sites_in_sync():
    out = rotate(Crystal(["Si"], [[0.1, 0.0, 0.0]], Lattice.cubic(10)), angle=90, axis=[0, 0, 1], center=[0, 0, 0])
    np.testing.assert_allclose(out.frac_positions[0], [0.0, 0.1, 0.0], atol=1e-12)
    np.testing.assert_allclose(out.sites[0].frac_position, out.frac_positions[0])


def test_translate_to_origin_uses_the_mass_weighted_center_for_crystals():
    out = translate_to_origin(Crystal(["H", "O"], [[0, 0, 0], [0.5, 0, 0]], Lattice.cubic(4.0)))
    masses = [out.elements[i].atomic_mass for i in range(2)]
    np.testing.assert_allclose(np.average(out.cart_positions, weights=masses, axis=0), 0, atol=1e-12)
