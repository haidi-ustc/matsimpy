"""Crystal prototype identifiers and the read-only prototype database.

Expected identifiers of real structures (pymatgen 2026.10.24 test files, see
tests/calculator/fixtures/vasp/PROVENANCE.md) are textbook Wyckoff sites,
e.g. antifluorite Li2O: O 4a, Li 8c.  The identifiers also match branch1 and
its CrystalPrototype reference database (checked when porting).
"""

import os
import pickle
from dataclasses import FrozenInstanceError

import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Molecule
from matsimpy.io import read
from matsimpy.symmetry import PrototypeDatabase, PrototypeInfo, get_prototype, get_prototype_info
from matsimpy.transformation.structural import make_supercell

pytest.importorskip("spglib")

VASP = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


def _real(name):
    return read(os.path.join(VASP, name))


def _rocksalt(elements=("Na", "Cl")):
    return from_prototype("rocksalt", list(elements), 5.64)


@pytest.mark.parametrize(
    ("fixture", "symprec", "expected"),
    [
        ("POSCAR_C2", 1e-5, "A_cF2_Fd-3m_a"),  # diamond, C 8a
        ("POSCAR_Li2O", 1e-5, "AB2_cF3_Fm-3m_a_c"),  # antifluorite, 96-atom supercell
        ("POSCAR_MnO", 1e-3, "AB_cF2_Fm-3m_a_b"),  # rocksalt
        ("POSCAR_bcc", 1e-5, "A_cI1_Im-3m_a"),  # conventional bcc cell
        ("POSCAR_fcc", 1e-5, "A_cF1_Fm-3m_a"),  # 8-atom fcc supercell
        ("POSCAR.AlN", 1e-5, "AB_hP4_P6_3mc_b_b"),  # wurtzite, Al 2b, N 2b
        ("POSCAR_Al12O18", 1e-3, "A2B3_hR10_R-3c_c_e"),  # corundum, Al 12c, O 18e
    ],
)
def test_real_structures_have_textbook_prototypes(fixture, symprec, expected):
    assert get_prototype(_real(fixture), symprec=symprec) == expected


def test_default_symprec_is_tight_for_six_digit_coordinates():
    """1e-5 (branch1's default, kept for identifier compatibility) sees the
    rounding noise of a real POSCAR as a lower symmetry."""
    assert get_prototype(_real("POSCAR_MnO")) == "AB_tI2_I4mm_a_a"


def test_prototype_info_components():
    info = get_prototype_info(_real("POSCAR_Li2O"))
    assert info == PrototypeInfo("AB2", "cF3", "Fm-3m", "a_c", "AB2_cF3_Fm-3m_a_c")
    assert info.as_dict()["pearson_symbol"] == "cF3"
    with pytest.raises(FrozenInstanceError):
        info.prototype = "x"


def test_conventional_cell_gives_the_crystallographic_pearson_symbol():
    assert get_prototype_info(_real("POSCAR_Li2O"), to_primitive=False).pearson_symbol == "cF12"
    assert get_prototype_info(_rocksalt(), to_primitive=False).pearson_symbol == "cF8"


def test_invariant_under_element_substitution():
    assert {get_prototype(_rocksalt(pair)) for pair in [("Na", "Cl"), ("Cs", "Cl"), ("Mg", "O")]} == {
        "AB_cF2_Fm-3m_a_b"
    }


def test_invariant_under_atom_order_and_supercell():
    crystal = _rocksalt()
    shuffled = Crystal(list(reversed(crystal.species)), list(reversed(crystal.frac_positions)), crystal.lattice)
    assert get_prototype(shuffled) == get_prototype(crystal)
    assert get_prototype(make_supercell(crystal, [2, 2, 1])) == get_prototype(crystal)
    diamond = _real("POSCAR_C2")
    assert get_prototype(make_supercell(diamond, [2, 1, 1])) == get_prototype(diamond)


def test_molecule_raises_type_error():
    with pytest.raises(TypeError, match="Expected Crystal"):
        get_prototype(Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]]))


def test_slab_raises_value_error():
    slab = _rocksalt().set_pbc([True, True, False])
    with pytest.raises(ValueError, match="3D-periodic"):
        get_prototype(slab)


@pytest.mark.parametrize("symprec", [0, -1, float("nan"), True, "1e-5"])
def test_rejects_invalid_symprec(symprec):
    with pytest.raises((TypeError, ValueError), match="symprec"):
        get_prototype(_rocksalt(), symprec=symprec)


