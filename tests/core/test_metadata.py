"""Tests for structure metadata: read-only, propagation, serialization."""

import copy
import json
import pickle

import numpy as np
import pytest
from monty.json import MontyDecoder, MontyEncoder

from matsimpy.core import Crystal, Lattice, Molecule


def _nacl():
    return Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.6),
                   metadata={"source": "test", "nested": {"k": [1]}})


def test_metadata_is_read_only_including_nested_values():
    c = _nacl()
    with pytest.raises(TypeError):
        c.metadata["source"] = "x"
    c.metadata["nested"]["k"].append(2)
    assert c.metadata["nested"]["k"] == [1]


@pytest.mark.parametrize("op", [
    lambda c: c.copy(),
    lambda c: c.set_pbc([True, True, False]),
    lambda c: c.with_site_property("q", [1, -1]),
    lambda c: c.with_metadata(extra=1),
])
def test_metadata_is_kept_when_the_atoms_do_not_change(op):
    assert op(_nacl()).metadata["source"] == "test"


@pytest.mark.parametrize("op", [
    lambda c: c.substitute(0, "K"),
    lambda c: c.remove_atom(0),
    lambda c: c.sort_atoms(),
    lambda c: c.wrap(),
    lambda c: c.add_atom("H", [0.25, 0.25, 0.25]),
])
def test_metadata_is_dropped_when_the_atoms_change(op):
    assert dict(op(_nacl()).metadata) == {}


def test_with_and_without_metadata():
    c = _nacl()
    assert dict(c.with_metadata(a=1).without_metadata("a", "nested").metadata) == {"source": "test"}
    assert dict(c.without_metadata().metadata) == {}
    with pytest.raises(TypeError):
        Crystal(["Na"], [[0, 0, 0]], Lattice.cubic(5.0), metadata={1: "x"})


@pytest.mark.parametrize("round_trip", [
    lambda o: type(o).from_dict(o.as_dict()),
    lambda o: MontyDecoder().decode(json.dumps(o, cls=MontyEncoder)),
    lambda o: pickle.loads(pickle.dumps(o)),
    copy.deepcopy,
], ids=["as_dict", "monty_json", "pickle", "deepcopy"])
def test_metadata_round_trips_exactly(round_trip):
    forces = np.array([[1 / 3, 0.0, 0.0], [0.0, -2 / 7, 0.0]])
    c = Crystal(["Fe", "Fe"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2.87)).with_metadata(
        forces=forces, energy=-1 / 3, label="frame-7")
    m = Molecule(["O", "H"], [[0, 0, 0], [0.96, 0, 0]]).with_metadata(charge=-1)
    for s in (c, m):
        r = round_trip(s)
        assert set(r.metadata) == set(s.metadata)
        for k, v in s.metadata.items():
            if isinstance(v, np.ndarray):
                assert isinstance(r.metadata[k], np.ndarray) and np.array_equal(r.metadata[k], v)
            else:
                assert r.metadata[k] == v


def test_metadata_is_not_a_calculator_input():
    c = _nacl()
    assert c.with_metadata(note="x")._structural_hash() == c._structural_hash()
