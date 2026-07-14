from __future__ import annotations

import re

from matsimpy.calculator.lammps.calculator import LammpsCalculator
from matsimpy.core import Crystal, Lattice


def _write_lammps_data(tmp_path, structure) -> str:
    calc = LammpsCalculator(directory=str(tmp_path), run=False)
    calc.write_input(structure)
    return (tmp_path / "data.lammps").read_text()


def test_lammps_data_preserves_multi_species_atom_types(tmp_path):
    crystal = Crystal(
        ["Si", "O", "Si"],
        [[0, 0, 0], [0.2, 0.2, 0.2], [0.4, 0.4, 0.4]],
        Lattice.cubic(5.0),
    )

    data = _write_lammps_data(tmp_path, crystal)

    assert "2 atom types" in data
    assert re.search(r"^1\s+28\.0855\b", data, re.MULTILINE)
    assert re.search(r"^2\s+15\.9994\b", data, re.MULTILINE)
    assert re.search(
        r"^1\s+1\s+0\.000000\s+0\.000000\s+0\.000000$",
        data,
        re.MULTILINE,
    )
    assert re.search(
        r"^2\s+2\s+1\.000000\s+1\.000000\s+1\.000000$",
        data,
        re.MULTILINE,
    )
    assert re.search(
        r"^3\s+1\s+2\.000000\s+2\.000000\s+2\.000000$",
        data,
        re.MULTILINE,
    )


def test_lammps_data_preserves_triclinic_box_tilts(tmp_path):
    crystal = Crystal(
        ["Si"],
        [[0, 0, 0]],
        Lattice([[3.0, 0.0, 0.0], [1.0, 4.0, 0.0], [0.5, 0.25, 5.0]]),
    )

    data = _write_lammps_data(tmp_path, crystal)

    assert re.search(
        r"^1\.000000\s+0\.500000\s+0\.250000\s+xy xz yz$",
        data,
        re.MULTILINE,
    )
