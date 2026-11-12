"""Crystal prototype identifiers and the read-only prototype database.

Expected identifiers are independent references: textbook Wyckoff sites of
real structures (pymatgen 2026.10.24 test files, see
tests/calculator/fixtures/vasp/PROVENANCE.md), e.g. antifluorite Li2O O 4a /
Li 8c, and AFLOW's label for YBa2Cu3O7, A2B3C7D_oP13_47_k_cj_aijl_f.
"""

import os
import pickle
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.io import read
from matsimpy.symmetry import PrototypeDatabase, PrototypeInfo, get_prototype, get_prototype_info
from matsimpy.transformation.structural import make_supercell

pytest.importorskip("spglib")

VASP = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


def _real(name):
    return read(os.path.join(VASP, name))


def _rocksalt(elements=("Na", "Cl")):
    return from_prototype("rocksalt", list(elements), 5.64)


def _redescribe(crystal, rng):
    """The same crystal in another cell, origin, atom order and orientation."""
    while True:
        change = rng.integers(-1, 2, size=(3, 3))
        if round(abs(np.linalg.det(change))) == 1:
            break
    matrix = np.asarray(crystal.lattice.matrix, float)
    new_matrix = change @ matrix
    cartesian = np.asarray(crystal.frac_positions) @ matrix + rng.random(3) @ matrix
    frac = (cartesian @ np.linalg.inv(new_matrix)) % 1
    order = rng.permutation(len(crystal))
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    rotation[:, 0] *= np.sign(np.linalg.det(rotation))
    return Crystal([crystal.species[i] for i in order], frac[order], Lattice(new_matrix @ rotation.T))


REAL = [
    ("POSCAR_C2", "A_cF8_227_a"),  # diamond, C 8a
    ("POSCAR_Li2O", "AB2_cF12_225_a_c"),  # antifluorite, O 4a, Li 8c; 96-atom supercell
    ("POSCAR_MnO", "AB_cF8_225_a_b"),  # rocksalt; primitive 2-atom cell
    ("POSCAR_bcc", "A_cI2_229_a"),
    ("POSCAR_fcc", "A_cF4_225_a"),  # 8-atom supercell of the primitive cell
    ("POSCAR.AlN", "AB_hP4_186_b_b"),  # wurtzite, Al 2b, N 2b
    ("POSCAR_Al12O18", "A2B3_hR10_167_c_e"),  # corundum, Al 12c, O 18e; rhombohedral count
]


@pytest.mark.parametrize(("fixture", "expected"), REAL)
def test_real_structures_have_textbook_prototypes(fixture, expected):
    assert get_prototype(_real(fixture)) == expected


@pytest.mark.parametrize(("fixture", "expected"), REAL)
def test_identifier_is_invariant_under_redescription(fixture, expected):
    rng = np.random.default_rng(7)
    crystal = _real(fixture)
    assert {get_prototype(_redescribe(crystal, rng)) for _ in range(4)} == {expected}


def _ybco(permutation=(0, 1, 2), shift=(0, 0, 0)):
    """YBa2Cu3O7 (Pmmm) in the ITA description Y 1h, Ba 2t, Cu 1a 2q, O 1e 2q 2r 2s."""
    species = ["Y", "Ba", "Ba", "Cu", "Cu", "Cu"] + ["O"] * 7
    positions = np.array([
        [.5, .5, .5], [.5, .5, .184], [.5, .5, .816], [0, 0, 0], [0, 0, .355], [0, 0, .645],
        [0, .5, 0], [.5, 0, .378], [.5, 0, .622], [0, .5, .378], [0, .5, .622], [0, 0, .159], [0, 0, .841],
    ])
    axes = np.eye(3)[list(permutation)]
    lattice = axes @ np.diag([3.82, 3.89, 11.68])
    return Crystal(species, (positions @ axes.T + shift) % 1, Lattice(lattice))


@pytest.mark.parametrize(
    ("permutation", "shift"),
    [((0, 1, 2), (0, 0, 0)), ((2, 0, 1), (0, 0, 0)), ((1, 0, 2), (.5, 0, .5)), ((0, 2, 1), (.5, .5, .5))],
)
def test_wyckoff_letters_match_aflow_for_ybco(permutation, shift):
    """AFLOW: A2B3C7D_oP13_47_k_cj_aijl_f (Ba k, Cu c j, O a i j l, Y f), the
    smallest letter sum of the 48 axis/origin choices.  The given ITA
    description (sum 105) and its re-descriptions all give it."""
    info = get_prototype_info(_ybco(permutation, shift))
    assert info.space_group_number == 47
    assert info.pearson_symbol == "oP13"
    # anonymized by count: Y (1) -> A, Ba (2) -> B, Cu (3) -> C, O (7) -> D
    assert info.prototype == "AB2C3D7_oP13_47_f_k_cj_aijl"


