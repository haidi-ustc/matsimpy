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


def test_str_delimited_joins_row_fields():
    from matsimpy.calculator.utils import str_delimited

    assert str_delimited([["ENCUT", 400], ["ISMEAR", 0]], None, " = ") == "ENCUT = 400\nISMEAR = 0"
    assert str_delimited([[1, 2]], header=["a", "b"]) == "a\tb\n1\t2"


def test_incar_text_is_tag_equals_value_and_round_trips(tmp_path):
    """0.8.x-0.9.0 wrote " =  ['ENCUT', 400.0]" lines, which VASP cannot parse and
    Incar.from_file read back as an empty INCAR."""
    from matsimpy.calculator.vasp.inputs import Incar

    incar = Incar({"ENCUT": 520, "ISMEAR": 0, "LWAVE": False, "MAGMOM": [1.0, 1.0, -1.0]})
    path = tmp_path / "INCAR"
    incar.write_file(path)
    text = path.read_text()
    assert text.splitlines() == [
        "ENCUT = 520.0",
        "ISMEAR = 0",
        "LWAVE = False",
        "MAGMOM = 2*1.0 1*-1.0",
    ]
    assert Incar.from_file(path) == incar


def test_micro_pyawk_runs_records_with_predicates(tmp_path):
    from matsimpy.calculator.utils import micro_pyawk

    path = tmp_path / "log.txt"
    path.write_text("mode up\nE = 1.5\nmode down\nE = -2.0\nE = 3.0\n")

    def set_mode(results, match):
        results["mode"] = match[1]

    def add_energy(results, match):
        results.setdefault(results["mode"], []).append(float(match[1]))

    results = micro_pyawk(
        path,
        [
            [r"^mode (\w+)", None, set_mode],
            [r"^E = (\S+)", lambda results, _line: "mode" in results, add_energy],
        ],
    )
    assert results == {"mode": "down", "up": [1.5], "down": [-2.0, 3.0]}


def test_micro_pyawk_rejects_the_old_dict_interface(tmp_path):
    from matsimpy.calculator.utils import micro_pyawk

    path = tmp_path / "log.txt"
    path.write_text("x\n")
    with pytest.raises(TypeError, match="records"):
        micro_pyawk(path, {"key": r"x"})
    with pytest.raises(ValueError, match="regex, predicate, action"):
        micro_pyawk(path, [[r"x", None]])
