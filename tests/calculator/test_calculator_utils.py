"""calculator.utils text helpers and the parsers that rely on them."""

import warnings

import pytest

from matsimpy.calculator.utils import clean_lines


def test_clean_lines_strips_comments_and_whitespace():
    lines = ["  5.43   # lattice constant ", "# only a comment", "", "Si  "]
    assert clean_lines(lines) == ["5.43", "Si"]
    assert clean_lines(lines, remove_empty_lines=False) == ["5.43", "", "", "Si"]


def test_poscar_accepts_trailing_comments():
    from matsimpy.calculator.vasp.inputs import Poscar

    text = """Si2 bulk
5.43   # lattice constant
0.0 0.5 0.5
0.5 0.0 0.5   # b
0.5 0.5 0.0
Si
2
Direct
0.00 0.00 0.00
0.25 0.25 0.25
"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        crystal = Poscar.from_str(text).structure
    assert crystal.species == ("Si", "Si")
    lattice = crystal.lattice
    assert (lattice.a, lattice.b, lattice.c) == pytest.approx((5.43 / 2**0.5,) * 3)


def test_lammps_data_header_accepts_trailing_comments(tmp_path):
    pytest.importorskip("pandas")
    from matsimpy.calculator.lammps.data import LammpsData

    path = tmp_path / "comments.data"
    path.write_text(
        "LAMMPS data file  # header\n\n"
        "2 atoms   # two Ar atoms\n1 atom types\n\n"
        "0.0 10.0 xlo xhi   # box x\n0.0 10.0 ylo yhi\n0.0 10.0 zlo zhi\n\n"
        "Masses\n\n1 39.948\n\n"
        "Atoms  # atomic\n\n1 1 0.0 0.0 0.0\n2 1 5.0 5.0 5.0\n"
    )
    data = LammpsData.from_file(str(path), atom_style="atomic")
    assert len(data.atoms) == 2
    assert data.box.bounds == [[0.0, 10.0]] * 3
