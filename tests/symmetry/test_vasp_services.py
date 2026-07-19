import importlib.util
import os
import subprocess
import sys
import warnings

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry import HighSymmKpath, SpacegroupAnalyzer, StructureMatcher


HAS_SPGLIB = importlib.util.find_spec("spglib") is not None
HAS_PYMATGEN = importlib.util.find_spec("pymatgen") is not None


def test_symmetry_kpath_imports_and_runs_when_ase_and_pymatgen_are_blocked(tmp_path):
    script = tmp_path / "blocked_symmetry.py"
    script.write_text(
        "import builtins\n"
        "real_import = builtins.__import__\n"
        "def blocked(name, *args, **kwargs):\n"
        "    if name.split('.')[0] in {'ase', 'pymatgen'}:\n"
        "        raise ImportError('blocked optional dependency: ' + name)\n"
        "    return real_import(name, *args, **kwargs)\n"
        "builtins.__import__ = blocked\n"
        "from matsimpy.core import Crystal, Lattice\n"
        "from matsimpy.symmetry import HighSymmKpath\n"
        "crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [.25, .25, .25]], Lattice.cubic(5.43))\n"
        "path = HighSymmKpath(crystal)\n"
        "assert len(path.get_kpoints(2)[0]) > 0\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    result = subprocess.run(
        [sys.executable, str(script)], env=env, text=True, capture_output=True
    )
    assert result.returncode == 0, result.stderr


def _bravais_cases():
    """Primitive cells with generic sites, covering every SC Bravais family."""
    lattices = [
        ("cP", _primitive_cell("cP", 3)), ("cF", _primitive_cell("cF", 3)),
        ("cI", _primitive_cell("cI", 3)), ("tP", _primitive_cell("tP", 3, 1, 4)),
        ("tI", _primitive_cell("tI", 3, 1, 4)), ("oP", _primitive_cell("oP", 2, 3, 4)),
        ("oF", _primitive_cell("oF", 2, 3, 4)), ("oI", _primitive_cell("oI", 2, 3, 4)),
        ("oC", _primitive_cell("oC", 2, 3, 4)), ("hP", _primitive_cell("hP", 3, 1, 5)),
        ("hR", _primitive_cell("hR", 3, 1, 1, 70)), ("mP", _primitive_cell("mP", 2, 3, 5, 70)),
        ("mC", _primitive_cell("mC", 2, 3, 5, 60)),
    ]
    triclinic = np.array([[2, 0, 0], [.4, 3, 0], [.3, .7, 4]])
    lattices.append(("aP", triclinic))
    return [
        (key, Crystal(["Si"], [[.123, .234, .345]], Lattice(cell)))
        for key, cell in lattices
    ]


def _metric_variant_cases():
    lattices = [
        ("BCT1", _primitive_cell("tI", 3, 1, 2)), ("BCT2", _primitive_cell("tI", 3, 1, 5)),
        ("ORCF1", _primitive_cell("oF", 2, 3, 4)), ("ORCF2", _primitive_cell("oF", 3, 4, 4.5)),
        ("ORCF3", _primitive_cell("oF", 2.4, 3, 4)),
        ("RHL1", _primitive_cell("hR", 3, 1, 1, 70)), ("RHL2", _primitive_cell("hR", 3, 1, 1, 100)),
        ("MCLC1", _primitive_cell("mC", 3.5461038558, 5.3113186419, 5.9048393325, 86.9380988435)),
        ("MCLC2", _primitive_cell("mC", 2.3, 2.3354812073372133, 4.3, 80)),
        ("MCLC3", _primitive_cell("mC", 4.4677886352, 2.5658580679, 4.8862046920, 38.0591791019)),
        ("MCLC4", _primitive_cell("mC", 2.095253697125836, 2, 3.5, 70)),
        ("MCLC5", _primitive_cell("mC", 4.2082802329, 4.2276386994, 5.0711981480, 68.7528333269)),
    ]
    cases = [
        (variant, Crystal(["Si"], [[.123, .234, .345]], Lattice(cell)))
        for variant, cell in lattices
    ]
    return cases