@pytest.mark.parametrize("to_primitive", [None, 0, 1, "yes"])
def test_requires_boolean_to_primitive(to_primitive):
    with pytest.raises(TypeError, match="to_primitive"):
        get_prototype(_rocksalt(), to_primitive=to_primitive)


def test_missing_spglib_raises_import_error(monkeypatch):
    import matsimpy.symmetry.spacegroup as spacegroup

    monkeypatch.setattr(spacegroup, "spglib", None)
    with pytest.raises(ImportError, match="pip install spglib"):
        get_prototype(_rocksalt())


class TestPrototypeDatabase:
    def test_is_a_read_only_mapping(self):
        db = PrototypeDatabase({"ABC": ["a.vasp", "b.vasp"]})
        assert db["ABC"] == ("a.vasp", "b.vasp")
        assert "ABC" in db and len(db) == 1 and list(db) == ["ABC"]
        with pytest.raises(TypeError):
            db["XYZ"] = ["c.vasp"]
        with pytest.raises(AttributeError, match="immutable"):
            db._entries = {}
        with pytest.raises(TypeError):
            hash(db)

    @pytest.mark.parametrize("data", [{"ABC": "a.vasp"}, {"ABC": []}, {"ABC": [""]}, {1: ["a"]}, ["ABC"]])
    def test_rejects_malformed_data(self, data):
        with pytest.raises(ValueError, match="lists of structure ids"):
            PrototypeDatabase(data)

    def test_json_round_trip(self, tmp_path):
        db = PrototypeDatabase({"ABC": ["a.vasp", "b.vasp"]})
        path = tmp_path / "prototypes.json"
        db.to_json(path)
        assert PrototypeDatabase.from_json(path) == db

    def test_missing_and_malformed_files_raise(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="missing.json"):
            PrototypeDatabase.from_json(tmp_path / "missing.json")
        malformed = tmp_path / "malformed.json"
        malformed.write_text('{"ABC": "a.vasp"}')
        with pytest.raises(ValueError, match="lists of structure ids"):
            PrototypeDatabase.from_json(malformed)

    def test_merge_returns_a_new_database_and_keeps_order(self):
        db = PrototypeDatabase({"ABC": ["a.vasp"]})
        merged = db.merge({"ABC": ["b.vasp", "a.vasp"], "XYZ": ["c.vasp"]})
        assert merged.as_dict() == {"ABC": ["a.vasp", "b.vasp"], "XYZ": ["c.vasp"]}
        assert db.as_dict() == {"ABC": ["a.vasp"]}

    def test_with_structures(self):
        db = PrototypeDatabase().with_structures(
            [("C2", _real("POSCAR_C2")), ("Li2O", _real("POSCAR_Li2O")), ("NaCl", _rocksalt())]
        )
        assert db.as_dict() == {
            "A_cF2_Fd-3m_a": ["C2"],
            "AB2_cF3_Fm-3m_a_c": ["Li2O"],
            "AB_cF2_Fm-3m_a_b": ["NaCl"],
        }

    def test_pickle(self):
        db = PrototypeDatabase({"ABC": ["a.vasp"]})
        assert pickle.loads(pickle.dumps(db)) == db


