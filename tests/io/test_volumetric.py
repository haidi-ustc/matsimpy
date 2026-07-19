import json

import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import Spin
from matsimpy.io.volumetric import VolumetricData


@pytest.fixture
def si_crystal():
    return Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))


def test_volumetric_arithmetic_integral_and_roundtrip(si_crystal):
    grid = np.arange(8.0).reshape(2, 2, 2)
    volume = VolumetricData(si_crystal, {"total": grid})
    assert volume.dim == (2, 2, 2)
    assert volume.ngridpts == 8
    assert volume.value_at(1, 1, 1) == 7.0
    assert (volume + volume).data["total"][1, 1, 1] == 14.0
    assert volume.get_integrated_diff(0, 1.0).shape[1] == 2
    decoded = MontyDecoder().process_decoded(json.loads(json.dumps(volume.as_dict())))
    assert isinstance(decoded, VolumetricData)
    np.testing.assert_array_equal(decoded.data["total"], grid)


def test_validation_interpolation_spin_and_axis_average(si_crystal):
    with pytest.raises(ValueError, match="non-empty"):
        VolumetricData(si_crystal, {})
    with pytest.raises(ValueError, match="same shape"):
        VolumetricData(si_crystal, {"total": np.zeros((2, 2, 2)), "diff": np.zeros((3, 2, 2))})
    with pytest.raises(ValueError, match="three-dimensional"):
        VolumetricData(si_crystal, {"total": np.zeros((2, 2))})

    total = np.arange(8.0).reshape(2, 2, 2)
    diff = np.ones((2, 2, 2))
    volume = VolumetricData(si_crystal, {"total": total, "diff": diff}, data_aug={"total": ["aug\n"]})
    assert volume.is_spin_polarized
    assert set(volume.spin_data) == {Spin.up, Spin.down}
    np.testing.assert_allclose(volume.spin_data[Spin.up], (total + diff) / 2)
    np.testing.assert_allclose(volume.get_average_along_axis(0), total.mean(axis=(1, 2)))
    assert volume.get_interpolated_value([0.25, 0.25, 0.25]) == pytest.approx(3.5)
    assert (2 * volume - 1).data["diff"][0, 0, 0] == 1
    assert (volume / 2).data_aug == {"total": ["aug\n"]}
