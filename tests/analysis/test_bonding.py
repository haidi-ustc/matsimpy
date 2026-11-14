"""Tests for matsimpy.analysis.bonding.BondAnalyzer."""
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
