import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry.kpath import HighSymmetryKpath


@pytest.mark.parametrize(
    ("lattice", "expected_type", "expected_path", "expected_points"),
    [
        (
            Lattice([[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 20.0]]),
            "square",
            ["M", "Γ", "X", "M"],
            {"X": [0.0, 0.5, 0.0], "M": [0.5, 0.5, 0.0]},
        ),
        (
            Lattice([[3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 20.0]]),
            "rectangular",
            ["Γ", "X", "S", "Y", "Γ", "S"],
            {"X": [0.5, 0.0, 0.0], "S": [0.5, 0.5, 0.0]},
        ),
        (
            Lattice.from_parameters(3.0, 3.0, 20.0, 90.0, 90.0, 70.0),
            "centered_rectangular",
            ["Γ", "X", "A1", "Y", "Γ"],
            {"Y": [0.5, 0.5, 0.0]},
        ),
        (
            Lattice.hexagonal(3.0, 20.0),
            "hexagonal",
            ["Γ", "M", "K", "Γ"],
            {"M": [0.5, 0.0, 0.0], "K": [1 / 3, 1 / 3, 0.0]},
        ),
        (
            Lattice.from_parameters(3.0, 4.0, 20.0, 90.0, 90.0, 70.0),
            "oblique",
            ["Γ", "Y", "H", "C", "H1", "X", "Γ"],
            {"X": [0.5, 0.0, 0.0], "C": [0.5, 0.5, 0.0]},
        ),
    ],
)
def test_high_symmetry_path_supports_all_five_2d_bravais_lattices(
    lattice,
    expected_type,
    expected_path,
    expected_points,
):
    """Catches missing or misclassified native 2D Bravais paths."""
    crystal = Crystal(["C"], [[0, 0, 0]], lattice, pbc=[True, True, False])

    kpath = HighSymmetryKpath(crystal)

    assert kpath.lattice_type == expected_type
    assert kpath.kpath["path"] == [expected_path]
    assert kpath.kpath["provenance"] == "native 2D Bravais-lattice table"
    for label, expected in expected_points.items():
        assert np.allclose(kpath.kpath["kpoints"][label], expected)


def test_high_symmetry_path_maps_2d_points_to_periodic_lattice_axes():
    """Catches accidental placement of 2D k-points on a non-periodic axis."""
    crystal = Crystal(
        ["C"],
        [[0, 0, 0]],
        Lattice([[4.0, 0.0, 0.0], [0.0, 20.0, 0.0], [0.0, 0.0, 3.0]]),
        pbc=[True, False, True],
    )

    kpath = HighSymmetryKpath(crystal)

    assert kpath.lattice_type == "rectangular"
    assert np.allclose(kpath.kpath["kpoints"]["X"], [0.0, 0.0, 0.5])
    assert np.allclose(kpath.kpath["kpoints"]["Y"], [0.5, 0.0, 0.0])
    assert all(point[1] == 0.0 for point in kpath.kpath["kpoints"].values())


def test_high_symmetry_path_reduces_an_equivalent_sheared_2d_basis():
    """Catches classifying a non-reduced square basis as an oblique lattice."""
    crystal = Crystal(
        ["C"],
        [[0, 0, 0]],
        Lattice([[3.0, 3.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 20.0]]),
        pbc=[True, True, False],
    )

    kpath = HighSymmetryKpath(crystal)

    assert kpath.lattice_type == "square"
    assert kpath.kpath["path"] == [["M", "Γ", "X", "M"]]


@pytest.mark.parametrize(
    ("lattice", "expected_points"),
    [
        (
            Lattice.from_parameters(3.0, 3.0, 20.0, 90.0, 90.0, 60.0),
            {"M": [0.5, 0.0, 0.0], "K": [1 / 3, -1 / 3, 0.0]},
        ),
        (
            Lattice.from_parameters(3.0, 4.0, 20.0, 90.0, 90.0, 110.0),
            {
                "Y": [0.0, -0.5, 0.0],
                "H": [0.4209887783, -0.6919821897, 0.0],
                "C": [0.5, -0.5, 0.0],
                "H1": [0.5790112217, -0.3080178103, 0.0],
                "X": [0.5, 0.0, 0.0],
            },
        ),
    ],
)
def test_high_symmetry_path_maps_canonical_tables_to_the_original_2d_basis(
    lattice,
    expected_points,
):
    """Catches returning fractions for a canonical cell instead of the input cell."""
    crystal = Crystal(["C"], [[0, 0, 0]], lattice, pbc=[True, True, False])

    kpath = HighSymmetryKpath(crystal)

    for label, expected in expected_points.items():
        assert np.allclose(kpath.kpath["kpoints"][label], expected)


