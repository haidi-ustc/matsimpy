"""Tests for the shared Structure behaviour: construction, exact coordinates, hashing, display."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.core.structure import Structure

SKEW = Lattice([[4.123456789, 0.1, 0.0], [0.0, 4.0, 0.0], [0.0, 0.3, 5.7]])


def _skew_crystal():
    cart = [[0.1, 0.2, 0.3], [2.3, 0.31, 3.37], [1.0, 2.0, 1.0]]
    return Crystal(["O", "Fe", "H"], cart, SKEW, coords_are_cartesian=True)


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cartesian", [False, True])
def test_init_and_internal_constructor_produce_identical_state(cartesian):
    c = Crystal(["Fe", "O"], [[0.11, 0.7, 2.2], [3.3, 0.7, 4.4]], SKEW,
                coords_are_cartesian=cartesian, pbc=[True, False, True],
                site_properties=[{"m": 1}, {"m": 2}], metadata={"k": 1})
    d = c._replace()
    assert vars(c).keys() == vars(d).keys()
    assert np.array_equal(c.cart_positions, d.cart_positions)
    assert np.array_equal(c.frac_positions, d.frac_positions)
    assert (c.pbc, c.site_properties, dict(c.metadata)) == (d.pbc, d.site_properties, dict(d.metadata))
    m = Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"q": 1}, {"q": 2}])
    assert vars(m).keys() == vars(m.copy()).keys()


def test_sort_atoms_rejects_an_unknown_method():
    with pytest.raises(ValueError):
        Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]]).sort_atoms("invalid")


# --------------------------------------------------------------------------
# Cartesian coordinates are kept bit-exact
# --------------------------------------------------------------------------


def test_cartesian_input_is_kept_bit_exact():
    cart = [[0.123456789123, 1.1, 2.2], [3.3, 0.7, 4.4]]
    assert np.array_equal(Crystal(["Fe", "O"], cart, SKEW, coords_are_cartesian=True).cart_positions, cart)


@pytest.mark.parametrize("op, rows", [
    (lambda c: c.remove_atom([1]), [0, 2]),
    (lambda c: c.sort_atoms("element"), [2, 0, 1]),  # H, O, Fe
    (lambda c: c.substitute(0, "Co"), [0, 1, 2]),
    (lambda c: c.substitute_all("O", "S"), [0, 1, 2]),
    (lambda c: c.add_atom("C", [3.3, 3.1, 0.123456789], coords_are_cartesian=True), [0, 1, 2]),
])
def test_operations_keep_cartesian_rows_bit_exact(op, rows):
    c = _skew_crystal()
    out = op(c)
    assert np.array_equal(out.cart_positions[: len(rows)], c.cart_positions[rows])


def test_added_cartesian_position_is_kept_bit_exact():
    new = [3.3, 3.1, 0.123456789]
    out = _skew_crystal().add_atom("C", new, coords_are_cartesian=True)
    assert out.cart_positions[-1].tolist() == new


def test_crystal_sites_match_the_backing_rows_exactly():
    c = _skew_crystal()
    for i, site in enumerate(c.sites):
        assert np.array_equal(site.cart_position, c.cart_positions[i])
        assert np.array_equal(site.frac_position, c.frac_positions[i])
        assert site.lattice is c.lattice
    assert c[1] == c.sites[1]


# --------------------------------------------------------------------------
# Structural hash (the calculator cache key)
# --------------------------------------------------------------------------


def test_structural_hash_is_exact_and_covers_every_calculator_input():
    c = Crystal(["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(4.0),
                site_properties=[{"magmom": 0.0}, {"magmom": 0.0}])
    base = c._structural_hash()
    assert c.copy()._structural_hash() == base
    moved = Crystal(c.species, c.cart_positions + 1e-9, c.lattice, coords_are_cartesian=True)
    assert moved._structural_hash() != base  # no rounding
    assert c.with_site_properties([{"magmom": 5.0}, {"magmom": 0.0}])._structural_hash() != base
    assert c.set_pbc([True, True, False])._structural_hash() != base


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------


def test_str_has_one_implementation():
    assert "__str__" not in vars(Crystal) and "__str__" not in vars(Molecule)
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64), site_properties=[{"m": 1}, {}])
    text = str(c)
    assert text.startswith("Crystal: NaCl\n  Sites: 2 atoms\n  PBC: [T T T]")
    assert "Fractional Coordinates" in text and "m=1" in text
    assert type(c).__str__ is Structure.__str__


def test_crystal_display_uses_unicode_units():
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
    assert "90.0°/90.0°/90.0°" in repr(c)
    assert "Volume: 179.4061 Å³" in str(c) and "g/cm³" in str(c)
    slab = Crystal(["C"], [[0, 0, 0]], Lattice.cubic(5.0), pbc=[True, True, False])
    assert "Area: 25.0000 Å²" in str(slab) and "g/cm²" in str(slab)


def test_molecule_display_uses_unicode_units():
    assert "Center of mass: (0.0000, 0.0000, 0.0000) Å" in str(Molecule(["H"], [[0, 0, 0]]))
