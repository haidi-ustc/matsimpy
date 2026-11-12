"""Core invariants that only the public constructor enforced in 0.9.0.

``add_atom`` and ``_construct`` both end in ``_set_state``, which did not check
for NaN/Inf, and ``==`` ignored PBC although the calculator cache key uses it.
"""

import numpy as np
import pytest

from matsimpy import Crystal, Lattice, Molecule


@pytest.fixture
def crystal():
    return Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))


@pytest.mark.parametrize("bad, kind", [(np.nan, "NaN"), (np.inf, "infinite"), (-np.inf, "infinite")])
def test_add_atom_rejects_non_finite_positions(crystal, bad, kind):
    molecule = Molecule(["He"], [[0, 0, 0]])
    with pytest.raises(ValueError, match=kind):
        molecule.add_atom("Ne", [bad, 0, 0])
    with pytest.raises(ValueError, match=kind):
        crystal.add_atom("Ne", [bad, 0, 0])
    with pytest.raises(ValueError, match=kind):
        crystal.add_atom("Ne", [bad, 0, 0], coords_are_cartesian=True)


def test_construct_rejects_non_finite_positions():
    with pytest.raises(ValueError, match="NaN"):
        Molecule._construct(("He",), np.array([[np.nan, 0, 0]]))
    with pytest.raises(ValueError, match="infinite"):
        Crystal._construct(("He",), np.array([[np.inf, 0, 0]]), Lattice.cubic(3), pbc=(True,) * 3)


def test_construct_rejects_species_position_count_mismatch():
    with pytest.raises(ValueError, match="Number of positions"):
        Molecule._construct(("H", "O"), np.zeros((1, 3)))


def test_crystal_equality_includes_pbc(crystal):
    slab = crystal.set_pbc([True, True, False])
    assert crystal != slab
    assert slab == crystal.set_pbc([True, True, False])
    assert crystal == crystal.copy()
    # consistent with the calculator cache key
    assert crystal._structural_hash() != slab._structural_hash()
