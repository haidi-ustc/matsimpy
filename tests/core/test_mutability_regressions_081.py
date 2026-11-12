"""Regression tests for the 0.8.1 mutability fixes.

Each test reproduces a mutation path that was open in 0.8.0 and silently
desynchronised an "immutable" object from its derived caches.
"""

import copy
import pickle

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule, Trajectory
from matsimpy.core.site import CrystalSite


def _crystal(props=None):
    return Crystal(
        ["Fe", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(4.0),
        site_properties=props,
    )


# --------------------------------------------------------------------------
# Lattice
# --------------------------------------------------------------------------

def test_lattice_matrix_cannot_be_reassigned():
    lat = Lattice.cubic(4.0)
    with pytest.raises(AttributeError):
        lat.matrix = np.eye(3)
    assert not hasattr(lat, "lattice_vectors")  # duplicate alias removed in 0.9.0


@pytest.mark.parametrize("accessor", ["matrix", "inv_matrix"])
def test_lattice_arrays_cannot_be_reopened_for_writing(accessor):
    lat = Lattice.cubic(4.0)
    arr = getattr(lat, accessor)
    with pytest.raises(ValueError):
        arr.flags.writeable = True
    # matrix and cached inverse stay consistent to machine precision
    assert np.array_equal(lat.matrix @ lat.inv_matrix, np.eye(3))


@pytest.mark.parametrize("clone", [copy.deepcopy, lambda o: pickle.loads(pickle.dumps(o))])
def test_lattice_stays_frozen_after_pickle_and_deepcopy(clone):
    lat = clone(Lattice.cubic(3.0))
    with pytest.raises(ValueError):
        lat.matrix.flags.writeable = True
    assert np.array_equal(lat.matrix, Lattice.cubic(3.0).matrix)


# --------------------------------------------------------------------------
# Crystal / Molecule
# --------------------------------------------------------------------------

def test_crystal_lattice_and_pbc_are_read_only():
    c = _crystal()
    with pytest.raises(AttributeError):
        c.lattice = Lattice.cubic(8.0)
    with pytest.raises(AttributeError):
        c.pbc = (True, True, False)
    assert c.set_pbc([True, True, False]).pbc == (True, True, False)
    assert c.pbc == (True, True, True)


@pytest.mark.parametrize("clone", [copy.deepcopy, lambda o: pickle.loads(pickle.dumps(o))])
def test_crystal_arrays_stay_frozen_after_pickle_and_deepcopy(clone):
    c = clone(_crystal())
    for arr in (c.positions, c.frac_positions, c.cart_positions):
        with pytest.raises(ValueError):
            arr.flags.writeable = True


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _crystal([{"m": 1.0}, {"m": 2.0}]),
        lambda: Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"m": 1.0}, {"m": 2.0}]),
    ],
)
def test_site_properties_are_read_only(factory):
    """The in-place setter (deprecated in 0.8.1) was removed in 0.8.6."""
    s = factory()
    with pytest.raises(AttributeError):
        s.site_properties = [{"m": 9.0}, {"m": 9.0}]
    assert [site.properties["m"] for site in s] == [1.0, 2.0]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _crystal([{"m": 1.0}, {"m": 2.0}]),
        lambda: Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"m": 1.0}, {"m": 2.0}]),
    ],
)
def test_with_site_properties_returns_new_object(factory):
    s = factory()
    new = s.with_site_properties([{"m": 5.0}, {"m": 6.0}])
    assert type(new) is type(s)
    assert s.site_properties == ({"m": 1.0}, {"m": 2.0})
    assert new.site_properties == ({"m": 5.0}, {"m": 6.0})
    assert np.array_equal(new.positions, s.positions)
    assert s.with_site_properties(None).site_properties == ()


def test_copy_is_bit_exact():
    lat = Lattice([[4.123456789123, 0.1, 0.0], [0.0, 4.0, 0.0], [0.0, 0.3, 5.7]])
    c = Crystal(
        ["Fe", "O"],
        [[0.1, 0.2, 0.3], [0.3, 0.31, 0.37]],
        lat,
        coords_are_cartesian=True,
        pbc=[True, True, False],
        site_properties=[{"m": 1}, {"m": 2}],
    )
    d = c.copy()
    assert d is not c
    assert np.array_equal(d.lattice.matrix, c.lattice.matrix)
    assert np.array_equal(d.cart_positions, c.cart_positions)
    assert np.array_equal(d.frac_positions, c.frac_positions)
    assert d.pbc == c.pbc and d.site_properties == c.site_properties


