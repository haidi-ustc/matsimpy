import importlib.util

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry import HighSymmKpath, SpacegroupAnalyzer, StructureMatcher


HAS_SPGLIB = importlib.util.find_spec("spglib") is not None
HAS_PYMATGEN = importlib.util.find_spec("pymatgen") is not None


@pytest.fixture
def si_crystal():
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.43))


@pytest.mark.requires_spglib
@pytest.mark.skipif(not HAS_SPGLIB, reason="spglib not installed")
def test_spacegroup_standardization_and_ir_mesh(si_crystal):
    analyzer = SpacegroupAnalyzer(si_crystal, symprec=1e-3)
    primitive = analyzer.get_primitive_standard_structure()
    conventional = analyzer.get_conventional_standard_structure()
    points, weights = analyzer.get_ir_reciprocal_mesh((4, 4, 4))
    assert len(primitive) <= len(conventional)
    assert sum(weights) == 64
    assert np.asarray(points).shape[1] == 3
    assert set(primitive.species) == {"Si"}


def test_structure_matcher_handles_permutation_and_translation(si_crystal):
    moved = Crystal(
        si_crystal.species[::-1],
        (si_crystal.frac_positions[::-1] + 0.2) % 1,
        si_crystal.lattice,
    )
    assert StructureMatcher().fit(si_crystal, moved)


def test_structure_matcher_rejects_composition_and_geometry(si_crystal):
    wrong_species = Crystal(["Si", "C"], si_crystal.frac_positions, si_crystal.lattice)
    distorted = Crystal(si_crystal.species, [[0, 0, 0], [0.45, 0.45, 0.45]], si_crystal.lattice)
    assert not StructureMatcher().fit(si_crystal, wrong_species)
    assert not StructureMatcher(stol=0.1).fit(si_crystal, distorted)


@pytest.mark.requires_spglib
@pytest.mark.skipif(not HAS_SPGLIB, reason="spglib not installed")
def test_cubic_kpath_is_deterministic_and_labeled(si_crystal):
    path = HighSymmKpath(si_crystal)
    points, labels = path.get_kpoints(line_density=10)
    points2, labels2 = path.get_kpoints(line_density=10)
    assert np.array_equal(points, points2)
    assert labels == labels2
    assert len(points) == len(labels)
    assert labels[0] and labels[-1]
    assert np.allclose(points[0], [0, 0, 0])


def test_services_raise_targeted_error_without_spglib(monkeypatch, si_crystal):
    import matsimpy.symmetry.spacegroup as module

    monkeypatch.setattr(module, "spglib", None)
    with pytest.raises(ImportError, match="pip install spglib"):
        SpacegroupAnalyzer(si_crystal).get_conventional_standard_structure()


@pytest.mark.parametrize(
    "key", ["cP", "cF", "cI", "tP", "tI", "oP", "oF", "oI", "oC", "hP", "hR", "mP", "mC", "aP"]
)
def test_every_supported_bravais_path_has_valid_segments(key):
    from matsimpy.symmetry.kpath import PATHS

    points, segments = PATHS[key]
    assert segments
    assert all(start in points and end in points for start, end in segments)
    assert all(len(points[label]) == 3 for label in points)


@pytest.mark.requires_pymatgen
@pytest.mark.skipif(not (HAS_SPGLIB and HAS_PYMATGEN), reason="pymatgen and spglib required")
def test_pymatgen_parity_for_cubic_standardization_and_mesh(si_crystal):
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer as PmgAnalyzer

    pmg = Structure(
        PmgLattice(si_crystal.lattice.matrix),
        si_crystal.species,
        si_crystal.frac_positions,
    )
    native = SpacegroupAnalyzer(si_crystal, symprec=1e-3)
    native_conventional = native.get_conventional_standard_structure()
    pmg_analyzer = PmgAnalyzer(pmg, symprec=1e-3)
    pmg_conventional = pmg_analyzer.get_conventional_standard_structure()
    assert sorted(native_conventional.species) == sorted(str(s) for s in pmg_conventional.species)
    assert np.allclose(
        sorted([native_conventional.lattice.a, native_conventional.lattice.b, native_conventional.lattice.c]),
        sorted(pmg_conventional.lattice.abc),
        atol=1e-7,
    )
    _, native_weights = native.get_ir_reciprocal_mesh((4, 4, 4))
    pmg_weights = [weight for _, weight in pmg_analyzer.get_ir_reciprocal_mesh((4, 4, 4))]
    assert sorted(native_weights) == sorted(pmg_weights)
