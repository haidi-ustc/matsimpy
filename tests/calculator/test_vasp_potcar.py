"""POTCAR handling without POTCAR reference data.

MatSimPy ships no POTCAR statistics (POTCARs are copyrighted), and the lookups
indexed the empty table by functional, so every real POTCAR raised KeyError.
Tests use pymatgen's placeholder ("FAKE") POTCARs only; see PROVENANCE.md.
"""

import os
import shutil
import warnings

import pytest

from matsimpy.calculator.vasp.inputs import Poscar, Potcar, UnknownPotcarWarning

VASP_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")
FAKE_DIR = os.path.join(VASP_DIR, "fake_potcars")


def test_potcar_from_file_is_unverified_not_an_error():
    with pytest.warns(UnknownPotcarWarning, match="could not be verified"):
        potcar = Potcar.from_file(os.path.join(FAKE_DIR, "POTCAR.gz"))
    assert potcar.symbols == ["Fe", "P", "O"]
    assert all(single.identify_potcar()[0] == [] for single in potcar)


def test_potcar_from_symbols_uses_pmg_vasp_psp_dir(monkeypatch):
    monkeypatch.setenv("PMG_VASP_PSP_DIR", FAKE_DIR)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnknownPotcarWarning)
        potcar = Potcar(["Fe", "P", "O"], functional="PBE_54")
    assert potcar.symbols == ["Fe", "P", "O"]
    # TITEL lines of the placeholder files ("; FAKE" is a separate header field)
    assert [single.TITEL for single in potcar] == [
        "PAW_PBE Fe 06Sep2000",
        "PAW_PBE P 06Sep2000",
        "PAW_PBE O 08Apr2002",
    ]


def test_poscar_next_to_a_potcar_takes_species_from_it(tmp_path):
    shutil.copy(os.path.join(VASP_DIR, "POSCAR"), tmp_path / "POSCAR")
    shutil.copy(os.path.join(FAKE_DIR, "POTCAR.gz"), tmp_path / "POTCAR.gz")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnknownPotcarWarning)
        poscar = Poscar.from_file(tmp_path / "POSCAR")
    assert poscar.site_symbols == ["Fe", "P", "O"]
    assert poscar.structure.formula == "Fe4P4O16"


def test_input_set_does_not_report_functional_mismatch_without_reference_data(monkeypatch):
    from matsimpy.calculator.vasp.sets import BadInputSetWarning, MPRelaxSet

    monkeypatch.setenv("PMG_VASP_PSP_DIR", FAKE_DIR)
    structure = Poscar.from_file(os.path.join(VASP_DIR, "POSCAR"), check_for_potcar=False).structure
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        potcar = MPRelaxSet(structure, user_potcar_functional="PBE_54").potcar
    assert potcar.symbols == ["Fe_pv", "P", "O"]  # MPRelaxSet POTCAR choices
    assert not [w for w in caught if issubclass(w.category, BadInputSetWarning) and "functionals" in str(w.message)]
