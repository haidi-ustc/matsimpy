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


def _potcar(*symbols):
    """A POTCAR as VASP users build it: the single placeholder POTCARs concatenated."""
    import gzip

    return "".join(gzip.open(os.path.join(FAKE_DIR, "POT_GGA_PAW_PBE_54", f"POTCAR.{s}.gz"), "rt").read()
                   for s in symbols)


@pytest.mark.parametrize("poscar, potcar, species", [
    ("POSCAR", ("Fe", "P", "O"), "Fe4P4O16"),  # VASP 4: the POTCAR names the species, as in VASP
    ("POSCAR_O2", ("O",), "O8"),               # VASP 5: the names agree
])
def test_poscar_next_to_a_matching_potcar(tmp_path, poscar, potcar, species):
    shutil.copy(os.path.join(VASP_DIR, poscar), tmp_path / "POSCAR")
    (tmp_path / "POTCAR").write_text(_potcar(*potcar))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnknownPotcarWarning)
        assert Poscar.from_file(tmp_path / "POSCAR").structure.formula == species


@pytest.mark.parametrize("poscar, potcar, error", [
    # POSCAR_MnO names "O Mn"; pymatgen relabelled the atoms with the POTCAR's names
    ("POSCAR_MnO", ("Fe", "O"), r"POSCAR species \['O', 'Mn'\] do not match the POTCAR's \['Fe', 'O'\]"),
    ("POSCAR_MnO", ("O", "Fe"), "do not match the POTCAR"),
    ("POSCAR", ("Fe", "P"), "2 species"),          # VASP 4 with too few POTCARs
    ("POSCAR", ("Fe", "P", "O", "O"), "4 species"),  # ... and too many (was accepted)
])
def test_poscar_next_to_a_potcar_of_another_structure_is_an_error(tmp_path, poscar, potcar, error):
    shutil.copy(os.path.join(VASP_DIR, poscar), tmp_path / "POSCAR")
    (tmp_path / "POTCAR").write_text(_potcar(*potcar))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnknownPotcarWarning)
        with pytest.raises(ValueError, match=error):
            Poscar.from_file(tmp_path / "POSCAR")
        # the POSCAR's own species can still be read
        if poscar == "POSCAR_MnO":
            assert Poscar.from_file(tmp_path / "POSCAR", check_for_potcar=False).site_symbols == ["O", "Mn"]


def test_input_set_does_not_report_functional_mismatch_without_reference_data(monkeypatch):
    from matsimpy.calculator.vasp.sets import BadInputSetWarning, MPRelaxSet

    monkeypatch.setenv("PMG_VASP_PSP_DIR", FAKE_DIR)
    structure = Poscar.from_file(os.path.join(VASP_DIR, "POSCAR"), check_for_potcar=False).structure
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        potcar = MPRelaxSet(structure, user_potcar_functional="PBE_54").potcar
    assert potcar.symbols == ["Fe_pv", "P", "O"]  # MPRelaxSet POTCAR choices
    assert not [w for w in caught if issubclass(w.category, BadInputSetWarning) and "functionals" in str(w.message)]


def test_written_poscar_potcar_and_per_species_tags_line_up(monkeypatch, tmp_path):
    """Species that are not grouped give repeated blocks; every per-species list follows them."""
    from matsimpy.calculator.vasp.inputs import Incar
    from matsimpy.calculator.vasp.sets import MPRelaxSet
    from matsimpy.core import Crystal, Lattice

    monkeypatch.setenv("PMG_VASP_PSP_DIR", FAKE_DIR)
    crystal = Crystal(["Fe", "O", "Fe", "P", "O"], [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5], [0.5] * 3],
                      Lattice.cubic(6.0), site_properties=[{"magmom": m} for m in (4.0, 0.0, -4.0, 0.0, 0.0)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        MPRelaxSet(crystal, sort_structure=False, user_potcar_functional="PBE_54").write_input(tmp_path)
    poscar = Poscar.from_file(tmp_path / "POSCAR", check_for_potcar=False)
    titles = [line.split()[3] for line in (tmp_path / "POTCAR").read_text().splitlines() if "TITEL" in line]
    incar = Incar.from_file(tmp_path / "INCAR")
    assert (poscar.site_symbols, poscar.natoms) == (["Fe", "O", "Fe", "P", "O"], [1, 1, 1, 1, 1])
    assert titles == ["Fe_pv", "O", "Fe_pv", "P", "O"]
    assert incar["LDAUU"] == [5.3, 0, 5.3, 0, 0] and incar["LDAUL"] == [2, 0, 2, 0, 0]
    assert incar["MAGMOM"] == [4.0, 0.0, -4.0, 0.0, 0.0]  # the site order, signs kept
