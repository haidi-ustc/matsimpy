"""Tests for crystal prototype identification."""
from pathlib import Path

import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Molecule
from matsimpy.symmetry import CrystalPrototype, get_prototype, get_prototype_info

DATA_DIR = Path(__file__).parent / "data"
DBS_DIR = DATA_DIR / "prototype_dbs"
REFERENCE_FILE = DATA_DIR / "prototype_reference.json"


def _diamond() -> Crystal:
    return from_prototype("diamond", "Si", 5.43)


def _rocksalt() -> Crystal:
    return from_prototype("rocksalt", ["Na", "Cl"], 5.64)


def test_known_prototype_diamond():
    assert get_prototype(_diamond()) == "A_cF2_Fd-3m_a"


def test_known_prototype_rocksalt():
    assert get_prototype(_rocksalt()) == "AB_cF2_Fm-3m_a_b"


def test_prototype_is_deterministic():
    crystal = _rocksalt()
    assert get_prototype(crystal) == get_prototype(crystal)


def test_molecule_raises_type_error():
    molecule = Molecule(["H", "H"], [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]])
    with pytest.raises(TypeError, match="Expected Crystal"):
        get_prototype(molecule)


def test_prototype_info_components():
    info = get_prototype_info(_rocksalt())
    assert info["prototype"] == "AB_cF2_Fm-3m_a_b"
    assert info["anonymized_formula"] == "AB"
    assert info["pearson_symbol"] == "cF2"
    assert info["space_group_symbol"] == "Fm-3m"
    assert info["wyckoff_fingerprint"] == "a_b"


def test_save_and_load_round_trip(tmp_path):
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"ABC": ["a.vasp", "b.vasp"]}
    output = tmp_path / "prototype_data.json"
    analyzer.save_prototype_data(str(output))
    reloaded = CrystalPrototype(str(output))
    assert reloaded.prototype_data == {"ABC": ["a.vasp", "b.vasp"]}


def test_get_structure_from_prototype():
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"ABC": ["a.vasp", "b.vasp"]}
    assert analyzer.get_structure_from_prototype("ABC") == "a.vasp"
    assert analyzer.get_structure_from_prototype("ABC", return_all=True) == [
        "a.vasp",
        "b.vasp",
    ]
    assert analyzer.get_structure_from_prototype("UNKNOWN") is None


def test_get_prototype_string_matches_function():
    crystal = _rocksalt()
    assert CrystalPrototype().get_prototype_string(crystal) == get_prototype(crystal)
