"""Immutability of structures, lattices and sites.

Every "mutation" returns a new object and leaves the input untouched; attributes cannot
be reassigned and arrays cannot be made writable, also after pickle and deepcopy.
"""

import copy
import pickle

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.core.site import CrystalSite
from matsimpy.transformation import make_supercell, perturb_positions

CLONES = [copy.deepcopy, lambda o: pickle.loads(pickle.dumps(o))]


def _nacl():
    return Crystal(["Na", "Cl"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64),
                   site_properties=[{"m": 1.0}, {"m": 2.0}])


def _water():
    return Molecule(["O", "H", "H"], [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]],
                    site_properties=[{"m": 1.0}, {"m": 2.0}, {"m": 3.0}])


# --------------------------------------------------------------------------
# Operations return new objects
# --------------------------------------------------------------------------


@pytest.mark.parametrize("make, op", [
    (_nacl, lambda s: s.add_atom("H", [0.1, 0.0, 0.0])),
    (_nacl, lambda s: s.remove_atom(0)),
    (_nacl, lambda s: s.substitute(0, "K")),
    (_nacl, lambda s: s.substitute_all("Na", "K")),
    (_nacl, lambda s: s.sort_atoms("alphabet")),
    (_nacl, lambda s: s.wrap()),
    (_nacl, lambda s: s.set_pbc([True, True, False])),
    (_nacl, lambda s: s.with_site_properties([{"m": 5.0}, {"m": 6.0}])),
    (_nacl, lambda s: make_supercell(s, [2, 2, 2])),
    (_nacl, lambda s: perturb_positions(s, 0.1, seed=42)),
    (_nacl, lambda s: s.add_atom("H", [0.1, 0.0, 0.0]).substitute(0, "K").sort_atoms("element")),
    (_water, lambda s: s.add_atom("H", [2.0, 0.0, 0.0])),
    (_water, lambda s: s.remove_atom(0)),
    (_water, lambda s: s.substitute(0, "N")),
    (_water, lambda s: s.translate([1.0, 0.0, 0.0])),
    (_water, lambda s: s.rotate(90, [0, 0, 1])),
    (_water, lambda s: s.to_crystal()),
    (_water, lambda s: perturb_positions(s, 0.1, seed=42)),
])
def test_operations_return_a_new_object_and_leave_the_input_unchanged(make, op):
    s = make()
    before = (s.species, s.positions.copy(), s.site_properties, getattr(s, "pbc", None))
    out = op(s)
    assert out is not s
    assert s.species == before[0]
    assert np.array_equal(s.positions, before[1])
    assert s.site_properties == before[2]
    assert getattr(s, "pbc", None) == before[3]


def test_cached_formula_and_composition_never_change():
    c = _nacl()
    formula, composition = c.formula, c.composition
    c.add_atom("H", [0.1, 0.0, 0.0])
    assert c.formula == formula
    assert c.composition is composition


# --------------------------------------------------------------------------
# Attributes cannot be reassigned
# --------------------------------------------------------------------------


@pytest.mark.parametrize("make, attr, value", [
    (_nacl, "positions", [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
    (_nacl, "species", ["K", "Br"]),
    (_nacl, "lattice", Lattice.cubic(8.0)),
    (_nacl, "pbc", (True, True, False)),
    (_nacl, "site_properties", [{"m": 9.0}, {"m": 9.0}]),
    (_water, "site_properties", [{"m": 9.0}] * 3),
    (lambda: Lattice.cubic(4.0), "matrix", np.eye(3)),
    (lambda: Lattice.cubic(4.0), "_matrix", np.eye(3)),
])
def test_attributes_cannot_be_reassigned(make, attr, value):
    with pytest.raises(AttributeError):
        setattr(make(), attr, value)


def test_lattice_has_no_duplicate_vector_alias():
    assert not hasattr(Lattice.cubic(4.0), "lattice_vectors")


# --------------------------------------------------------------------------
# Arrays cannot be made writable
# --------------------------------------------------------------------------


@pytest.mark.parametrize("make", [_nacl, _water])
def test_internal_coordinates_are_read_only(make):
    with pytest.raises(ValueError):
        make()._coords[0, 0] = 0.25


@pytest.mark.parametrize("clone", [lambda o: o] + CLONES, ids=["original", "deepcopy", "pickle"])
def test_lattice_arrays_stay_frozen(clone):
    lat = clone(Lattice.cubic(4.0))
    for arr in (lat.matrix, lat.inv_matrix):
        with pytest.raises(ValueError):
            arr.flags.writeable = True
    assert np.array_equal(lat.matrix @ lat.inv_matrix, np.eye(3))


@pytest.mark.parametrize("clone", [lambda o: o] + CLONES, ids=["original", "deepcopy", "pickle"])
def test_crystal_arrays_stay_frozen(clone):
    c = clone(_nacl())
    for arr in (c.positions, c.frac_positions, c.cart_positions):
        with pytest.raises(ValueError):
            arr.flags.writeable = True


# --------------------------------------------------------------------------
# Sites
# --------------------------------------------------------------------------


@pytest.mark.parametrize("attr", ["lattice", "specie", "position", "properties", "anything"])
def test_crystal_site_is_frozen(attr):
    site = CrystalSite([0.5, 0.5, 0.5], "Fe", Lattice.cubic(2.0))
    with pytest.raises(AttributeError):
        setattr(site, attr, None)
    for arr in (site.position, site.frac_position, site.cart_position):
        with pytest.raises(ValueError):
            arr[0] = 9.0
    assert np.array_equal(site.position, site.cart_position)  # position is always Cartesian


@pytest.mark.parametrize("clone", CLONES, ids=["deepcopy", "pickle"])
def test_crystal_site_clone_is_equal_and_frozen(clone):
    site = CrystalSite([0.5, 0.25, 0.0], "Fe", Lattice.cubic(2.0), {"m": [1]})
    other = clone(site)
    assert other == site and other is not site
    with pytest.raises(AttributeError):
        other.specie = "O"
    with pytest.raises(ValueError):
        other.frac_position.flags.writeable = True
