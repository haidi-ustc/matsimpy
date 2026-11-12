"""0.8.7: per-site column API, structure metadata, Results, single construction path."""

import copy
import json
import pickle

import numpy as np
import pytest
from monty.json import MontyDecoder, MontyEncoder

from matsimpy.calculator import LennardJones, Results
from matsimpy.core import Crystal, Lattice, Molecule


def _fe2():
    return Crystal(["Fe", "Fe"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2.87))


def _water():
    return Molecule(["O", "H", "H"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])


# ---------------------------------------------------------------- site properties
@pytest.mark.parametrize("make", [_fe2, _water])
def test_site_property_column_api(make):
    s = make()
    n = len(s)
    a = s.with_site_property("magmom", np.arange(n, dtype=float))
    assert a.site_property("magmom") == list(range(n))
    assert type(a.site_property("magmom")[0]) is float  # ndarray input -> tolist()
    b = a.with_site_property("tag", ["x"] * n)
    assert b.site_properties[0] == {"magmom": 0.0, "tag": "x"}
    assert b.without_site_property("magmom").site_property("tag") == ["x"] * n
    assert b.without_site_property("magmom", "tag").site_properties == ()
    assert s.site_properties == ()  # originals untouched
    with pytest.raises(KeyError):
        s.site_property("magmom")
    assert s.site_property("magmom", default=0.0) == [0.0] * n
    with pytest.raises(ValueError):
        s.with_site_property("magmom", [1.0])


def test_site_property_values_are_copies():
    s = _fe2().with_site_property("v", [[1, 2, 3], [4, 5, 6]])
    s.site_property("v")[0].append(99)
    assert s.site_property("v")[0] == [1, 2, 3]


def test_site_property_partial_rows():
    s = _fe2().with_site_properties([{"magmom": 2.0}, {}])
    with pytest.raises(KeyError):
        s.site_property("magmom")
    assert s.site_property("magmom", default=None) == [2.0, None]


# ---------------------------------------------------------------- metadata
def test_metadata_is_read_only_and_propagates_only_through_replace_style_ops():
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.6),
                metadata={"source": "test", "nested": {"k": [1]}})
    with pytest.raises(TypeError):
        c.metadata["source"] = "x"
    c.metadata["nested"]["k"].append(2)
    assert c.metadata["nested"]["k"] == [1]
    for kept in (c.copy(), c.set_pbc([True, True, False]), c.with_site_property("q", [1, -1]),
                 c.with_metadata(extra=1)):
        assert kept.metadata["source"] == "test"
    for dropped in (c.substitute(0, "K"), c.remove_atom(0), c.sort_atoms(), c.wrap(),
                    c.add_atom("H", [0.25, 0.25, 0.25])):
        assert dict(dropped.metadata) == {}
    assert dict(c.with_metadata(a=1).without_metadata("a", "nested").metadata) == {"source": "test"}
    assert dict(c.without_metadata().metadata) == {}
    with pytest.raises(TypeError):
        Crystal(["Na"], [[0, 0, 0]], Lattice.cubic(5.0), metadata={1: "x"})


@pytest.mark.parametrize("path", ["as_dict", "monty_json", "pickle", "deepcopy"])
def test_metadata_round_trips_exactly(path):
    forces = np.array([[1 / 3, 0.0, 0.0], [0.0, -2 / 7, 0.0]])
    c = _fe2().with_metadata(forces=forces, energy=-1 / 3, label="frame-7")
    m = _water().with_metadata(charge=-1)
    for s in (c, m):
        r = {
            "as_dict": lambda o: type(o).from_dict(o.as_dict()),
            "monty_json": lambda o: MontyDecoder().decode(json.dumps(o, cls=MontyEncoder)),
            "pickle": lambda o: pickle.loads(pickle.dumps(o)),
            "deepcopy": copy.deepcopy,
        }[path](s)
        assert set(r.metadata) == set(s.metadata)
        for k, v in s.metadata.items():
            if isinstance(v, np.ndarray):
                assert isinstance(r.metadata[k], np.ndarray) and np.array_equal(r.metadata[k], v)
            else:
                assert r.metadata[k] == v


def test_metadata_is_not_a_calculator_input():
    c = _fe2()
    assert c.with_metadata(note="x")._structural_hash() == c._structural_hash()


# ---------------------------------------------------------------- construction
def test_init_and_internal_constructor_produce_identical_state():
    lat = Lattice([[4.1, 0.3, 0.0], [0.2, 4.7, 0.0], [0.1, 0.4, 5.9]])
    for cart in (False, True):
        c = Crystal(["Fe", "O"], [[0.11, 0.7, 2.2], [3.3, 0.7, 4.4]], lat,
                    coords_are_cartesian=cart, pbc=[True, False, True],
                    site_properties=[{"m": 1}, {"m": 2}], metadata={"k": 1})
        d = c._replace()
        assert vars(c).keys() == vars(d).keys()
        assert np.array_equal(c.cart_positions, d.cart_positions)
        assert np.array_equal(c.frac_positions, d.frac_positions)
        assert (c.pbc, c.site_properties, dict(c.metadata)) == (d.pbc, d.site_properties, dict(d.metadata))
    m = Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"q": 1}, {"q": 2}])
    assert vars(m).keys() == vars(m.copy()).keys()


def test_cartesian_input_keeps_user_values_bit_exact():
    lat = Lattice([[4.1, 0.3, 0.0], [0.2, 4.7, 0.0], [0.1, 0.4, 5.9]])
    cart = [[0.123456789123, 1.1, 2.2], [3.3, 0.7, 4.4]]
    c = Crystal(["Fe", "O"], cart, lat, coords_are_cartesian=True)
    assert np.array_equal(c.cart_positions, np.array(cart))


# ---------------------------------------------------------------- Results / LRU
class _Counting(LennardJones):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.n = 0

    def _calculate(self, structure):
        self.n += 1
        return super()._calculate(structure)


def test_compute_returns_frozen_results_and_uses_lru_cache():
    calc = _Counting(sigma=2.3, epsilon=0.01)
    calc.cache_size = 2
    a, b, c = (_fe2().set_pbc(p) for p in ([True] * 3, [True, True, False], [True, False, False]))
    r = calc.compute(a)
    assert isinstance(r, Results) and r.forces.shape == (2, 3) and r.stress.shape == (3, 3)
    with pytest.raises(ValueError):
        r.forces[0, 0] = 1.0
    with pytest.raises(AttributeError):
        r.energy = 0.0
    assert np.array_equal(r.stress_voigt, calc.get_stress(a, voigt=True))
    calc.compute(b)
    assert calc.compute(a) is r and calc.n == 2      # hit
    calc.compute(c)                                  # evicts b (least recently used)
    calc.compute(b)
    assert calc.n == 4
    calc.set_parameters(epsilon=0.02)                 # parameter change clears cache
    assert calc.compute(a) is not r and calc.n == 5


def test_results_as_dict_is_independent():
    calc = LennardJones(sigma=2.3, epsilon=0.01)
    d = calc.compute(_fe2()).as_dict()
    d["forces"][0, 0] = 1e9
    assert calc.compute(_fe2()).forces[0, 0] != 1e9
