import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import (
    BandStructure,
    BandStructureSymmLine,
    Spin,
    get_reconstructed_band_structure,
)


@pytest.fixture
def si_crystal():
    return Crystal(["Si"], [[0.0, 0.0, 0.0]], Lattice.cubic(4.0))


@pytest.fixture
def two_band_branches(si_crystal):
    lattice = si_crystal.lattice.get_reciprocal_lattice()
    return [
        BandStructureSymmLine(
            [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
            {Spin.up: [[-1.0, -0.5], [1.0, 1.5]]},
            lattice,
            0.0,
            labels_dict={"G": [0.0, 0.0, 0.0]},
            structure=si_crystal,
        ),
        BandStructureSymmLine(
            [[0.5, 0.0, 0.0], [1.0, 0.0, 0.0]],
            {Spin.up: [[-0.4, -0.2], [1.6, 2.0]]},
            lattice,
            0.0,
            labels_dict={"X": [1.0, 0.0, 0.0]},
            structure=si_crystal,
        ),
    ]


def test_band_structure_detects_crossing_band(si_crystal):
    bands = {Spin.up: np.array([[-1.0, 1.0]])}
    bs = BandStructure(
        [[0, 0, 0], [0.5, 0, 0]],
        bands,
        si_crystal.lattice.get_reciprocal_lattice(),
        0.0,
        structure=si_crystal,
    )

    assert bs.is_metal()


def test_band_gap_uses_fermi_level_edges(si_crystal):
    bs = BandStructure(
        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
        {Spin.up: [[-1.0, -0.5], [1.25, 1.5]]},
        si_crystal.lattice.get_reciprocal_lattice(),
        0.0,
        structure=si_crystal,
    )

    assert bs.get_band_gap()["energy"] == pytest.approx(1.75)


def test_reconstruct_concatenates_branch_kpoints(two_band_branches):
    result = get_reconstructed_band_structure(two_band_branches, efermi=0.25)

    assert len(result.kpoints) == sum(len(branch.kpoints) for branch in two_band_branches)
    assert result.efermi == 0.25
    assert result.bands[Spin.up].shape == (2, 4)


def test_symm_line_roundtrip_preserves_labels_and_bands(two_band_branches):
    restored = BandStructureSymmLine.from_dict(two_band_branches[0].as_dict())

    assert restored.labels_dict == {"G": [0.0, 0.0, 0.0]}
    assert restored.bands[Spin.up] == pytest.approx(two_band_branches[0].bands[Spin.up])


def test_reconstruct_rejects_mismatched_branch_band_count(two_band_branches):
    other = BandStructureSymmLine(
        [[0.0, 0.0, 0.0]],
        {Spin.up: [[-1.0], [0.5], [1.0]]},
        two_band_branches[0].lattice,
        0.0,
        labels_dict={},
    )

    with pytest.raises(ValueError, match="band dimensions"):
        get_reconstructed_band_structure([two_band_branches[0], other])


def test_reconstruct_concatenates_branch_projections(si_crystal):
    lattice = si_crystal.lattice.get_reciprocal_lattice()
    branches = [
        BandStructure(
            [[0.0, 0.0, 0.0]],
            {Spin.up: [[-1.0]]},
            lattice,
            0.0,
            projections={Spin.up: [[[0.25]]]},
        ),
        BandStructure(
            [[0.5, 0.0, 0.0]],
            {Spin.up: [[1.0]]},
            lattice,
            0.0,
            projections={Spin.up: [[[0.75]]]},
        ),
    ]

    result = get_reconstructed_band_structure(branches)

    np.testing.assert_allclose(result.projections[Spin.up], [[[0.25], [0.75]]])


def test_band_structure_rejects_wrong_kpoint_dimension(si_crystal):
    with pytest.raises(ValueError, match="kpoints"):
        BandStructure(
            [[0.0, 0.0]],
            {Spin.up: [[-1.0]]},
            si_crystal.lattice.get_reciprocal_lattice(),
            0.0,
        )
