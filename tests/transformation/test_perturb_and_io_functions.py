"""0.9.0: behaviour of the former Crystal/Molecule convenience methods, now plain functions.

``crystal.perturb(...)``      -> ``perturb_positions`` / ``perturb_lattice``
``structure.to_file/from_file`` -> ``matsimpy.io.write`` / ``matsimpy.io.read``
"""

import numpy as np
import pytest

from matsimpy.analysis.selection import AtomSelection
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.io import read, write
from matsimpy.transformation import perturb_lattice, perturb_positions


@pytest.mark.parametrize(
    "structure",
    [
        Crystal(["Si", "O", "Si", "O"], [[0, 0, 0], [0.25] * 3, [0.5] * 3, [0.75] * 3], Lattice.cubic(5.0)),
        Molecule(["H", "O", "H", "C"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0], [1.5, 0, 0]]),
    ],
)
def test_perturb_positions_with_atom_selection(structure):
    target = structure.species[0]
    before = structure.positions.copy()
    result = perturb_positions(structure, 0.1, indices=AtomSelection(structure).by_species(target), seed=42)
    assert np.array_equal(structure.positions, before)  # input untouched
    moved = ~np.all(np.isclose(result.positions, before), axis=1)
    assert moved.tolist() == [s == target for s in structure.species]


def test_perturb_positions_rejects_selection_from_other_structure():
    a, b = (from_prototype("diamond", "Si", 5.43) for _ in range(2))
    with pytest.raises(ValueError):
        perturb_positions(b, 0.1, indices=AtomSelection(a).by_species("Si"))


def test_perturb_lattice_keeps_fractional_coordinates():
    c = from_prototype("diamond", "Si", 5.43)
    r = perturb_lattice(c, 0.1, seed=42)
    assert np.allclose(r.frac_positions, c.frac_positions)
    assert not np.allclose(r.lattice.matrix, c.lattice.matrix)
    assert np.allclose(c.lattice.matrix, from_prototype("diamond", "Si", 5.43).lattice.matrix)


@pytest.mark.parametrize(
    ("structure", "name"),
    [
        (Molecule(["C", "O", "O"], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]), "co2.xyz"),
        (Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43)), "si.vasp"),
    ],
)
def test_io_write_read_roundtrip(tmp_path, structure, name):
    path = str(tmp_path / name)
    write(structure, path)
    back = read(path)
    assert type(back) is type(structure) and back.species == structure.species
