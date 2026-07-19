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
    with pytest.raises(ValueError, match="non-zero"):
        VolumetricData(si_crystal, {"total": np.zeros((2, 0, 2))})

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


def test_minimum_image_distances_match_brute_force_for_skew_lattice():
    lattice = Lattice([[1.0, 0.0, 0.0], [0.9, 0.2, 0.0], [0.1, 0.1, 1.0]])
    crystal = Crystal(["Si"], [[0.17, 0.31, 0.43]], lattice)
    volume = VolumetricData(crystal, {"total": np.ones((3, 4, 2))})

    grid = np.indices(volume.dim).transpose(1, 2, 3, 0) / np.asarray(volume.dim)
    delta = grid - crystal.frac_positions[0]
    translations = np.asarray(list(np.ndindex(9, 9, 9))) - 4
    expected = np.min(
        np.linalg.norm((delta[..., None, :] + translations) @ lattice.matrix, axis=-1),
        axis=-1,
    )
    np.testing.assert_allclose(volume._distances_from_site(0), expected, atol=1e-12)


def test_large_radius_counts_each_periodic_grid_sample_once(si_crystal):
    volume = VolumetricData(si_crystal, {"total": np.ones((2, 2, 2))})
    assert volume.get_integrated_diff(0, 100.0)[-1, 1] == pytest.approx(1.0)


def test_supplied_distance_matrix_is_used_and_validated(si_crystal):
    distances = np.full((1, 2, 2, 2), 99.0)
    volume = VolumetricData(si_crystal, {"total": np.ones((2, 2, 2))}, distance_matrix=distances)
    assert volume.get_integrated_diff(0, 1.0)[-1, 1] == 0
    assert volume._distances_from_site(0) is volume._distances_from_site(0)

    with pytest.raises(ValueError, match="distance_matrix"):
        VolumetricData(
            si_crystal,
            {"total": np.ones((2, 2, 2))},
            distance_matrix=np.zeros((2, 2)),
        )


def test_cached_distance_matrix_json_roundtrip_preserves_sparse_cache():
    crystal = Crystal(["Si", "Ge"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2))
    distances = {1: np.full((2, 2, 2), 99.0)}
    volume = VolumetricData(crystal, {"total": np.ones((2, 2, 2))}, distance_matrix=distances)

    serialized = json.loads(json.dumps(volume.as_dict()))
    assert serialized["distance_matrix"] == {"1": distances[1].tolist()}
    restored = MontyDecoder().process_decoded(serialized)

    assert set(restored._distance_matrix) == {1}
    assert restored.get_integrated_diff(1, 1.0)[-1, 1] == 0


@pytest.mark.parametrize("invalid_key", ["site-0", "1.5", "-1", "2"])
def test_cached_distance_matrix_json_keys_are_validated(invalid_key):
    crystal = Crystal(["Si", "Ge"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2))
    payload = VolumetricData(crystal, {"total": np.ones((2, 2, 2))}).as_dict()
    payload["distance_matrix"] = {invalid_key: np.zeros((2, 2, 2)).tolist()}

    with pytest.raises(ValueError, match="invalid site index"):
        MontyDecoder().process_decoded(json.loads(json.dumps(payload)))