def _primitive_cell(key, a, b=1, c=1, alpha=60):
    """Independent standardized primitive fixtures (SC equations)."""
    if key == "cP": return a * np.eye(3)
    if key == "cF": return .5 * np.array([[0, a, a], [a, 0, a], [a, a, 0]])
    if key == "cI": return .5 * np.array([[-a, a, a], [a, -a, a], [a, a, -a]])
    if key == "tP": return np.diag([a, a, c])
    if key == "tI": return .5 * np.array([[-a, a, c], [a, -a, c], [a, a, -c]])
    if key == "oP": return np.diag([a, b, c])
    if key == "oF": return .5 * np.array([[0, b, c], [a, 0, c], [a, b, 0]])
    if key == "oI": return .5 * np.array([[-a, b, c], [a, -b, c], [a, b, -c]])
    if key == "oC": return np.array([[a/2, -b/2, 0], [a/2, b/2, 0], [0, 0, c]])
    if key == "hP": return np.array([[a/2, -np.sqrt(3)*a/2, 0], [a/2, np.sqrt(3)*a/2, 0], [0, 0, c]])
    if key == "hR":
        co=np.cos(np.radians(alpha)); co2=np.cos(np.radians(alpha/2)); si2=np.sin(np.radians(alpha/2)); q=co/co2
        return np.array([[a*co2, -a*si2, 0], [a*co2, a*si2, 0], [a*q, 0, a*np.sqrt(1-q*q)]])
    if key == "mP": return np.array([[a, 0, 0], [0, b, 0], [0, c*np.cos(np.radians(alpha)), c*np.sin(np.radians(alpha))]])
    if key == "mC": return np.array([[a/2, b/2, 0], [-a/2, b/2, 0], [0, c*np.cos(np.radians(alpha)), c*np.sin(np.radians(alpha))]])


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


def test_structure_matcher_uses_true_minimum_image_for_skew_cell():
    lattice = Lattice([[1.0, 0.0, 0.0], [0.95, 0.2, 0.0], [0.0, 0.0, 3.0]])
    original = Crystal(["Si", "Si"], [[0, 0, 0], [0.49, 0.49, 0]], lattice)
    # The second displacement has a short image obtained by shifting only one
    # skew fractional component; component-wise rounding chooses the wrong image.
    moved = Crystal(["Si", "Si"], [[0, 0, 0], [0.51, -0.49, 0]], lattice)
    assert StructureMatcher(stol=0.08).fit(original, moved)


def test_minimum_image_distance_is_exact_for_triclinic_lattice():
    from matsimpy.symmetry.matcher import _minimum_image_distances

    lattice = np.array([[1.0, 0.0, 0.0], [0.95, 0.2, 0.0], [0.4, 0.1, 2.0]])
    delta = np.array([0.49, 0.49, 0.0])
    brute = min(
        np.linalg.norm((delta + [i, j, k]) @ lattice)
        for i in range(-2, 3)
        for j in range(-2, 3)
        for k in range(-2, 3)
    )
    rounded = np.linalg.norm((delta - np.rint(delta)) @ lattice)
    assert brute < rounded
    assert _minimum_image_distances(delta, lattice) == pytest.approx(brute)


@pytest.mark.parametrize(
    "basis",
    [
        np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]]),
        np.array([[1, 1, 0], [0, 1, 0], [0, 0, 1]]),
    ],
    ids=["axis-permutation", "unimodular-shear"],
)
def test_structure_matcher_accepts_equivalent_integer_bases(basis):
    lattice = np.array([[3.1, 0.0, 0.0], [0.4, 4.2, 0.0], [0.2, 0.6, 5.3]])
    frac = np.array([[0.11, 0.23, 0.37], [0.41, 0.17, 0.83], [0.73, 0.61, 0.29]])
    original = Crystal(["Si", "O", "O"], frac, Lattice(lattice))
    transformed = Crystal(
        ["O", "Si", "O"],
        np.mod((frac @ np.linalg.inv(basis))[[1, 0, 2]] + 0.137, 1),
        Lattice(basis @ lattice),
    )
    assert StructureMatcher(ltol=1e-6, stol=1e-6, angle_tol=1e-6).fit(
        original, transformed
    )


def test_structure_matcher_tolerance_boundary_is_inclusive():
    original = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(4.0))
    boundary = Crystal(["Si"], [[0.2, 0, 0]], Lattice.cubic(4.4))
    assert StructureMatcher(ltol=0.1, stol=0.3).fit(original, boundary)
    assert not StructureMatcher(ltol=0.09, stol=0.3).fit(original, boundary)


def _standardization_cases():
    return [
        Crystal(["Si", "Si"], [[0, 0, 0], [.25, .25, .25]], Lattice.cubic(5.43)),
        Crystal(["Na", "Cl"], [[0, 0, 0], [.5, .5, .5]], Lattice.cubic(5.64)),
        Crystal(["Ti", "O", "O"], [[0, 0, 0], [.305, .305, 0], [.695, .695, 0]], Lattice.tetragonal(4.59, 2.96)),
        Crystal(["C", "C"], [[0, 0, 0], [1/3, 2/3, .5]], Lattice.hexagonal(2.46, 6.71)),
    ]


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
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="The input structure does not match the expected standard primitive")
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
@pytest.mark.parametrize("expected,structure", _metric_variant_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_every_metric_subvariant_has_exact_pymatgen_parity(expected, structure):
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer as PmgAnalyzer
    from pymatgen.symmetry.bandstructure import HighSymmKpath as PmgKpath

    native = HighSymmKpath(structure, symprec=1e-5)
    pmg = Structure(PmgLattice(structure.lattice.matrix), structure.species, structure.frac_positions)
    standardized = PmgAnalyzer(pmg, symprec=1e-5).get_primitive_standard_structure()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="The input structure does not match the expected standard primitive")
        reference = PmgKpath(standardized, path_type="setyawan_curtarolo", symprec=1e-5)
    assert native.kpath["variant"] == expected
    assert native.kpath["path"] == reference.kpath["path"]
    assert set(native.kpath["kpoints"]) == set(reference.kpath["kpoints"])
    for label, point in native.kpath["kpoints"].items():
        assert np.allclose(point, reference.kpath["kpoints"][label], atol=1e-7)
    actual_points, actual_labels = native.get_kpoints(2, coords_are_cartesian=False)
    expected_points, expected_labels = reference.get_kpoints(2, coords_are_cartesian=False)
    assert actual_labels == expected_labels
    assert len(actual_points) == len(expected_points)
    assert np.allclose(actual_points, expected_points, atol=1e-7)


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


