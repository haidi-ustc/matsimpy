import importlib.util

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry import HighSymmKpath, SpacegroupAnalyzer, StructureMatcher


HAS_SPGLIB = importlib.util.find_spec("spglib") is not None
HAS_PYMATGEN = importlib.util.find_spec("pymatgen") is not None


def _bravais_cases():
    """Primitive cells with generic sites, covering every SC Bravais family."""
    from ase.cell import Cell
    from ase.lattice import (
        BCC, BCT, CUB, FCC, HEX, MCL, MCLC, ORC, ORCC, ORCF, ORCI, RHL, TET,
    )

    lattices = [
        ("cP", CUB(3)), ("cF", FCC(3)), ("cI", BCC(3)),
        ("tP", TET(3, 4)), ("tI", BCT(3, 4)),
        ("oP", ORC(2, 3, 4)), ("oF", ORCF(2, 3, 4)),
        ("oI", ORCI(2, 3, 4)), ("oC", ORCC(2, 3, 4)),
        ("hP", HEX(3, 5)), ("hR", RHL(3, 70)),
        ("mP", MCL(2, 3, 5, 70)), ("mC", MCLC(2, 3, 5, 60)),
    ]
    triclinic = Cell([[2, 0, 0], [.4, 3, 0], [.3, .7, 4]])
    lattices.append(("aP", triclinic))
    return [
        (key, Crystal(["Si"], [[.123, .234, .345]], Lattice(np.asarray(cell.tocell() if hasattr(cell, "tocell") else cell))))
        for key, cell in lattices
    ]


def _metric_variant_cases():
    from ase.lattice import BCT, MCLC, ORCF, RHL

    lattices = [
        ("BCT1", BCT(3, 2)), ("BCT2", BCT(3, 5)),
        ("ORCF1", ORCF(2, 3, 4)), ("ORCF2", ORCF(3, 4, 4.5)),
        ("ORCF3", ORCF(2.4, 3, 4)),
        ("RHL1", RHL(3, 70)), ("RHL2", RHL(3, 100)),
        ("MCLC1", MCLC(3.5461038558, 5.3113186419, 5.9048393325, 86.9380988435)),
        ("MCLC3", MCLC(4.4677886352, 2.5658580679, 4.8862046920, 38.0591791019)),
        ("MCLC4", MCLC(4.0189289526, 4.0697563098, 4.4021938100, 49.7471371456)),
        ("MCLC5", MCLC(4.2082802329, 4.2276386994, 5.0711981480, 68.7528333269)),
    ]
    cases = [
        (variant, Crystal(["Si"], [[.123, .234, .345]], Lattice(np.asarray(cell.tocell()))))
        for variant, cell in lattices
    ]
    return cases


def test_source_definitions_cover_mclc2_boundary_variant():
    from ase.lattice import MCLC

    assert MCLC(2, 2.309401076758506, 4, 60).variant == "MCLC2"


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


def test_metric_dependent_paths_are_not_primitive_family_aliases():
    from matsimpy.symmetry.kpath import PATHS

    assert PATHS["tI"] is not PATHS["tP"]
    assert PATHS["oF"] is not PATHS["oP"]
    assert PATHS["oI"] is not PATHS["oP"]
    assert PATHS["oC"] is not PATHS["oP"]
    assert PATHS["mC"] is not PATHS["mP"]


@pytest.mark.requires_spglib
@pytest.mark.skipif(not HAS_SPGLIB, reason="spglib not installed")
def test_interpolation_includes_both_endpoints_with_pymatgen_count(si_crystal):
    path = HighSymmKpath(si_crystal)
    points, labels = path.get_kpoints(line_density=1, coords_are_cartesian=True)
    reciprocal = path._reciprocal
    start_label, end_label = path.kpath["path"][0][:2]
    start = np.asarray(path.kpath["kpoints"][start_label])
    end = np.asarray(path.kpath["kpoints"][end_label])
    expected_first_segment = int(np.ceil(np.linalg.norm((end - start) @ reciprocal))) + 1
    assert labels[0] == start_label
    assert labels[expected_first_segment - 1] == end_label
    assert np.allclose(points[expected_first_segment - 1], end @ reciprocal)


@pytest.mark.requires_spglib
@pytest.mark.skipif(not HAS_SPGLIB, reason="spglib not installed")
@pytest.mark.parametrize("expected,structure", _bravais_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_all_bravais_families_have_strong_native_invariants(expected, structure):
    path = HighSymmKpath(structure, symprec=1e-4)
    points, labels = path.get_kpoints(line_density=2)
    assert path.bravais == expected
    assert np.isfinite(np.asarray(list(path.kpath["kpoints"].values()))).all()
    assert all(len(branch) >= 2 for branch in path.kpath["path"])
    assert len(points) == len(labels) > 0
    assert labels[0] == path.kpath["path"][0][0]
    assert labels[-1] == path.kpath["path"][-1][-1]


@pytest.mark.requires_pymatgen
@pytest.mark.skipif(not (HAS_SPGLIB and HAS_PYMATGEN), reason="pymatgen and spglib required")
@pytest.mark.parametrize("expected,structure", _bravais_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_setyawan_curtarolo_kpath_parity_matrix(expected, structure):
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer as PmgAnalyzer
    from pymatgen.symmetry.bandstructure import HighSymmKpath as PmgKpath

    native = HighSymmKpath(structure, symprec=1e-4)
    pmg_input = Structure(
        PmgLattice(structure.lattice.matrix), structure.species, structure.frac_positions
    )
    pmg_structure = PmgAnalyzer(pmg_input, symprec=1e-4).get_primitive_standard_structure()
    reference = PmgKpath(
        pmg_structure, path_type="setyawan_curtarolo", symprec=1e-4
    )
    assert native.bravais == expected
    assert native.kpath["path"] == reference.kpath["path"]
    assert set(native.kpath["kpoints"]) == set(reference.kpath["kpoints"])
    for label, point in native.kpath["kpoints"].items():
        assert np.allclose(point, reference.kpath["kpoints"][label], atol=1e-7)
    native_points, native_labels = native.get_kpoints(2, coords_are_cartesian=False)
    ref_points, ref_labels = reference.get_kpoints(2, coords_are_cartesian=False)
    assert native_labels == ref_labels
    assert len(native_points) == len(ref_points)
    assert np.allclose(native_points, ref_points, atol=1e-7)


@pytest.mark.requires_spglib
@pytest.mark.skipif(not HAS_SPGLIB, reason="spglib not installed")
@pytest.mark.parametrize("expected,structure", _metric_variant_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_metric_subvariant_classification(expected, structure):
    path = HighSymmKpath(structure, symprec=1e-5)
    assert path.kpath["variant"] == expected


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
