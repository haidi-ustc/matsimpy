import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import Spin
from matsimpy.io import VolumetricData


@pytest.fixture
def si_crystal():
    return Crystal(["Si"], [[0.0, 0.0, 0.0]], Lattice.cubic(4.0))


def test_volumetric_data_derives_grid_and_spin(si_crystal):
    total = np.arange(8, dtype=float).reshape(2, 2, 2)
    diff = np.ones((2, 2, 2))
    volume = VolumetricData(si_crystal, {"total": total, "diff": diff})

    assert volume.dim == (2, 2, 2)
    assert volume.ngridpts == 8
    assert volume.is_spin_polarized
    assert not volume.is_soc
    np.testing.assert_allclose(volume.spin_data[Spin.up], (total + diff) / 2)
    np.testing.assert_allclose(volume.spin_data[Spin.down], (total - diff) / 2)


def test_volumetric_data_detects_soc_from_four_channels(si_crystal):
    data = {
        "total": np.zeros((2, 2, 2)),
        "diff_x": np.ones((2, 2, 2)),
        "diff_y": np.ones((2, 2, 2)) * 2,
        "diff_z": np.ones((2, 2, 2)) * 3,
    }

    volume = VolumetricData(si_crystal, data)

    assert not volume.is_spin_polarized
    assert volume.is_soc


def test_volumetric_data_soc_requires_expected_vector_keys(si_crystal):
    volume = VolumetricData(
        si_crystal,
        {
            "total": np.zeros((2, 2, 2)),
            "a": np.ones((2, 2, 2)),
            "b": np.ones((2, 2, 2)),
            "c": np.ones((2, 2, 2)),
        },
    )
    incomplete_soc = VolumetricData(
        si_crystal,
        {
            "total": np.zeros((2, 2, 2)),
            "diff_x": np.ones((2, 2, 2)),
            "diff_y": np.ones((2, 2, 2)),
        },
    )

    assert not volume.is_soc
    assert not volume.is_spin_polarized
    assert not incomplete_soc.is_soc
    assert not incomplete_soc.is_spin_polarized


def test_volumetric_data_rejects_collinear_spin_data_for_soc(si_crystal):
    volume = VolumetricData(
        si_crystal,
        {
            "total": np.zeros((2, 2, 2)),
            "diff_x": np.ones((2, 2, 2)),
            "diff_y": np.ones((2, 2, 2)),
            "diff_z": np.ones((2, 2, 2)),
        },
    )

    with pytest.raises(ValueError, match="SOC"):
        _ = volume.spin_data


def test_volumetric_data_requires_matching_three_dimensional_shapes(si_crystal):
    with pytest.raises(ValueError, match="three-dimensional"):
        VolumetricData(si_crystal, {"total": np.zeros((2, 2))})

    with pytest.raises(ValueError, match="same shape"):
        VolumetricData(
            si_crystal,
            {"total": np.zeros((2, 2, 2)), "diff": np.zeros((2, 2, 3))},
        )


def test_volumetric_data_rejects_non_positive_grid_extents(si_crystal):
    with pytest.raises(ValueError, match="positive"):
        VolumetricData(si_crystal, {"total": np.zeros((0, 2, 2))})


def test_get_axis_grid_uses_native_lattice_lengths(si_crystal):
    volume = VolumetricData(si_crystal, {"total": np.zeros((2, 4, 1))})

    assert volume.get_axis_grid(0) == pytest.approx([0.0, 2.0])
    assert volume.get_axis_grid(1) == pytest.approx([0.0, 1.0, 2.0, 3.0])
    assert volume.get_axis_grid(2) == pytest.approx([0.0])


def test_value_at_periodically_trilinearly_samples_total_channel(si_crystal):
    total = np.array(
        [
            [[0.0, 4.0], [2.0, 6.0]],
            [[1.0, 5.0], [3.0, 7.0]],
        ]
    )
    volume = VolumetricData(si_crystal, {"total": total})

    assert volume.value_at(0.5, 0.0, 0.0) == pytest.approx(1.0)
    assert volume.value_at(0.25, 0.25, 0.25) == pytest.approx(3.5)
    assert volume.value_at(1.25, -0.75, 0.25) == pytest.approx(3.5)


def test_volumetric_data_adds_and_subtracts_matching_channels(si_crystal):
    left = VolumetricData(
        si_crystal,
        {"total": np.ones((2, 2, 2)), "diff": np.ones((2, 2, 2)) * 2},
    )
    right = VolumetricData(
        si_crystal,
        {"total": np.ones((2, 2, 2)) * 3, "diff": np.ones((2, 2, 2))},
    )

    summed = left + right
    difference = left - right

    np.testing.assert_allclose(summed.data["total"], np.ones((2, 2, 2)) * 4)
    np.testing.assert_allclose(summed.data["diff"], np.ones((2, 2, 2)) * 3)
    np.testing.assert_allclose(difference.data["total"], np.ones((2, 2, 2)) * -2)
    np.testing.assert_allclose(difference.data["diff"], np.ones((2, 2, 2)))
    assert summed.data_aug == {}


def test_volumetric_data_rejects_linear_arithmetic_with_different_channels(si_crystal):
    left = VolumetricData(si_crystal, {"total": np.ones((2, 2, 2))})
    right = VolumetricData(
        si_crystal,
        {"total": np.ones((2, 2, 2)), "diff": np.ones((2, 2, 2))},
    )

    with pytest.raises(ValueError, match="different keys"):
        _ = left + right


def test_volumetric_data_preserves_augmentation_payload(si_crystal):
    data_aug = {"total": ["augmentation line"]}

    volume = VolumetricData(si_crystal, {"total": np.zeros((2, 2, 2))}, data_aug=data_aug)

    assert volume.data_aug is data_aug
