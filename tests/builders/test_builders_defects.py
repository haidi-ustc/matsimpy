"""Tests for the point-defect builders."""

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.defects import (
    create_antisite,
    create_frenkel,
    create_interstitial,
    create_schottky,
    create_substitution,
    create_vacancy,
)
from matsimpy.core import Crystal, Lattice
from matsimpy.transformation.structural import make_supercell

# Every coordinate is in [0, 1), yet the image of Cu at 2a is 0.2 Å from fractional
# (0, 0.5, 0): further than one cell away in the unreduced basis.
SKEW = Lattice([[4, 0, 0], [16, 0.4, 0], [0, 0, 4]])


@pytest.fixture
def si():
    return from_prototype("diamond", "Si", 5.43)


@pytest.fixture
def nacl():
    return from_prototype("rocksalt", ["Na", "Cl"], 5.64)


# --------------------------------------------------------------------------
# Vacancy and substitution
# --------------------------------------------------------------------------


def test_create_vacancy(si):
    assert len(create_vacancy(si, 0)) == len(si) - 1
    with pytest.raises(IndexError):
        create_vacancy(si, 1000)


def test_create_substitution(si):
    assert create_substitution(si, np.int64(1), "Ge").species[1] == "Ge"  # numpy index
    with pytest.raises(ValueError):
        create_substitution(si, [0, 1], ["Ni"])
    with pytest.raises(IndexError):
        create_substitution(si, 1000, "Ni")


# --------------------------------------------------------------------------
# Interstitial
# --------------------------------------------------------------------------


def test_create_interstitials(si):
    out = create_interstitial(si, ["H", "H"], [[0.5, 0.5, 0.5], [0.1, 0.1, 0.1]])
    assert out.species == si.species + ("H", "H")
    with pytest.raises(ValueError):
        create_interstitial(si, ["H", "H"], [[0.5, 0.5, 0.5]])


def test_interstitial_positions_wrap_along_periodic_axes_only(si):
    np.testing.assert_allclose(create_interstitial(si, "H", [1.5, 1.5, 1.5]).frac_positions[-1], 0.5)
    slab = Crystal(["Cu"], [[0, 0, 0.5]], Lattice.tetragonal(2.55, 20.0), pbc=(True, True, False))
    np.testing.assert_allclose(create_interstitial(slab, "H", [1.5, 0.5, 0.6]).frac_positions[-1], [0.5, 0.5, 0.6])
    assert create_interstitial(slab, "H", [0.5, 0.5, 1.2]).frac_positions[-1][2] == pytest.approx(1.2)


@pytest.mark.parametrize("structure, position", [
    (from_prototype("diamond", "Si", 5.43), [1.0, 0.0, 0.01]),
    (Crystal(["Cu"], [[3, 0, 0]], Lattice.cubic(4)), [0.025, 0, 0]),  # atom stored three cells away
    (Crystal(["Cu"], [[0, 0, 0]], SKEW), [0, 0.5, 0]),
])
def test_interstitial_too_close_to_an_atom_raises(structure, position):
    with pytest.raises(ValueError, match="from an existing atom|too close|already exists"):
        create_interstitial(structure, "H", position)


def test_interstitial_near_an_atom_across_a_non_periodic_axis_is_allowed():
    cell = Crystal(["Cu"], [[0, 0, 3]], Lattice.cubic(4), pbc=(True, True, False))
    np.testing.assert_allclose(create_interstitial(cell, "H", [0, 0, 0]).cart_positions, [[0, 0, 12], [0, 0, 0]])


# --------------------------------------------------------------------------
# Frenkel and Schottky
# --------------------------------------------------------------------------


def test_create_frenkel_moves_the_atom(nacl):
    out = create_frenkel(nacl, 0, [0.25, 0.25, 0.25])
    assert sorted(out.species) == sorted(nacl.species)
    np.testing.assert_allclose(out.frac_positions[-1], [0.25, 0.25, 0.25])
    with pytest.raises(IndexError):
        create_frenkel(nacl, 1000, [0.25, 0.25, 0.25])


@pytest.mark.parametrize("structure, position", [
    (from_prototype("rocksalt", ["Na", "Cl"], 5.64), [0.5, 0.5, 0.52]),
    (Crystal(["H", "Cu"], [[0, 0, 0.5], [0, 0, 0]], SKEW), [0, 0.5, 0]),
])
def test_frenkel_site_must_be_free(structure, position):
    with pytest.raises(ValueError, match="from an existing atom|too close"):
        create_frenkel(structure, 0, position)


def test_frenkel_needs_an_explicit_site(nacl):
    with pytest.raises(TypeError):
        create_frenkel(nacl, 0)  # the old default moved the atom by a random step


def test_create_schottky_removes_a_formula_unit(nacl):
    cell = make_supercell(nacl, [2, 2, 2])
    for seed in range(5):
        defect = create_schottky(cell, seed=seed)
        assert (defect.species.count("Na"), defect.species.count("Cl")) == (7, 7)
    np.testing.assert_array_equal(create_schottky(cell, seed=3).frac_positions,
                                  create_schottky(cell, seed=3).frac_positions)


def test_create_schottky_rejects_bad_input(nacl):
    na = [i for i, s in enumerate(nacl.species) if s == "Na"]
    with pytest.raises(ValueError, match="formula units"):
        create_schottky(nacl, indices=na[:1])
    with pytest.raises(ValueError, match="every atom"):
        create_schottky(nacl, indices=list(range(len(nacl))))
    with pytest.raises(TypeError):
        create_schottky(nacl, num_vacancies=2)


# --------------------------------------------------------------------------
# Antisite
# --------------------------------------------------------------------------


def test_create_antisite_swaps_species_on_fixed_sites():
    gan = from_prototype("zincblende", ["Ga", "N"], 4.5)
    out = create_antisite(gan, 0, 1)
    assert out.species == (gan.species[1], gan.species[0])
    np.testing.assert_allclose(out.positions, gan.positions)


def test_create_antisite_rejects_bad_pairs():
    gan = from_prototype("zincblende", ["Ga", "N"], 4.5)
    with pytest.raises(ValueError):
        create_antisite(gan, 0, 0)
    with pytest.raises(IndexError):
        create_antisite(gan, 0, 1000)
    cell = make_supercell(gan, [2, 1, 1])
    ga = [i for i, s in enumerate(cell.species) if s == "Ga"]
    with pytest.raises(ValueError, match="different species"):
        create_antisite(cell, ga[0], ga[1])