def test_high_symmetry_path_has_labeled_endpoints():
    crystal = Crystal(
        ["Si"],
        [[0, 0, 0]],
        Lattice.cubic(5.43),
    )

    path = HighSymmetryKpath(crystal)
    kpoints, labels = path.get_kpoints(line_density=8)

    assert len(kpoints) == len(labels)
    assert labels[0] == "Γ"
    assert labels[-1] == "R"
    assert ["Γ", "X", "M", "Γ", "R", "X"] in path.kpath["path"]
    assert ["M", "R"] in path.kpath["path"]
    assert path.kpath["provenance"] == "native primitive-cubic table"


def test_high_symmetry_path_preserves_disconnected_segment_start_label():
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))

    path = HighSymmetryKpath(crystal)
    _, labels = path.get_kpoints(line_density=2)

    assert labels[11] == "M"


def test_high_symmetry_path_rejects_unsupported_crystal_system():
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice([4.0, 4.0, 6.0]))

    with pytest.raises(NotImplementedError, match="Tetragonal"):
        HighSymmetryKpath(crystal)


@pytest.mark.parametrize("line_density", [True, 0, -1, 1.5, "4"])
def test_high_symmetry_path_rejects_invalid_line_density(line_density):
    """Catches acceptance of values that cannot define interpolation intervals."""
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    path = HighSymmetryKpath(crystal)

    with pytest.raises(ValueError, match="positive integer"):
        path.get_kpoints(line_density=line_density)


def test_high_symmetry_path_rejects_non_boolean_cartesian_flag():
    """Catches truthy values silently changing the coordinate convention."""
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    path = HighSymmetryKpath(crystal)

    with pytest.raises(TypeError, match="coords_are_cartesian"):
        path.get_kpoints(coords_are_cartesian="yes")


@pytest.mark.parametrize(
    "pbc",
    [
        [False, False, False],
        [True, False, False],
    ],
)
def test_high_symmetry_path_rejects_non_2d_non_3d_periodicity(pbc):
    """Catches silently applying a 3D table to zero- or one-dimensional cells."""
    crystal = Crystal(["C"], [[0, 0, 0]], Lattice.cubic(5.0), pbc=pbc)

    with pytest.raises(NotImplementedError, match="periodic dimensions"):
        HighSymmetryKpath(crystal)


@pytest.mark.parametrize(
    ("crystal", "space_group"),
    [
        (
            Crystal(
                ["Fe", "Fe"],
                [[0, 0, 0], [0.5, 0.5, 0.5]],
                Lattice.cubic(2.87),
            ),
            "Im-3m",
        ),
        (
            Crystal(
                ["Cu"] * 4,
                [
                    [0, 0, 0],
                    [0, 0.5, 0.5],
                    [0.5, 0, 0.5],
                    [0.5, 0.5, 0],
                ],
                Lattice.cubic(3.61),
            ),
            "Fm-3m",
        ),
        (
            Crystal(
                ["Si"] * 8,
                [
                    [0, 0, 0],
                    [0, 0.5, 0.5],
                    [0.5, 0, 0.5],
                    [0.5, 0.5, 0],
                    [0.25, 0.25, 0.25],
                    [0.25, 0.75, 0.75],
                    [0.75, 0.25, 0.75],
                    [0.75, 0.75, 0.25],
                ],
                Lattice.cubic(5.43),
            ),
            "Fd-3m",
        ),
    ],
)
def test_high_symmetry_path_rejects_non_primitive_cubic_structures(
    crystal,
    space_group,
):
    with pytest.raises(NotImplementedError, match=space_group):
        HighSymmetryKpath(crystal)
