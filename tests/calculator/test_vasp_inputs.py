"""Tests for VASP input file classes.

All VASP data comes from unmodified pymatgen 2026.10.24 test files
(see fixtures/vasp/PROVENANCE.md). pymatgen is used only as an optional
reference oracle.
"""

import os

import numpy as np
import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")


def _fixture(name):
    return os.path.join(FIXTURES_DIR, name)


def _read_text(name):
    with open(_fixture(name)) as fh:
        return fh.read()


class TestIncar:
    def test_from_file(self):
        """Parse INCAR from real VASP INCAR fixture."""
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar.from_file(_fixture("INCAR"))
        assert incar["ALGO"] == "Damped"
        assert float(incar["EDIFF"]) == pytest.approx(1e-4)
        assert isinstance(incar["LORBIT"], int)

    def test_from_dict_and_get(self):
        from matsimpy.calculator.vasp.inputs import Incar

        parsed = Incar.from_file(_fixture("INCAR_2"))
        rebuilt = Incar(dict(parsed))
        assert dict(rebuilt) == dict(parsed)
        assert rebuilt["ISIF"] == parsed["ISIF"] == 3

    @pytest.mark.parametrize("name", ["INCAR", "INCAR_2", "INCAR_C2", "INCAR.lobster"])
    def test_write_read_roundtrip(self, name, tmp_path):
        """0.8.x-0.9.0 wrote " =  ['ENCUT', 400.0]" lines (str_delimited), which VASP
        cannot parse and Incar.from_file read back as an empty INCAR."""
        import re

        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar.from_file(_fixture(name))
        fpath = tmp_path / "INCAR"
        incar.write_file(fpath)
        lines = fpath.read_text().splitlines()
        assert len(lines) == len(incar) > 3
        assert all(re.fullmatch(r"[A-Z_0-9]+ = \S.*", line) for line in lines), lines
        assert dict(Incar.from_file(fpath)) == dict(incar)

    def test_diff(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar1 = Incar.from_file(_fixture("INCAR"))
        incar2 = Incar.from_file(_fixture("INCAR_2"))
        diff = incar1.diff(incar2)
        assert diff["Different"]["ENCUT"] == {
            "INCAR1": incar1["ENCUT"],
            "INCAR2": None,  # INCAR_2 has no ENCUT
        }
        assert diff["Different"]["ISMEAR"] == {"INCAR1": incar1["ISMEAR"], "INCAR2": incar2["ISMEAR"]}
        assert set(diff["Same"]) | set(diff["Different"]) == set(incar1) | set(incar2)

    def test_get_str(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar.from_file(_fixture("INCAR"))
        lines = incar.get_str().splitlines()
        assert "ALGO = Damped" in lines
        assert dict(Incar.from_str(incar.get_str())) == dict(incar)

    def test_key_case_insensitive(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar.from_file(_fixture("INCAR"))
        incar["encut"] = 490
        assert incar["ENCUT"] == 490
        assert incar.get("encut") == 490

    @pytest.mark.parametrize("name", ["INCAR", "INCAR_2", "INCAR_C2", "INCAR.lobster"])
    def test_check_params(self, name):
        import warnings

        from matsimpy.calculator.vasp.inputs import Incar

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Incar.from_file(_fixture(name)).check_params()

    def test_incar_set_and_get(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar()
        incar["ENCUT"] = 500
        assert incar["ENCUT"] == 500

    @pytest.mark.parametrize("name", ["INCAR", "INCAR_2", "INCAR_C2", "INCAR.lobster"])
    def test_optional_pymatgen_reference(self, name):
        pytest.importorskip("pymatgen")
        from pymatgen.io.vasp.inputs import Incar as PmgIncar

        from matsimpy.calculator.vasp.inputs import Incar

        assert dict(Incar.from_file(_fixture(name))) == dict(PmgIncar.from_file(_fixture(name)))


KPOINTS_FILES = [
    "KPOINTS",
    "KPOINTS_auto",
    "KPOINTS_gamma",
    "KPOINTS_band",
    "KPOINTS_cartesian",
    "KPOINTS_explicit",
    "KPOINTS_explicit_tet",
]


class TestKpoints:
    def test_gamma_file(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.from_file(_fixture("KPOINTS_gamma"))
        assert kpt.style.name == "Gamma"
        assert [list(k) for k in kpt.kpts] == [[4, 4, 4]]

    def test_line_mode_file(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.from_file(_fixture("KPOINTS_band"))
        assert kpt.style.name == "Line_mode"
        assert kpt.num_kpts == 16
        assert kpt.labels[0] == "Γ"

    def test_explicit_tetrahedra_file(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.from_file(_fixture("KPOINTS_explicit_tet"))
        assert kpt.num_kpts == 4
        assert list(kpt.kpts_weights) == [1, 1, 2, 4]
        assert kpt.tet_number > 0

    @pytest.mark.parametrize("name", KPOINTS_FILES)
    def test_write_read_roundtrip(self, name, tmp_path):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.from_file(_fixture(name))
        fpath = tmp_path / "KPOINTS"
        kpt.write_file(fpath)
        again = Kpoints.from_file(fpath)
        assert again.style == kpt.style
        assert again.num_kpts == kpt.num_kpts
        np.testing.assert_allclose(np.asarray(again.kpts, float), np.asarray(kpt.kpts, float))

    @pytest.mark.parametrize("name", KPOINTS_FILES)
    def test_optional_pymatgen_reference(self, name):
        pytest.importorskip("pymatgen")
        from pymatgen.io.vasp.inputs import Kpoints as PmgKpoints

        from matsimpy.calculator.vasp.inputs import Kpoints

        ours = Kpoints.from_file(_fixture(name))
        ref = PmgKpoints.from_file(_fixture(name))
        assert ours.style.name == ref.style.name
        assert ours.num_kpts == ref.num_kpts
        np.testing.assert_allclose(np.asarray(ours.kpts, float), np.asarray(ref.kpts, float))
        assert list(ours.kpts_shift) == pytest.approx(list(ref.kpts_shift))
        assert ours.labels == ref.labels
        if ref.kpts_weights is not None:
            assert list(ours.kpts_weights) == pytest.approx(list(ref.kpts_weights))
        assert ours.tet_number == ref.tet_number
        assert ours.tet_weight == pytest.approx(ref.tet_weight)
        assert ours.tet_connections == ref.tet_connections

    # Generators: the data is produced by the API from parameters.
    def test_automatic(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.automatic(10)
        assert kpt.style.name == "Automatic"
        parsed = Kpoints.from_file(_fixture("KPOINTS_auto"))
        assert [list(k) for k in kpt.kpts] == [list(k) for k in parsed.kpts]

    def test_gamma_automatic(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.gamma_automatic([4, 4, 4])
        parsed = Kpoints.from_file(_fixture("KPOINTS_gamma"))
        assert kpt.style == parsed.style
        assert [list(k) for k in kpt.kpts] == [list(k) for k in parsed.kpts]

    def test_monkhorst_pack(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.monkhorst_automatic([6, 6, 6])
        assert kpt.style.name == "Monkhorst"
        assert [list(k) for k in kpt.kpts] == [[6, 6, 6]]


class TestPoscar:
    @pytest.fixture
    def c2_structure(self):
        from matsimpy.calculator.vasp.inputs import Poscar

        return Poscar.from_file(_fixture("POSCAR_C2"), check_for_potcar=False).structure

    def test_from_str_basic(self):
        """Parse POSCAR text (VASP 5 format)."""
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar.from_str(_read_text("POSCAR_C2"))
        assert poscar.structure.formula == "C2"
        assert poscar.site_symbols == ["C"]

    def test_from_str_vasp4_with_symbols(self):
        """VASP 4 file: no symbol line, symbols at the end of the coordinate lines."""
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar.from_str(_read_text("POSCAR"))
        assert poscar.natoms == [4, 4, 16]
        assert poscar.structure.composition.reduced_formula == "FePO4"
        # line 2 is a negative scale factor, i.e. the cell volume
        assert poscar.structure.lattice.volume == pytest.approx(300.65685512, rel=1e-6)

    def test_from_str_symbols_natoms_multilines(self):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar.from_str(_read_text("POSCAR_symbols_natoms_multilines"))
        assert len(poscar.structure) == 53
        assert poscar.structure.composition.reduced_formula == "Fe35Cr16Ni2"

    def test_selective_dynamics_roundtrip(self):
        """No pymatgen test file has selective dynamics, so the flags are set via
        the API on a real structure, written by the library and parsed back."""
        from matsimpy.calculator.vasp.inputs import Poscar

        structure = Poscar.from_file(_fixture("POSCAR.AlN"), check_for_potcar=False).structure
        flags = [[True, True, True], [False, False, False], [True, False, True], [False, True, False]]
        text = Poscar(structure, selective_dynamics=flags).get_str()
        assert "Selective dynamics" in text
        parsed = Poscar.from_str(text)
        assert [list(x) for x in parsed.selective_dynamics] == flags

    def test_from_str_empty_raises(self):
        from matsimpy.calculator.vasp.inputs import Poscar

        with pytest.raises(ValueError, match="Empty POSCAR"):
            Poscar.from_str("")

    def test_site_symbols(self, c2_structure):
        from matsimpy.calculator.vasp.inputs import Poscar

        assert Poscar(c2_structure).site_symbols == ["C"]

    def test_comment_default(self, c2_structure):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(c2_structure)
        assert poscar.comment == c2_structure.formula

    def test_comment_custom(self, c2_structure):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(c2_structure, comment="Custom POSCAR")
        assert poscar.comment == "Custom POSCAR"

    @pytest.mark.parametrize("name", ["POSCAR_C2", "POSCAR.AlN", "POSCAR_symbols_natoms_multilines", "POSCAR"])
    def test_write_read_roundtrip(self, name, tmp_path):
        from matsimpy.calculator.vasp.inputs import Poscar

        structure = Poscar.from_file(_fixture(name), check_for_potcar=False).structure
        fpath = tmp_path / "POSCAR"
        Poscar(structure).write_file(fpath)
        again = Poscar.from_file(fpath, check_for_potcar=False).structure
        assert again.composition == structure.composition
        np.testing.assert_allclose(again.lattice.matrix, structure.lattice.matrix, atol=1e-8)
        np.testing.assert_allclose(again.frac_positions, structure.frac_positions, atol=1e-8)

    @pytest.mark.parametrize("name", ["POSCAR", "POSCAR_C2", "POSCAR.AlN", "POSCAR_symbols_natoms_multilines"])
    def test_optional_pymatgen_reference(self, name):
        """Compare matsimpy Poscar parsing against pymatgen as reference oracle."""
        pytest.importorskip("pymatgen")
        from pymatgen.io.vasp.inputs import Poscar as PmgPoscar

        from matsimpy.calculator.vasp.inputs import Poscar

        path = _fixture(name)
        pmg_poscar = PmgPoscar.from_file(path, check_for_potcar=False, read_velocities=False)
        ms_poscar = Poscar.from_file(path, check_for_potcar=False, read_velocities=False)
        assert ms_poscar.site_symbols == pmg_poscar.site_symbols
        assert ms_poscar.natoms == pmg_poscar.natoms
        np.testing.assert_allclose(
            ms_poscar.structure.lattice.matrix, pmg_poscar.structure.lattice.matrix, atol=1e-10
        )
        np.testing.assert_allclose(
            ms_poscar.structure.frac_positions, pmg_poscar.structure.frac_coords, atol=1e-10
        )


class TestSettings:
    """SETTINGS was referenced but never defined: Poscar.from_file and
    Potcar(symbols) raised NameError."""

    def test_poscar_from_file_with_default_arguments(self):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar.from_file(os.path.join(FIXTURES_DIR, "POSCAR"))
        assert poscar.structure.formula == "Fe4P4O16"

    def test_settings_read_pmg_environment_variables(self, monkeypatch):
        from matsimpy.calculator.vasp.inputs import SETTINGS

        monkeypatch.delenv("PMG_VASP_PSP_DIR", raising=False)
        assert SETTINGS.get("PMG_VASP_PSP_DIR") is None
        monkeypatch.setenv("PMG_VASP_PSP_DIR", "/opt/psp")
        assert SETTINGS.get("PMG_VASP_PSP_DIR") == "/opt/psp"
        assert "PMG_VASP_PSP_DIR" in dict(SETTINGS)
        for raw, expected in [("false", False), ("0", False), ("True", True)]:
            monkeypatch.setenv("PMG_POTCAR_CHECKS", raw)
            assert SETTINGS.get("PMG_POTCAR_CHECKS") is expected
        assert SETTINGS.get("HOME") is None  # only PMG_* keys

    def test_potcar_from_symbols_reports_missing_psp_dir(self, monkeypatch):
        from matsimpy.calculator.vasp.inputs import PmgVaspPspDirError, Potcar

        monkeypatch.delenv("PMG_VASP_PSP_DIR", raising=False)
        with pytest.raises(PmgVaspPspDirError, match="PMG_VASP_PSP_DIR environment variable"):
            Potcar(["Si"], functional="PBE")