class TestBuilders:
    FILES = ["POSCAR_C2", "POSCAR_Li2O", "POSCAR_MnO", "POSCAR_bcc"]

    def test_build_prototype_database_from_files(self):
        from matsimpy.builders.bulk import build_prototype_database

        db = build_prototype_database([os.path.join(VASP, f) for f in self.FILES], symprec=1e-3)
        assert db.as_dict() == {
            "A_cF2_Fd-3m_a": ["POSCAR_C2"],
            "AB2_cF3_Fm-3m_a_c": ["POSCAR_Li2O"],
            "AB_cF2_Fm-3m_a_b": ["POSCAR_MnO"],
            "A_cI1_Im-3m_a": ["POSCAR_bcc"],
        }

    def test_build_merges_into_an_existing_database(self):
        from matsimpy.builders.bulk import build_prototype_database

        existing = PrototypeDatabase({"A_cF2_Fd-3m_a": ["existing.vasp"]})
        db = build_prototype_database([os.path.join(VASP, "POSCAR_C2")], database=existing)
        assert db["A_cF2_Fd-3m_a"] == ("existing.vasp", "POSCAR_C2")
        assert existing["A_cF2_Fd-3m_a"] == ("existing.vasp",)

    def test_build_propagates_file_errors(self, tmp_path):
        from matsimpy.builders.bulk import build_prototype_database

        with pytest.raises(FileNotFoundError, match="missing.vasp"):
            build_prototype_database([tmp_path / "missing.vasp"])

    def _db(self):
        return PrototypeDatabase({"AB_cF2_Fm-3m_a_b": ["POSCAR_MnO"]})

    def test_structures_from_prototype(self):
        from matsimpy.builders.bulk import structures_from_prototype

        structures = structures_from_prototype(
            self._db(), "AB_cF2_Fm-3m_a_b", VASP,
            element_substitutions={"Mn": ["Mn", "Ni"], "O": ["O", "S"]}, max_structures=3,
        )
        assert [sorted(s.species) for s in structures] == [["Mn", "O"], ["Mn", "S"], ["Ni", "O"]]
        assert all(get_prototype(s, symprec=1e-3) == "AB_cF2_Fm-3m_a_b" for s in structures)

    def test_substitutions_are_simultaneous(self):
        from matsimpy.builders.bulk import structures_from_prototype

        (swapped,) = structures_from_prototype(
            self._db(), "AB_cF2_Fm-3m_a_b", VASP, element_substitutions={"Mn": ["O"], "O": ["Mn"]}
        )
        template = _real("POSCAR_MnO")
        assert list(swapped.species) == [{"Mn": "O", "O": "Mn"}[s] for s in template.species]

    def test_default_substitutions_use_suggestions(self):
        from matsimpy.builders.bulk import structures_from_prototype, suggest_element_substitutions

        options = suggest_element_substitutions(["Mn", "O"])
        structures = structures_from_prototype(self._db(), "AB_cF2_Fm-3m_a_b", VASP, max_structures=5)
        assert len(structures) == 5
        assert all(set(s.species) <= set(options["Mn"]) | set(options["O"]) for s in structures)

    def test_zero_limit(self):
        from matsimpy.builders.bulk import structures_from_prototype

        assert structures_from_prototype(self._db(), "AB_cF2_Fm-3m_a_b", VASP, max_structures=0) == []

    @pytest.mark.parametrize(
        ("kwargs", "error", "match"),
        [
            ({"element_substitutions": {"Xe": ["Kr"]}}, ValueError, "not present.*Xe"),
            ({"element_substitutions": {"Mn": []}}, ValueError, "substitutions for Mn"),
            ({"element_substitutions": {"Mn": "Ni"}}, TypeError, "substitutions for Mn"),
            ({"element_substitutions": {"Mn": ["Qq"]}}, ValueError, "invalid element"),
            ({"max_structures": -1}, ValueError, "max_structures"),
            ({"max_structures": 1.5}, TypeError, "max_structures"),
            ({"max_structures": True}, TypeError, "max_structures"),
        ],
    )
    def test_invalid_arguments(self, kwargs, error, match):
        from matsimpy.builders.bulk import structures_from_prototype

        with pytest.raises(error, match=match):
            structures_from_prototype(self._db(), "AB_cF2_Fm-3m_a_b", VASP, **kwargs)

    def test_unknown_prototype_and_missing_template(self, tmp_path):
        from matsimpy.builders.bulk import structures_from_prototype

        with pytest.raises(ValueError, match="No template structure"):
            structures_from_prototype(self._db(), "UNKNOWN", VASP)
        with pytest.raises(FileNotFoundError, match="Template structure file not found"):
            structures_from_prototype(self._db(), "AB_cF2_Fm-3m_a_b", tmp_path)


class TestSuggestions:
    def test_same_group(self):
        from matsimpy.builders.bulk import suggest_element_substitutions

        options = suggest_element_substitutions(["Li", "O"])
        assert {"Li", "Na", "K"} <= set(options["Li"])
        assert {"O", "S", "Se"} <= set(options["O"])
        assert "Fr" not in options["Li"]  # period 7

    def test_transition_metals(self):
        from matsimpy.builders.bulk import suggest_element_substitutions

        options = suggest_element_substitutions(["Fe"])["Fe"]
        assert {"Co", "Ni", "Au"} <= set(options)
        assert options == sorted(options)

    def test_unknown_symbol_is_returned_unchanged(self):
        from matsimpy.builders.bulk import suggest_element_substitutions

        assert suggest_element_substitutions(["Xx"]) == {"Xx": ["Xx"]}
