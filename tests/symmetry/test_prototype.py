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


def test_prototype_is_invariant_under_element_substitution():
    sodium_chloride = from_prototype("rocksalt", ["Na", "Cl"], 5.64)
    cesium_chloride = from_prototype("rocksalt", ["Cs", "Cl"], 5.64)
    magnesium_oxide = from_prototype("rocksalt", ["Mg", "O"], 5.64)

    assert get_prototype(cesium_chloride) == get_prototype(sodium_chloride)
    assert get_prototype(magnesium_oxide) == get_prototype(sodium_chloride)


def test_prototype_is_deterministic():
    crystal = _rocksalt()
    assert get_prototype(crystal) == get_prototype(crystal)


def test_molecule_raises_type_error():
    molecule = Molecule(["H", "H"], [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]])
    with pytest.raises(TypeError, match="Expected Crystal"):
        get_prototype(molecule)


@pytest.mark.parametrize("symprec", [0, -1, float("nan"), True, "1e-5"])
def test_prototype_rejects_invalid_symprec(symprec):
    with pytest.raises((TypeError, ValueError), match="symprec"):
        get_prototype(_rocksalt(), symprec=symprec)


@pytest.mark.parametrize("to_primitive", [None, 0, 1, "yes"])
def test_prototype_requires_boolean_to_primitive(to_primitive):
    with pytest.raises(TypeError, match="to_primitive"):
        get_prototype(_rocksalt(), to_primitive=to_primitive)


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


def test_explicit_missing_prototype_file_raises(tmp_path):
    missing = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="missing.json"):
        CrystalPrototype(str(missing))


def test_malformed_prototype_database_raises(tmp_path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"ABC": "a.vasp"}')

    with pytest.raises(ValueError, match="lists of structure file names"):
        CrystalPrototype(str(malformed))


def test_get_structure_from_prototype():
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"ABC": ["a.vasp", "b.vasp"]}
    assert analyzer.get_structure_from_prototype("ABC") == "a.vasp"
    assert analyzer.get_structure_from_prototype("ABC", return_all=True) == [
        "a.vasp",
        "b.vasp",
    ]
    assert analyzer.get_structure_from_prototype("UNKNOWN") is None


def test_get_structure_from_empty_prototype_entry_returns_none():
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"ABC": []}

    assert analyzer.get_structure_from_prototype("ABC") is None


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


def test_build_prototype_database_merges_existing_entries():
    source = DBS_DIR / "mp-1234325.vasp"
    analyzer = CrystalPrototype()
    prototype = get_prototype(read(str(source)))
    analyzer.prototype_data = {prototype: ["existing.vasp"]}

    analyzer.build_prototype_database([str(source)])

    assert analyzer.prototype_data[prototype] == [
        "existing.vasp",
        "mp-1234325.vasp",
    ]


def test_build_prototype_database_propagates_file_errors(tmp_path):
    analyzer = CrystalPrototype()
    missing = tmp_path / "missing.vasp"

    with pytest.raises(FileNotFoundError, match="missing.vasp"):
        analyzer.build_prototype_database([str(missing)])


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


def test_generate_structures_applies_substitutions_simultaneously(tmp_path):
    crystal = Crystal(
        ["Na", "Li"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
        _rocksalt().lattice,
    )
    template = tmp_path / "template.vasp"
    write(crystal, str(template))
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"prototype": [template.name]}

    structures = analyzer.generate_structures_from_prototype(
        "prototype",
        structures_dir=str(tmp_path),
        element_substitutions={"Na": ["Li"], "Li": ["K"]},
    )

    assert structures[0].species == ("Li", "K")


def test_generate_structures_honors_zero_limit(tmp_path):
    template = tmp_path / "template.vasp"
    write(_rocksalt(), str(template))
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"prototype": [template.name]}

    structures = analyzer.generate_structures_from_prototype(
        "prototype",
        structures_dir=str(tmp_path),
        element_substitutions={"Na": ["Na", "Li"], "Cl": ["Cl", "F"]},
        max_structures=0,
    )

    assert structures == []


def test_generate_structures_rejects_elements_absent_from_template(tmp_path):
    template = tmp_path / "template.vasp"
    write(_rocksalt(), str(template))
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"prototype": [template.name]}

    with pytest.raises(ValueError, match="not present.*Xe"):
        analyzer.generate_structures_from_prototype(
            "prototype",
            structures_dir=str(tmp_path),
            element_substitutions={"Xe": ["Kr"]},
        )


@pytest.mark.parametrize("invalid_substitutes", [[], "Li"])
def test_generate_structures_rejects_invalid_substitution_options(
    tmp_path, invalid_substitutes
):
    template = tmp_path / "template.vasp"
    write(_rocksalt(), str(template))
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"prototype": [template.name]}

    with pytest.raises((TypeError, ValueError), match="substitutions for Na"):
        analyzer.generate_structures_from_prototype(
            "prototype",
            structures_dir=str(tmp_path),
            element_substitutions={"Na": invalid_substitutes, "Cl": ["Cl"]},
        )


@pytest.mark.parametrize("max_structures", [-1, 1.5, True])
def test_generate_structures_rejects_invalid_limits(tmp_path, max_structures):
    template = tmp_path / "template.vasp"
    write(_rocksalt(), str(template))
    analyzer = CrystalPrototype()
    analyzer.prototype_data = {"prototype": [template.name]}

    with pytest.raises((TypeError, ValueError), match="max_structures"):
        analyzer.generate_structures_from_prototype(
            "prototype",
            structures_dir=str(tmp_path),
            element_substitutions={"Na": ["Na"], "Cl": ["Cl"]},
            max_structures=max_structures,
        )
