"""P1 regression tests for core structure invariants."""

import numpy as np
import pytest

from matsimpy import Crystal, Lattice, Molecule


def test_molecule_add_atom_rejects_nan_position():
    molecule = Molecule(["He"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="NaN"):
        molecule.add_atom("Ne", [float("nan"), 0, 0])


def test_crystal_add_atom_rejects_nan_position():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))

    with pytest.raises(ValueError, match="NaN"):
        crystal.add_atom("Ne", [float("nan"), 0, 0])


def test_structure_construct_rejects_species_position_length_mismatch():
    with pytest.raises(ValueError, match="Number of positions"):
        Molecule._construct(("H", "O"), np.zeros((1, 3)))


def test_crystal_construct_rejects_infinite_position():
    with pytest.raises(ValueError, match="infinite"):
        Crystal._construct(
            ("He",),
            np.array([[float("inf"), 0, 0]]),
            Lattice.cubic(3),
            (True, True, True),
        )


def test_crystal_equality_includes_pbc():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))
    non_periodic = crystal.set_pbc([False, False, False])

    assert crystal != non_periodic


def test_crystal_structural_hash_includes_pbc():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))
    non_periodic = crystal.set_pbc([False, False, False])

    assert crystal._structural_hash() != non_periodic._structural_hash()
