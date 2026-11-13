"""Tests for matsimpy.io XSF reading and writing."""

import os

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal
from matsimpy.io import read_POSCAR, read_XSF, to_ase, write_XSF

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


def test_round_trip(tmp_path):
    crystal = from_prototype("diamond", "Si", 5.43)
    write_XSF(crystal, tmp_path / "x.xsf")
    back = read_XSF(tmp_path / "x.xsf")
    assert isinstance(back, Crystal)
    assert back.species == crystal.species
    np.testing.assert_allclose(back.cart_positions, crystal.cart_positions, atol=1e-6)


def test_reads_atomic_numbers_as_written_by_ase(tmp_path):
    ase_io = pytest.importorskip("ase.io")
    c = read_POSCAR(os.path.join(VASP_DIR, "POSCAR_MnO"))
    ase_io.write(tmp_path / "x.xsf", to_ase(c))
    assert read_XSF(tmp_path / "x.xsf").species == c.species


def test_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_XSF(tmp_path / "missing.xsf")
    (tmp_path / "bad.xsf").write_text("Invalid\n")
    with pytest.raises(ValueError):
        read_XSF(tmp_path / "bad.xsf")
    with pytest.raises(ValueError):
        write_XSF("not a crystal", tmp_path / "x.xsf")