@pytest.mark.parametrize(
    ("name", "elements", "expected"),
    [
        ("diamond", "Si", "A_cF8_227_a"),
        ("zincblende", ["Ga", "As"], "AB_cF8_216_a_c"),
        ("rocksalt", ["Na", "Cl"], "AB_cF8_225_a_b"),
        ("wurtzite", ["Zn", "O"], "AB_hP4_186_b_b"),
        ("perovskite", ["Sr", "Ti", "O"], "ABC3_cP5_221_a_b_c"),
        ("hcp", "Mg", "A_hP2_194_c"),
    ],
)
def test_builder_prototypes(name, elements, expected):
    """Primitive and conventional cells give the same letters and the
    conventional-cell Pearson symbol (diamond was a/b, zincblende a_c/a_d)."""
    crystal = from_prototype(name, elements, 4.0)
    assert get_prototype(crystal) == expected
    conventional = make_supercell(crystal, [[-1, 1, 1], [1, -1, 1], [1, 1, -1]])
    assert get_prototype(conventional) == expected


def test_prototype_info_components():
    info = get_prototype_info(_real("POSCAR_Li2O"))
    assert info.as_dict() == {
        "anonymized_formula": "AB2",
        "pearson_symbol": "cF12",
        "space_group_number": 225,
        "space_group_symbol": "Fm-3m",
        "wyckoff_fingerprint": "a_c",
        "prototype": "AB2_cF12_225_a_c",
        "symprec": pytest.approx(info.symprec),
    }
    assert isinstance(info, PrototypeInfo)
    with pytest.raises(FrozenInstanceError):
        info.prototype = "x"


class TestTolerance:
    def test_adaptive_tolerance_is_a_hundredth_of_the_shortest_distance(self):
        # MnO: Mn-O 2.26 A
        assert get_prototype_info(_real("POSCAR_MnO")).symprec == pytest.approx(0.0226, abs=1e-4)

    def test_explicit_tolerance_is_used_as_given(self):
        """1e-5 sees the rounding noise of the 6-decimal POSCAR as lower symmetry."""
        info = get_prototype_info(_real("POSCAR_MnO"), symprec=1e-5)
        assert info.symprec == 1e-5
        assert info.space_group_symbol == "I4mm"

    def test_inconsistent_tolerance_is_halved(self, monkeypatch):
        import matsimpy.symmetry.prototype as module

        real = module._standardize
        tried = []

        def standardize(crystal, symprec):
            tried.append(symprec)
            return None if len(tried) < 3 else real(crystal, symprec)

        monkeypatch.setattr(module, "_standardize", standardize)
        info = get_prototype_info(_real("POSCAR_MnO"))
        assert tried == pytest.approx([tried[0], tried[0] / 2, tried[0] / 4])
        assert info.symprec == tried[-1]
        assert info.prototype == "AB_cF8_225_a_b"

    def test_no_consistent_tolerance_raises(self, monkeypatch):
        import matsimpy.symmetry.prototype as module

        monkeypatch.setattr(module, "_standardize", lambda crystal, symprec: None)
        with pytest.raises(ValueError, match="any tolerance"):
            get_prototype(_rocksalt())
        with pytest.raises(ValueError, match="symprec=0.01"):
            get_prototype(_rocksalt(), symprec=0.01)

    def test_tolerance_above_a_quarter_of_the_shortest_distance_is_rejected(self):
        """spglib 2.8 crashes the interpreter from about 0.45 of the distance."""
        with pytest.raises(ValueError, match="too large"):
            get_prototype(_rocksalt(), symprec=1.0)  # Na-Cl 2.82 A


def test_invariant_under_element_substitution():
    assert {get_prototype(_rocksalt(pair)) for pair in [("Na", "Cl"), ("Cs", "Cl"), ("Mg", "O")]} == {
        "AB_cF8_225_a_b"
    }


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
            "A_cF8_227_a": ["C2"],
            "AB2_cF12_225_a_c": ["Li2O"],
            "AB_cF8_225_a_b": ["NaCl"],
        }

    def test_pickle(self):
        db = PrototypeDatabase({"ABC": ["a.vasp"]})
        assert pickle.loads(pickle.dumps(db)) == db


