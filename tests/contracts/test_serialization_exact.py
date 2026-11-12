"""Serialization contract (0.8.4): every lossless path is bit-exact.

as_dict/from_dict, MontyEncoder JSON, the io JSON format, copy(), pickle and
deepcopy must reproduce lattice, fractional *and* Cartesian coordinates,
PBC and per-site properties with ``np.array_equal`` — not ``allclose``.
(Text formats such as CIF/PDB/XYZ have fixed precision by design and are
out of scope.)
"""

import copy
import json
import pickle

import numpy as np
import pytest
from monty.json import MontyDecoder, MontyEncoder

from matsimpy import io as mio
from matsimpy.core import Crystal, Lattice, Molecule, Trajectory


def _random_crystal(rng, cartesian):
    params = rng.uniform([2.5, 2.5, 2.5, 60, 60, 60], [9.0, 9.0, 9.0, 120, 120, 120])
    try:
        lat = Lattice.from_parameters(*params)
    except ValueError:  # geometrically impossible angle triple
        lat = Lattice.from_parameters(*params[:3], 90, 90, 90)
    n = int(rng.integers(1, 6))
    species = list(rng.choice(["H", "C", "O", "Fe", "Na", "Cl"], n))
    props = [{"magmom": float(rng.normal()), "v": rng.normal(size=3).tolist()} for _ in range(n)]
    if cartesian:
        pos = rng.normal(size=(n, 3)) * 5.0
    else:
        pos = rng.uniform(-0.5, 1.5, size=(n, 3))
    pbc = tuple(bool(x) for x in rng.integers(0, 2, 3))
    return Crystal(species, pos, lat, pbc=pbc, coords_are_cartesian=cartesian, site_properties=props)


def _assert_same(a, b):
    assert type(a) is type(b)
    if isinstance(a, Trajectory):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            _assert_same(x, y)
        assert [dict(x.metadata) for x in a] == [dict(y.metadata) for y in b]
        assert np.array_equal(a.base_positions, b.base_positions)
        return
    assert a.species == b.species
    assert a.site_properties == b.site_properties
    if isinstance(a, Crystal):
        assert np.array_equal(a.lattice.matrix, b.lattice.matrix)
        assert np.array_equal(a.frac_positions, b.frac_positions)
        assert np.array_equal(a.cart_positions, b.cart_positions)
        assert a.pbc == b.pbc
    else:
        assert np.array_equal(a.positions, b.positions)


ROUND_TRIPS = {
    "as_dict": lambda o: type(o).from_dict(o.as_dict()),
    "monty_json": lambda o: MontyDecoder().decode(json.dumps(o, cls=MontyEncoder)),
    "pickle": lambda o: pickle.loads(pickle.dumps(o)),
    "deepcopy": copy.deepcopy,
}


@pytest.mark.parametrize("path", sorted(ROUND_TRIPS))
@pytest.mark.parametrize("cartesian", [False, True], ids=["frac", "cart"])
def test_crystal_round_trips_are_bit_exact(path, cartesian):
    rng = np.random.default_rng(84 + cartesian)
    for _ in range(50):
        c = _random_crystal(rng, cartesian)
        _assert_same(c, ROUND_TRIPS[path](c))
        _assert_same(c, c.copy())


@pytest.mark.parametrize("path", sorted(ROUND_TRIPS))
def test_molecule_and_trajectory_round_trips_are_bit_exact(path):
    rng = np.random.default_rng(7)
    mol = Molecule(["O", "H", "H"], rng.normal(size=(3, 3)), site_properties=[{"q": -2 / 3}, {"q": 1 / 3}, {"q": 1 / 3}])
    _assert_same(mol, ROUND_TRIPS[path](mol))
    frames = [_random_crystal(rng, False) for _ in range(1)]
    traj = Trajectory([frames[0].with_metadata(e=-1 / 3), frames[0].with_metadata(e=-2 / 7)],
                      base_positions=rng.random((len(frames[0]), 3)))
    _assert_same(traj, ROUND_TRIPS[path](traj))


def test_lattice_as_dict_keeps_full_precision():
    lat = Lattice.from_parameters(4.123456789123457, 5.3, 6.7, 81.123456789, 97.3, 104.987654321)
    assert np.array_equal(Lattice.from_dict(lat.as_dict()).matrix, lat.matrix)


def test_io_json_file_round_trip_is_bit_exact(tmp_path):
    rng = np.random.default_rng(3)
    for cartesian in (False, True):
        c = _random_crystal(rng, cartesian)
        path = tmp_path / f"c{int(cartesian)}.json"
        mio.write(c, str(path))
        _assert_same(c, mio.read(str(path)))


def test_legacy_dict_without_cart_positions_still_loads():
    c = _random_crystal(np.random.default_rng(5), True)
    d = c.as_dict()
    d.pop("cart_positions", None)
    old = Crystal.from_dict(d)  # 0.8.3-style payload
    assert np.array_equal(old.frac_positions, c.frac_positions)
    assert np.allclose(old.cart_positions, c.cart_positions, atol=1e-12, rtol=0)


@pytest.mark.parametrize("op", ["remove_atom", "sort_atoms"])
def test_per_atom_metadata_ops_read_site_properties_a_bounded_number_of_times(op, monkeypatch):
    """0.8.3 deep-copied every site's properties once *per atom* (O(N^2))."""
    n = 64
    c = Crystal(["Si"] * n, np.random.default_rng(1).random((n, 3)), Lattice.cubic(20.0),
                site_properties=[{"m": float(i)} for i in range(n)])
    calls = {"n": 0}
    original = Crystal.site_properties.fget

    def counting(self):
        calls["n"] += 1
        return original(self)

    monkeypatch.setattr(Crystal, "site_properties", property(counting))
    out = c.remove_atom([0]) if op == "remove_atom" else c.sort_atoms()
    assert calls["n"] <= 4
    assert len(out) in (n - 1, n)