@pytest.mark.requires_pymatgen
@pytest.mark.skipif(not HAS_PYMATGEN, reason="pymatgen required")
def test_pymatgen_2025_6_14_structure_matcher_decision_matrix():
    from pymatgen.analysis.structure_matcher import StructureMatcher as PmgMatcher
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure

    lattice = np.array([[3.1, 0, 0], [.4, 4.2, 0], [.2, .6, 5.3]])
    frac = np.array([[.11, .23, .37], [.41, .17, .83], [.73, .61, .29]])
    base = Crystal(["Si", "O", "O"], frac, Lattice(lattice))
    shear = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 1]])
    cases = [
        Crystal(base.species[::-1], np.mod(base.frac_positions[::-1] + .173, 1), base.lattice),
        Crystal(base.species, frac @ np.linalg.inv(shear), Lattice(shear @ lattice)),
        Crystal(["Si", "O", "N"], frac, base.lattice),
        Crystal(base.species, frac, Lattice(np.diag([2.0, 1.0, 1.0]) @ lattice)),
    ]

    def pmg(crystal):
        return Structure(PmgLattice(crystal.lattice.matrix), crystal.species, crystal.frac_positions)

    native = StructureMatcher()
    reference = PmgMatcher()
    assert [native.fit(base, case) for case in cases] == [
        reference.fit(pmg(base), pmg(case)) for case in cases
    ]
    skew_lattice = Lattice([[1.0, 0, 0], [.95, .2, 0], [.4, .1, 2.0]])
    skew_a = Crystal(["Si", "Si"], [[0, 0, 0], [.49, .49, 0]], skew_lattice)
    skew_b = Crystal(["Si", "Si"], [[0, 0, 0], [.51, -.49, 0]], skew_lattice)
    assert StructureMatcher(stol=.08).fit(skew_a, skew_b) == PmgMatcher(stol=.08).fit(
        pmg(skew_a), pmg(skew_b)
    )


@pytest.mark.requires_pymatgen
@pytest.mark.skipif(not (HAS_SPGLIB and HAS_PYMATGEN), reason="pymatgen and spglib required")
@pytest.mark.parametrize("structure", _standardization_cases())
def test_standardization_and_ir_mesh_coordinate_parity(structure):
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer as PmgAnalyzer

    pmg_input = Structure(
        PmgLattice(structure.lattice.matrix), structure.species, structure.frac_positions
    )
    native = SpacegroupAnalyzer(structure, symprec=1e-4)
    reference = PmgAnalyzer(pmg_input, symprec=1e-4)
    for actual, expected in [
        (native.get_primitive_standard_structure(), reference.get_primitive_standard_structure()),
        (native.get_conventional_standard_structure(), reference.get_conventional_standard_structure()),
    ]:
        expected_native = Crystal(
            [str(species) for species in expected.species],
            expected.frac_coords,
            Lattice(expected.lattice.matrix),
        )
        assert StructureMatcher(ltol=1e-7, stol=1e-7, angle_tol=1e-7).fit(
            actual, expected_native
        )
        assert sorted(actual.species) == sorted(str(species) for species in expected.species)
        assert all(species in {"Si", "Na", "Cl", "Ti", "O", "C"} for species in actual.species)

    for shift in [(0, 0, 0), (1, 0, 1)]:
        actual_points, actual_weights = native.get_ir_reciprocal_mesh((3, 4, 2), shift)
        expected_mesh = reference.get_ir_reciprocal_mesh((3, 4, 2), shift)
        actual_rows = sorted(
            (tuple(np.round(np.mod(point, 1), 8)), weight)
            for point, weight in zip(actual_points, actual_weights)
        )
        expected_rows = sorted(
            (tuple(np.round(np.mod(point, 1), 8)), weight)
            for point, weight in expected_mesh
        )
        assert actual_rows == expected_rows
