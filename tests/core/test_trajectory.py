import json

import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.core import Crystal, Lattice, Trajectory


@pytest.fixture
def si_crystal():
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.4))


def test_trajectory_from_structures_keeps_variable_lattices(si_crystal):
    expanded = Crystal(si_crystal.species, si_crystal.frac_positions, Lattice.cubic(6.0))
    trajectory = Trajectory.from_structures([si_crystal, expanded], constant_lattice=False)
    assert len(trajectory) == 2
    assert trajectory[1].lattice == expanded.lattice
    assert list(trajectory)[0] == si_crystal
    assert len(trajectory[:1]) == 1


def test_trajectory_constant_lattice_rejects_changes(si_crystal):
    expanded = Crystal(si_crystal.species, si_crystal.frac_positions, Lattice.cubic(6.0))
    with pytest.raises(ValueError, match="constant_lattice"):
        Trajectory.from_structures([si_crystal, expanded], constant_lattice=True)


def test_trajectory_copies_frames_and_roundtrips(si_crystal):
    si_crystal._extra_properties = {"forces": [[1, 2, 3], [4, 5, 6]]}
    trajectory = Trajectory.from_structures([si_crystal])
    frame = trajectory[0]
    assert frame is not si_crystal
    decoded = MontyDecoder().process_decoded(trajectory.as_dict())
    assert decoded[0] == si_crystal
    assert decoded[0]._extra_properties == si_crystal._extra_properties


def test_trajectory_recursively_serializes_extra_metadata(si_crystal):
    extras = {
        "nested": [{"lattice": Lattice.cubic(3), "label": "Si"}],
        "values": np.array([1.0, 2.0]),
    }
    si_crystal._extra_properties = extras
    trajectory = Trajectory.from_structures([si_crystal])

    serialized = trajectory.as_dict()
    json.dumps(serialized)
    restored = MontyDecoder().process_decoded(serialized)

    restored_extras = restored[0]._extra_properties
    assert restored_extras["nested"][0]["lattice"] == Lattice.cubic(3)
    assert restored_extras["nested"][0]["label"] == "Si"
    assert restored_extras["values"] == [1.0, 2.0]
    assert isinstance(extras["nested"][0]["lattice"], Lattice)
    assert isinstance(extras["values"], np.ndarray)


def _metadata_trajectory(si_crystal):
    frames = []
    for index in range(4):
        frame = Crystal(
            si_crystal.species,
            si_crystal.frac_positions + index * 0.01,
            si_crystal.lattice,
        )
        frame._extra_properties = {"index": index, "nested": {"values": [index]}}
        frames.append(frame)
    return Trajectory(
        frames,
        constant_lattice=True,
        frame_properties=[{"energy": -index} for index in range(4)],
        charge=1.5,
        spin=2.0,
        spin_multiplicity=3,
        time_step=0.5,
        coords_are_displacement=True,
        base_positions=si_crystal.frac_positions,
    )


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        (slice(1, 3), [1, 2]),
        (slice(None, None, 2), [0, 2]),
        ([3, 1], [3, 1]),
        (np.array([2, 0]), [2, 0]),
    ],
)
def test_trajectory_selection_subsets_frames_and_preserves_metadata(
    si_crystal, selection, expected
):
    trajectory = _metadata_trajectory(si_crystal)

    selected = trajectory[selection]

    assert [frame._extra_properties["index"] for frame in selected] == expected
    assert selected.frame_properties == tuple({"energy": -index} for index in expected)
    assert selected.constant_lattice is True
    assert selected.charge == 1.5
    assert selected.spin == 2.0
    assert selected.spin_multiplicity == 3
    assert selected.time_step == 0.5
    assert selected.coords_are_displacement is True
    assert np.array_equal(selected.base_positions, trajectory.base_positions)


def test_trajectory_empty_slice_preserves_metadata(si_crystal):
    trajectory = _metadata_trajectory(si_crystal)

    selected = trajectory[1:1]

    assert len(selected) == 0
    assert selected.frame_properties == ()
    assert selected.constant_lattice is True
    assert selected.coords_are_displacement is True
    assert np.array_equal(selected.base_positions, trajectory.base_positions)


def test_trajectory_slice_roundtrips_metadata_and_is_independent(si_crystal):
    trajectory = _metadata_trajectory(si_crystal)
    selected = trajectory[1:3]

    restored = MontyDecoder().process_decoded(selected.as_dict())
    selected.frame_properties[0]["energy"] = 99
    selected[0]._extra_properties["nested"]["values"].append(99)
    selected.base_positions[0, 0] = 99

    assert restored.frame_properties == ({"energy": -1}, {"energy": -2})
    assert restored[0]._extra_properties["index"] == 1
    assert trajectory.frame_properties[1] == {"energy": -1}
    assert trajectory[1]._extra_properties["nested"]["values"] == [1]
    assert trajectory.base_positions[0, 0] != 99


def test_trajectory_integer_selection_remains_independent_crystal(si_crystal):
    trajectory = _metadata_trajectory(si_crystal)

    selected = trajectory[1]
    selected._extra_properties["nested"]["values"].append(99)

    assert isinstance(selected, Crystal)
    assert trajectory[1]._extra_properties["nested"]["values"] == [1]
