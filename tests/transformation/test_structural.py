"""Tests for matsimpy.transformation.structural: supercells and molecular operations."""

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation.structural import (
    align_molecules,
    fragment_molecule,
    generate_conformers,
    make_supercell,
    merge_molecules,
)


# --------------------------------------------------------------------------
# make_supercell
# --------------------------------------------------------------------------


def test_make_supercell_repeats_atoms_site_properties_and_pbc():
    crystal = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64),
                      pbc=[True, False, True], site_properties=[{"id": "Na"}, {"id": "Cl"}])
    supercell = make_supercell(crystal, [2, 1, 1])
    assert supercell.pbc == (True, False, True)
    assert supercell.site_properties == ({"id": "Na"}, {"id": "Cl"}) * 2
    assert len(make_supercell(from_prototype("diamond", "Si", 5.0), [2, 2, 2])) == 16


def test_make_supercell_general_matrix_keeps_cartesian_positions():
    crystal = Crystal(["He"], [[0.25, 0, 0]], Lattice.cubic(1.0))
    out = make_supercell(crystal, [[1, 1, 0], [0, 1, 0], [0, 0, 1]])
    delta = (out.cart_positions[0] - crystal.cart_positions[0]) @ np.linalg.inv(out.lattice.matrix)
    np.testing.assert_allclose(delta, np.rint(delta), atol=1e-12)


def test_make_supercell_leaves_a_non_periodic_axis_alone():
    slab = Crystal(["C"], [[0.25, 0.25, 1.3]], Lattice.cubic(5.0), pbc=[True, True, False])
    np.testing.assert_allclose(make_supercell(slab, [2, 2, 1]).frac_positions[:, 2], 1.3)


@pytest.mark.parametrize("matrix, error", [
    ([2, 2], ValueError),
    ([1, 1, 2], ValueError),  # repeats the vacuum axis
    ([[1, 0, 1], [0, 1, 0], [0, 0, 1]], ValueError),  # mixes it into a periodic axis
    ([True, True, True], TypeError),
])
def test_make_supercell_rejects_bad_matrices(matrix, error):
    slab = Crystal(["C"], [[0.25, 0.25, 0.5]], Lattice.cubic(5.0), pbc=[True, True, False])
    with pytest.raises(error):
        make_supercell(slab, matrix)


# --------------------------------------------------------------------------
# align_molecules
# --------------------------------------------------------------------------


def test_align_molecules_recovers_a_rigid_motion():
    p = np.random.default_rng(1).normal(size=(5, 3)) * 2
    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    moved = Molecule(["C"] * 5, p @ R.T + [1, 2, 3])
    aligned = align_molecules(Molecule(["C"] * 5, p), moved, range(5), range(5))
    np.testing.assert_allclose(aligned.positions, p, atol=1e-10)


@pytest.mark.parametrize("ref_idx, mov_idx, error, match", [
    ([], [], ValueError, "at least one"),
    ([0], [1], IndexError, "outside molecule"),
])
def test_align_molecules_rejects_bad_selections(ref_idx, mov_idx, error, match):
    m = Molecule(["H"], [[0, 0, 0]])
    with pytest.raises(error, match=match):
        align_molecules(m, m, ref_idx, mov_idx)


# --------------------------------------------------------------------------
# merge_molecules / fragment_molecule / generate_conformers
# --------------------------------------------------------------------------


def test_merge_molecules_places_the_second_molecule_at_the_bond_length():
    c, o = Molecule(["C"], [[0, 0, 0]]), Molecule(["O"], [[5, 5, 5]])
    merged = merge_molecules(c, o, 0, 0, bond_length=1.2)
    assert merged.species == ("C", "O")
    np.testing.assert_allclose(merged.positions[1], [1.2, 0, 0])
    with pytest.raises(ValueError, match="apart"):
        merge_molecules(c, o, 0, 0)  # would put both atoms on one point


def test_fragment_molecule_splits_at_the_bond_and_keeps_site_properties():
    m = Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]], site_properties=[{"id": "left"}, {"id": "right"}])
    fragments = fragment_molecule(m, [(0, 1)])
    assert [f.site_properties for f in fragments] == [({"id": "left"},), ({"id": "right"},)]


def test_fragment_molecule_rejects_a_pair_that_is_not_bonded():
    m = Molecule(["C", "C", "C"], [[0, 0, 0], [1.5, 0, 0], [3.0, 0, 0]])
    with pytest.raises(ValueError, match="not bonded"):
        fragment_molecule(m, [[0, 2]])


def test_generate_conformers_returns_molecules_or_asks_for_rdkit():
    molecule = Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]])
    try:
        conformers = generate_conformers(molecule, n_conformers=1)
    except ImportError as e:
        assert "RDKit is required" in str(e)
    else:
        assert len(conformers) == 1 and isinstance(conformers[0], Molecule)
