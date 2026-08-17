import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry.kpath import HighSymmetryKpath


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
