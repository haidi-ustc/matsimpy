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


def test_high_symmetry_path_rejects_unsupported_crystal_system():
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice([4.0, 4.0, 6.0]))

    with pytest.raises(NotImplementedError, match="Tetragonal"):
        HighSymmetryKpath(crystal)
