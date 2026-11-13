"""Tests for the ASE extended-XYZ text format and the MDL MOL format."""

import os

import numpy as np
import pytest

from matsimpy.core import Molecule
from matsimpy.io import read_ASE, read_MOL, read_POSCAR, write_ASE, write_MOL

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


@pytest.fixture
def co2():
    return Molecule(["C", "O", "O"], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]])


# --------------------------------------------------------------------------
# ASE format
# --------------------------------------------------------------------------


def test_ase_round_trip_keeps_partial_pbc(tmp_path):
    c = read_POSCAR(os.path.join(VASP_DIR, "POSCAR_MnO")).set_pbc([True, True, False])
    write_ASE(c, tmp_path / "s.ase", title="MnO slab")
    back = read_ASE(tmp_path / "s.ase")
    assert back.species == c.species
    assert back.pbc == (True, True, False)
    np.testing.assert_allclose(back.lattice.matrix, c.lattice.matrix)


def test_ase_molecule_with_a_blank_title(tmp_path, co2):
    write_ASE(co2, tmp_path / "m.ase", title="")
    assert read_ASE(tmp_path / "m.ase").species == co2.species


def test_ase_file_without_a_lattice_is_a_molecule(tmp_path):
    (tmp_path / "m.ase").write_text("3\nNo lattice info\nSi 0.0 0.0 0.0\nO 2.5 2.5 2.5\nO 5.0 5.0 5.0\n")
    assert isinstance(read_ASE(tmp_path / "m.ase"), Molecule)


def test_ase_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_ASE(tmp_path / "missing.ase")
    with pytest.raises(ValueError):
        write_ASE("not a structure", tmp_path / "x.ase")


# --------------------------------------------------------------------------
# MOL format
# --------------------------------------------------------------------------


def test_mol_round_trip(tmp_path, co2):
    write_MOL(co2, tmp_path / "x.mol", title="CO2")
    back = read_MOL(tmp_path / "x.mol")
    assert back.species == co2.species
    np.testing.assert_allclose(back.positions, co2.positions, atol=1e-4)


def test_mol_counts_line_is_read_by_column(tmp_path):
    # "  2150": 2 atoms and 150 bonds run together in the fixed-width fields
    lines = ["title", "", "", "  2150  0  0  0  0  0  0  0  0999 V2000",
             "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0",
             "    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0", "M  END"]
    (tmp_path / "x.mol").write_text("\n".join(lines) + "\n")
    assert len(read_MOL(tmp_path / "x.mol")) == 2


def test_mol_atom_line_without_an_element_raises(tmp_path):
    (tmp_path / "x.mol").write_text(
        "bad element\n  MatSimPy\n\n  1  0  0  0  0  0  0  0  0  0  1 V2000\n"
        "    0.0000    0.0000    0.0000     0  0\nM  END\n"
    )
    with pytest.raises(ValueError):
        read_MOL(tmp_path / "x.mol")


def test_mol_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_MOL(tmp_path / "missing.mol")
    (tmp_path / "bad.mol").write_text("Invalid\n")
    with pytest.raises(ValueError):
        read_MOL(tmp_path / "bad.mol")
    with pytest.raises(ValueError):
        write_MOL("not a molecule", tmp_path / "x.mol")
    big = Molecule(["H"] * 1000, [[i * 1.0, 0, 0] for i in range(1000)])
    with pytest.raises(ValueError, match="999"):
        write_MOL(big, tmp_path / "big.mol")
