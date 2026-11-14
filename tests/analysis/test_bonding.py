"""Tests for matsimpy.analysis.bonding.BondAnalyzer."""
import numpy as np
import pytest

from matsimpy.analysis.bonding import BondAnalyzer
from matsimpy.core import Molecule
from matsimpy.io import read
from tests.conftest import require_path


def test_coordination_numbers_count_every_periodic_image():
    # Primitive rocksalt MnO: 6 neighbours at 2.26 A, all images of the other atom.
    crystal = read(require_path("tests", "calculator", "fixtures", "vasp", "POSCAR_MnO"))
    assert BondAnalyzer(crystal, cutoff=2.5).get_coordination_numbers() == {0: 6, 1: 6}


def test_periodic_coordination_cutoff_is_exclusive():
    # POSCAR_bcc (a = 1): 8 neighbours at 0.866 A and 6 at exactly 1.0 A. A cutoff of
    # 1.0 keeps only the 8, matching find_bonds' strict ``d < cutoff``.
    crystal = read(require_path("tests", "calculator", "fixtures", "vasp", "POSCAR_bcc"))
    assert BondAnalyzer(crystal).get_coordination_numbers(cutoff=1.0) == {0: 8, 1: 8}


def test_molecule_coordination_numbers_count_bonds():
    # Linear H-C-H chain: C bonded to both H, H atoms 2.2 A apart.
    mol = Molecule(["H", "C", "H"], [[-1.1, 0, 0], [0, 0, 0], [1.1, 0, 0]])
    assert BondAnalyzer(mol, cutoff=1.5).get_coordination_numbers() == {0: 1, 1: 2, 2: 1}


def _butane(dihedral_deg):
    # C1-C2 along x, C0 in the xy plane; C3 rotated about the C1-C2 axis.
    phi = np.radians(dihedral_deg)
    return Molecule(
        ["C", "C", "C", "C"],
        [[-0.51, 1.442, 0.0], [0.0, 0.0, 0.0], [1.53, 0.0, 0.0],
         [2.04, 1.442 * np.cos(phi), 1.442 * np.sin(phi)]],
    )


@pytest.mark.parametrize("dihedral", [180.0, 60.0, -60.0])
def test_dihedral_angles_are_signed_about_the_central_bond(dihedral):
    (i, j, k, ell, angle), = BondAnalyzer(_butane(dihedral), cutoff=1.8).get_dihedral_angles()
    assert (i, j, k, ell) == (0, 1, 2, 3)
    assert angle == pytest.approx(dihedral, abs=1e-6)


@pytest.mark.parametrize("species, distance, order", [
    (["C", "C"], 1.53, 1.0),
    (["C", "O"], 1.21, 1.0),  # documented limit: the step heuristic cannot see C=O as double
    (["C", "C"], 1.0, 2.0),   # ratio 1.4 > 1.3
    (["C", "C"], 1.6, 0.5),   # ratio 0.875 < 0.9
])
def test_bond_order_steps_on_atomic_radius_ratio(species, distance, order):
    mol = Molecule(species, [[0.0, 0.0, 0.0], [distance, 0.0, 0.0]])
    assert BondAnalyzer(mol).get_bond_order(0, 1) == order
