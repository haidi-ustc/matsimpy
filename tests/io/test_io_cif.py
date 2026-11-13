"""Tests for matsimpy.io CIF reading and writing.

Real CIF inputs are unmodified pymatgen test files in tests/calculator/fixtures/cif
(see PROVENANCE.md there).
"""

import os

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Lattice
from matsimpy.io import read_CIF, write_CIF

CIF_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "cif")


def _path(name):
    return os.path.join(CIF_DIR, name)


_CELL = (
    "_cell_length_a 5\n_cell_length_b 5\n_cell_length_c 5\n"
    "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n"
)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def test_real_file_with_comments_and_a_single_row_loop_matches_pymatgen():
    c = read_CIF(_path("FePO4.cif"))
    assert c.formula == "Fe4P4O16"
    pmg = pytest.importorskip("pymatgen.io.cif")
    ref = pmg.CifParser(_path("FePO4.cif")).parse_structures(primitive=False)[0]
    assert c.volume == pytest.approx(ref.volume, rel=1e-6)


def test_type_symbols_with_charges():
    assert sorted(read_CIF(_path("CsCl-manual-oxi-ref.mcif")).species) == ["Cl", "Cs"]


@pytest.mark.parametrize("name, match", [
    ("nosymm.cif", "not P1"),
    ("magnetic.example.NiO.mcif", "symmetry expansion"),
    ("C26H16BeN2O2S2.cif", "symmetry expansion"),  # used to fail in the tokenizer
    ("MultiStructure.cif", "2 structures"),
])
def test_files_that_cannot_be_read_as_p1_raise(name, match):
    with pytest.raises(ValueError, match=match):
        read_CIF(_path(name))


def test_cartesian_coordinates_are_converted(tmp_path):
    (tmp_path / "c.cif").write_text(
        "data_test\n" + _CELL +
        "loop_\n_atom_site_type_symbol\n_atom_site_Cartn_x\n_atom_site_Cartn_y\n_atom_site_Cartn_z\n"
        "Si 0.0 0.0 0.0\nO  2.5 2.5 2.5\n"
    )
    crystal = read_CIF(tmp_path / "c.cif")
    assert crystal.species == ("Si", "O")
    np.testing.assert_allclose(crystal.frac_positions[1], [0.5, 0.5, 0.5])


def test_cif_quoting_comments_and_text_fields(tmp_path):
    (tmp_path / "q.cif").write_text(
        "data_q\n"
        "_publ_author_name 'Strel'tsov, V.A.'\n" + _CELL +
        "_symmetry_space_group_name_H-M 'P 1'\n"
        "loop_\n_atom_site_label\n_atom_site_type_symbol\n"
        "_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n"
        "C1' C 0 0 0  # a comment with an apostrophe: it's\n"
        "O1' O 0.5 0.5 0.5\n"
        "_journal_coden_ASTM\n;\nsome text\n;\n"
    )
    assert read_CIF(tmp_path / "q.cif").species == ("C", "O")


def test_read_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_CIF(tmp_path / "missing.cif")
    (tmp_path / "bad.cif").write_text("Invalid\n")
    with pytest.raises(ValueError):
        read_CIF(tmp_path / "bad.cif")


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------


def test_write_round_trip_with_a_multi_line_title(tmp_path):
    crystal = from_prototype("diamond", "Si", 5.43)
    write_CIF(crystal, tmp_path / "x.cif", title="two\nlines")
    back = read_CIF(tmp_path / "x.cif")
    assert back.species == crystal.species
    np.testing.assert_allclose(back.lattice.matrix, crystal.lattice.matrix, atol=1e-4)


def test_write_uses_per_element_labels(tmp_path):
    crystal = Crystal(["Si", "O", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]], Lattice.cubic(5.0))
    write_CIF(crystal, tmp_path / "x.cif")
    content = (tmp_path / "x.cif").read_text()
    assert "Si1" in content and "Si2" in content and "O1" in content
    assert "Si3" not in content


def test_write_rejects_non_crystals(tmp_path):
    with pytest.raises(ValueError):
        write_CIF("not a crystal", tmp_path / "x.cif")