class TestBuilders:
    FILES = ["POSCAR_C2", "POSCAR_Li2O", "POSCAR_MnO", "POSCAR_bcc"]

    def test_build_prototype_database_from_files(self):
        from matsimpy.builders.bulk import build_prototype_database

        db = build_prototype_database([os.path.join(VASP, f) for f in self.FILES])
        assert db.as_dict() == {
            "A_cF8_227_a": ["POSCAR_C2"],
            "AB2_cF12_225_a_c": ["POSCAR_Li2O"],
            "AB_cF8_225_a_b": ["POSCAR_MnO"],
            "A_cI2_229_a": ["POSCAR_bcc"],
        }

    def test_build_merges_into_an_existing_database(self):
        from matsimpy.builders.bulk import build_prototype_database

        existing = PrototypeDatabase({"A_cF8_227_a": ["existing.vasp"]})
        db = build_prototype_database([os.path.join(VASP, "POSCAR_C2")], database=existing)
        assert db["A_cF8_227_a"] == ("existing.vasp", "POSCAR_C2")
        assert existing["A_cF8_227_a"] == ("existing.vasp",)

    def test_build_propagates_file_errors(self, tmp_path):
        from matsimpy.builders.bulk import build_prototype_database

        with pytest.raises(FileNotFoundError, match="missing.vasp"):
            build_prototype_database([tmp_path / "missing.vasp"])

    def _db(self):
        return PrototypeDatabase({"AB_cF8_225_a_b": ["POSCAR_MnO"]})

    def test_structures_from_prototype(self):
        from matsimpy.builders.bulk import structures_from_prototype

        structures = structures_from_prototype(
            self._db(), "AB_cF8_225_a_b", VASP,
            element_substitutions={"Mn": ["Mn", "Ni"], "O": ["O", "S"]}, max_structures=3,
        )
        assert [sorted(s.species) for s in structures] == [["Mn", "O"], ["Mn", "S"], ["Ni", "O"]]
        assert all(get_prototype(s) == "AB_cF8_225_a_b" for s in structures)

    def test_substitutions_are_simultaneous(self):
        from matsimpy.builders.bulk import structures_from_prototype

        (swapped,) = structures_from_prototype(
            self._db(), "AB_cF8_225_a_b", VASP, element_substitutions={"Mn": ["O"], "O": ["Mn"]}
        )
        template = _real("POSCAR_MnO")
        assert list(swapped.species) == [{"Mn": "O", "O": "Mn"}[s] for s in template.species]

    def test_default_substitutions_use_suggestions(self):
        from matsimpy.builders.bulk import structures_from_prototype, suggest_element_substitutions

        options = suggest_element_substitutions(["Mn", "O"])
        structures = structures_from_prototype(self._db(), "AB_cF8_225_a_b", VASP, max_structures=5)
        assert len(structures) == 5
        assert all(set(s.species) <= set(options["Mn"]) | set(options["O"]) for s in structures)

    def test_zero_limit(self):
        from matsimpy.builders.bulk import structures_from_prototype

        assert structures_from_prototype(self._db(), "AB_cF8_225_a_b", VASP, max_structures=0) == []

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
            structures_from_prototype(self._db(), "AB_cF8_225_a_b", VASP, **kwargs)

    def test_unknown_prototype_and_missing_template(self, tmp_path):
        from matsimpy.builders.bulk import structures_from_prototype

        with pytest.raises(ValueError, match="No template structure"):
            structures_from_prototype(self._db(), "UNKNOWN", VASP)
        with pytest.raises(FileNotFoundError, match="Template structure file not found"):
            structures_from_prototype(self._db(), "AB_cF8_225_a_b", tmp_path)


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


def test_wyckoff_letter_values_continue_after_z():
    """spglib names the 27th Wyckoff position "A" (Pmmm general position 8A);
    it must count as 27, not as a negative number, in the letter sum."""
    from matsimpy.symmetry.prototype import _letter_value

    assert [_letter_value(letter) for letter in "azA"] == [1, 26, 27]
    point = np.array([.11, .23, .37])
    signs = [(1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1), (-1, -1, -1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)]
    general = Crystal(["Si"] * 8, [(np.array(s) * point) % 1 for s in signs], Lattice(np.diag([3., 4., 5.])))
    assert get_prototype(general) == "A_oP8_47_A"