def test_calculator_fingerprint_is_exact_and_complete():
    c = _crystal([{"magmom": 0.0}, {"magmom": 0.0}])
    base = c._structural_hash()
    assert base == c.copy()._structural_hash()
    # sub-rounding displacement (0.8.0 rounded positions to 7 d.p.)
    moved = Crystal(c.species, c.cart_positions + 1e-9, c.lattice, coords_are_cartesian=True)
    assert moved._structural_hash() != base
    # magnetic configuration and PBC are calculator inputs too
    assert c.with_site_properties([{"magmom": 5.0}, {"magmom": 0.0}])._structural_hash() != base
    assert c.set_pbc([True, True, False])._structural_hash() != base


@pytest.mark.parametrize("attr", ["lattice", "specie", "position", "properties", "anything"])
def test_crystal_site_is_immutable(attr):
    """0.8.x sites had setters (lattice, specie, position, properties); 0.9.0 sites are frozen."""
    site = CrystalSite([0.5, 0.5, 0.5], "Fe", Lattice.cubic(2.0))
    with pytest.raises(AttributeError):
        setattr(site, attr, None)
    for arr in (site.position, site.frac_position, site.cart_position):
        with pytest.raises(ValueError):
            arr[0] = 9.0
    assert np.array_equal(site.position, site.cart_position)  # position is always Cartesian
    assert np.allclose(site.cart_position, [1.0, 1.0, 1.0])


@pytest.mark.parametrize("clone", [copy.deepcopy, lambda o: pickle.loads(pickle.dumps(o))])
def test_crystal_site_clone_is_equal_and_frozen(clone):
    site = CrystalSite([0.5, 0.25, 0.0], "Fe", Lattice.cubic(2.0), {"m": [1]})
    other = clone(site)
    assert other == site and other is not site
    with pytest.raises(AttributeError):
        other.specie = "O"
    with pytest.raises(ValueError):
        other.frac_position.flags.writeable = True


# --------------------------------------------------------------------------
# Trajectory
# --------------------------------------------------------------------------

def test_trajectory_is_immutable():
    frame = _crystal([{"m": 1.0}, {"m": 2.0}])
    traj = Trajectory([frame.with_metadata(e={"v": 1}), frame.with_metadata(e={"v": 2})],
                      base_positions=[[0, 0, 0], [1, 1, 1]])
    traj[0].metadata["e"]["v"] = 99
    assert traj[0].metadata["e"]["v"] == 1
    with pytest.raises(ValueError):
        traj.base_positions[0, 0] = 5.0
    with pytest.raises(AttributeError):
        traj.constant_lattice = True
    frames = list(traj)  # iteration yields copies, never the internal frames
    assert all(f is not g for f, g in zip(frames, traj._frames))


def test_trajectory_pickle_roundtrip_stays_frozen():
    traj = Trajectory([_crystal()], base_positions=[[0, 0, 0], [1, 1, 1]])
    restored = pickle.loads(pickle.dumps(traj))
    with pytest.raises(ValueError):
        restored.base_positions.flags.writeable = True


# --------------------------------------------------------------------------
# Per-atom metadata propagation (crashed in 0.8.0 whenever site_properties set)
# --------------------------------------------------------------------------

def _with_props():
    c = Crystal(["Fe", "O", "O"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.2, 0.3, 0.1]],
                Lattice.cubic(4.0), site_properties=[{"m": 1}, {"m": 2}, {"m": 3}])
    m = Molecule(["O", "H", "C"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
                 site_properties=[{"m": 1}, {"m": 2}, {"m": 3}])
    return [c, m]


@pytest.mark.parametrize("idx", [0, 1])
def test_remove_atom_filters_site_properties(idx):
    s = _with_props()[idx]
    r = s.remove_atom([1])
    assert [p["m"] for p in r.site_properties] == [1, 3]
    assert r.species == (s.species[0], s.species[2])
    assert [p["m"] for p in s.site_properties] == [1, 2, 3]  # original untouched


@pytest.mark.parametrize("idx", [0, 1])
def test_sort_atoms_reorders_site_properties(idx):
    s = _with_props()[idx]
    r = s.sort_atoms("element")
    by_species = dict(zip(s.species, (p["m"] for p in s.site_properties)))
    assert all(by_species[sp] == p["m"] for sp, p in zip(r.species, r.site_properties)
               if s.species.count(sp) == 1)
    assert sorted(p["m"] for p in r.site_properties) == [1, 2, 3]
