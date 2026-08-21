"""Tests for crystal prototype identification."""
import json
from pathlib import Path

import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Molecule
from matsimpy.io import read, write
from matsimpy.symmetry import CrystalPrototype, get_prototype, get_prototype_info
from matsimpy.transformation.structural import make_supercell

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


def test_reference_database_parity():
    files = sorted(str(path) for path in DBS_DIR.glob("*.vasp"))
    assert len(files) == 7
    reference = json.loads(REFERENCE_FILE.read_text())
    analyzer = CrystalPrototype()
    results = analyzer.build_prototype_database(files)
    assert set(results) == set(reference)
    for key, structure_ids in reference.items():
        assert set(results[key]) == set(structure_ids)


def test_matching_pair_maps_to_same_prototype():
    base = DBS_DIR / "mp-1234353.vasp"
    variant = DBS_DIR / "mp-1234353-1.vasp"
    assert get_prototype(read(str(base))) == get_prototype(read(str(variant)))


def test_prototype_invariant_under_atom_order():
    crystal = _rocksalt()
    shuffled = Crystal(
        list(reversed(crystal.species)),
        list(reversed(crystal.frac_positions)),
        crystal.lattice,
    )
    assert get_prototype(shuffled) == get_prototype(crystal)


def test_prototype_invariant_under_supercell():
    crystal = _diamond()
    supercell = make_supercell(crystal, [2, 1, 1])
    assert get_prototype(supercell) == get_prototype(crystal)


def test_prototype_invariant_under_supercell_rocksalt():
    crystal = _rocksalt()
    supercell = make_supercell(crystal, [2, 2, 1])
    assert get_prototype(supercell) == get_prototype(crystal)


def test_suggest_element_substitutions_same_group():
    analyzer = CrystalPrototype()
    substitutions = analyzer.suggest_element_substitutions(["Li", "O"])
    assert "Li" in substitutions["Li"]
    assert "Na" in substitutions["Li"]
    assert "O" in substitutions["O"]
    assert "S" in substitutions["O"]


def test_suggest_element_substitutions_transition_metals():
    analyzer = CrystalPrototype()
    substitutions = analyzer.suggest_element_substitutions(["Fe"])
    assert "Co" in substitutions["Fe"]
    assert "Ni" in substitutions["Fe"]
    assert "Au" in substitutions["Fe"]
    assert substitutions["Fe"] == sorted(substitutions["Fe"])


def test_suggest_element_substitutions_unknown_element():
    analyzer = CrystalPrototype()
    assert analyzer.suggest_element_substitutions(["Xx"]) == {"Xx": ["Xx"]}


def test_generate_structures_from_prototype(tmp_path):
    crystal = _rocksalt()
    template = tmp_path / "template.vasp"
    write(crystal, str(template))
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"AB_cF2_Fm-3m_a_b": ["template.vasp"]}
    structures = analyzer.generate_structures_from_prototype(
        "AB_cF2_Fm-3m_a_b",
        structures_dir=str(tmp_path),
        element_substitutions={"Na": ["Na", "Li"], "Cl": ["Cl", "F"]},
        max_structures=3,
    )
    assert len(structures) == 3
    assert all(isinstance(s, Crystal) and len(s) == 2 for s in structures)
    assert set(structures[0].species) == {"Na", "Cl"}
    assert set(structures[1].species) == {"Na", "F"}
    assert set(structures[2].species) == {"Li", "Cl"}
