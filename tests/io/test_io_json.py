"""Tests for matsimpy.io JSON serialization (bit-exactness is in contracts/test_serialization_exact.py)."""

import json
import os

import numpy as np
import pytest

from matsimpy.core import Molecule
from matsimpy.io import from_json, read_POSCAR, to_json

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


def test_molecule_round_trip():
    m = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])
    back = from_json(json_string=to_json(m))
    assert isinstance(back, Molecule) and back.species == m.species


def test_numpy_site_properties_round_trip():
    c = read_POSCAR(os.path.join(VASP_DIR, "POSCAR_MnO"))
    c = c.with_site_property("magmom", [np.array([0, 0, 1.0])] * len(c))
    assert isinstance(from_json(to_json(c)).site_properties[0]["magmom"], np.ndarray)


def test_pymatgen_json_points_to_from_pymatgen():
    pmg = pytest.importorskip("pymatgen.io.vasp")
    s = pmg.Poscar.from_file(os.path.join(VASP_DIR, "POSCAR_MnO")).structure
    with pytest.raises(ValueError, match="from_pymatgen"):
        from_json(json.dumps(s.as_dict()))


@pytest.mark.parametrize("kwargs, error", [
    ({"json_string": "{}", "filename": "test.json"}, ValueError),
    ({}, ValueError),
    ({"filename": "nonexistent.json"}, FileNotFoundError),
])
def test_from_json_argument_errors(kwargs, error):
    with pytest.raises(error):
        from_json(**kwargs)


def test_to_json_rejects_non_structures():
    with pytest.raises(TypeError):
        to_json("not a structure")
