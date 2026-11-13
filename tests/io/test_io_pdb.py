"""Tests for matsimpy.io PDB reading and writing."""

import os

import numpy as np
import pytest

from matsimpy.core import Crystal, Molecule
from matsimpy.io import read_PDB, read_POSCAR, write_PDB

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


@pytest.mark.parametrize("name", ["POSCAR_fcc", "POSCAR_Al12O18"])
def test_crystal_round_trip_in_the_standard_orientation(tmp_path, name):
    c = read_POSCAR(os.path.join(VASP_DIR, name))
    write_PDB(c, tmp_path / "x.pdb")
    assert "CRYST1" in (tmp_path / "x.pdb").read_text()
    back = read_PDB(tmp_path / "x.pdb", as_crystal=True)
    assert isinstance(back, Crystal)
    assert back.species == c.species
    d = back.frac_positions - c.frac_positions
    assert np.abs(d - np.round(d)).max() < 1e-3


def test_molecule_round_trip(tmp_path):
    m = Molecule(["C", "O", "O"], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]])
    write_PDB(m, tmp_path / "m.pdb")
    back = read_PDB(tmp_path / "m.pdb")
    assert back.species == m.species
    np.testing.assert_allclose(back.positions, m.positions, atol=1e-3)


def test_element_from_atom_name_follows_the_column_convention(tmp_path):
    (tmp_path / "n.pdb").write_text(
        "ATOM      1 FE   UNK A   1       0.000   0.000   0.000  1.00  0.00\n"
        "ATOM      2 CL   UNK A   1       2.000   0.000   0.000  1.00  0.00\n"
        "ATOM      3  CA  UNK A   1       0.000   2.000   0.000  1.00  0.00\n"  # alpha carbon
        "ATOM      4  C1  UNK A   1       0.000   0.000   2.000  1.00  0.00            \n"
        "END\n"
    )
    assert read_PDB(tmp_path / "n.pdb").species == ("Fe", "Cl", "C", "C")


def test_several_models_raise(tmp_path):
    atom = "ATOM      1  C   UNK A   1       0.000   0.000   0.000  1.00  0.00           C\n"
    (tmp_path / "m.pdb").write_text("MODEL 1\n" + atom + "ENDMDL\nMODEL 2\n" + atom + "ENDMDL\nEND\n")
    with pytest.raises(ValueError, match="MODEL"):
        read_PDB(tmp_path / "m.pdb")


def test_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_PDB(tmp_path / "missing.pdb")
    (tmp_path / "bad.pdb").write_text("Invalid\n")
    with pytest.raises(ValueError):
        read_PDB(tmp_path / "bad.pdb")
    with pytest.raises(ValueError):
        write_PDB("not a structure", tmp_path / "x.pdb")
