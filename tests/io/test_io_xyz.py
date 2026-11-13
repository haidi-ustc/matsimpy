"""Tests for matsimpy.io XYZ reading and writing (plain XYZ; extended XYZ is format='ase')."""

import os

import numpy as np
import pytest

from matsimpy.core import Molecule
from matsimpy.io import read, read_POSCAR, read_XYZ, read_XYZ_multiframe, write_XYZ
from matsimpy.io.ase import write_ASE

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


@pytest.fixture
def co2():
    return Molecule(["C", "O", "O"], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]])


def test_round_trip(tmp_path, co2):
    write_XYZ(co2, tmp_path / "x.xyz", title="CO2")
    back = read_XYZ(tmp_path / "x.xyz")
    assert back.species == co2.species
    np.testing.assert_allclose(back.positions, co2.positions)


def test_multiframe_reads_every_frame(tmp_path):
    (tmp_path / "f.xyz").write_text(
        "2\nFrame 1\nH 0.0 0.0 0.0\nH 0.74 0.0 0.0\n"
        "2\nFrame 2\nH 0.0 0.0 0.0\nH 0.75 0.0 0.0\n"
        "2\nFrame 3\nH 0.0 0.0 0.0\nH 0.76 0.0 0.0\n"
    )
    frames = read_XYZ_multiframe(tmp_path / "f.xyz")
    assert [f.positions[1, 0] for f in frames] == pytest.approx([0.74, 0.75, 0.76])


def test_multiframe_strict_mode_rejects_garbage_between_frames(tmp_path, co2):
    write_XYZ(co2, tmp_path / "a.xyz")
    text = (tmp_path / "a.xyz").read_text()
    (tmp_path / "multi.xyz").write_text(text + "this is not xyz\n" + text)
    with pytest.raises(ValueError, match="atom count"):
        read_XYZ_multiframe(tmp_path / "multi.xyz")
    assert len(read_XYZ_multiframe(tmp_path / "multi.xyz", strict=False)) == 2


def test_extended_xyz_with_a_cell_is_not_read_as_a_molecule(tmp_path):
    c = read_POSCAR(os.path.join(VASP_DIR, "POSCAR_MnO"))
    write_ASE(c, tmp_path / "x.xyz")
    with pytest.raises(ValueError, match="format='ase'"):
        read_XYZ(tmp_path / "x.xyz")
    assert read(tmp_path / "x.xyz", format="ase").formula == c.formula


def test_errors(tmp_path, co2):
    with pytest.raises(FileNotFoundError):
        read_XYZ(tmp_path / "missing.xyz")
    (tmp_path / "bad.xyz").write_text("Invalid\n")
    with pytest.raises(ValueError):
        read_XYZ(tmp_path / "bad.xyz")
    with pytest.raises(ValueError):
        write_XYZ("not a molecule", tmp_path / "x.xyz")
    with pytest.raises(ValueError, match="single line"):
        write_XYZ(co2, tmp_path / "x.xyz", title="a\nb")
