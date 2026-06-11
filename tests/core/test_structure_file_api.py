"""Core structure file API wrapper tests."""

import pytest

from matsimpy.core import Crystal, Lattice, Molecule, Structure
from matsimpy.exceptions import StructureTypeError


def write_xyz(path):
    path.write_text(
        "3\n"
        "water\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.8 0.6\n"
        "H 0.0 -0.8 0.6\n"
    )


def test_structure_from_file_returns_molecule_for_xyz(tmp_path):
    path = tmp_path / "water.xyz"
    write_xyz(path)

    structure = Structure.from_file(str(path))

    assert isinstance(structure, Molecule)
    assert structure.species == ("O", "H", "H")


def test_molecule_to_file_writes_via_registry(tmp_path):
    path = tmp_path / "co2.xyz"
    molecule = Molecule(["C", "O", "O"], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]])

    molecule.to_file(str(path))

    assert path.exists()
    roundtrip = Structure.from_file(str(path))
    assert isinstance(roundtrip, Molecule)
    assert roundtrip.species == molecule.species


def test_crystal_from_file_rejects_molecule_result(tmp_path):
    path = tmp_path / "water.xyz"
    write_xyz(path)

    with pytest.raises(StructureTypeError):
        Crystal.from_file(str(path))


def test_molecule_from_file_rejects_crystal_result(tmp_path):
    path = tmp_path / "silicon.vasp"
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    crystal.to_file(str(path))

    with pytest.raises(StructureTypeError):
        Molecule.from_file(str(path))
