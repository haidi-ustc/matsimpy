
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
    si_crystal = si_crystal.with_metadata(forces=[[1, 2, 3], [4, 5, 6]])
    trajectory = Trajectory.from_structures([si_crystal])
    frame = trajectory[0]
    assert frame is not si_crystal
    decoded = MontyDecoder().process_decoded(trajectory.as_dict())
    assert decoded[0] == si_crystal
    assert decoded[0].metadata == si_crystal.metadata


def _metadata_trajectory(si_crystal):
    frames = []
    for index in range(4):
        frame = Crystal(
            si_crystal.species,
            si_crystal.frac_positions + index * 0.01,
            si_crystal.lattice,
            metadata={"index": index, "nested": {"values": [index]}, "energy": -index},
        )
        frames.append(frame)
    return Trajectory(
        frames,
        constant_lattice=True,
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

    assert [frame.metadata["index"] for frame in selected] == expected
    assert [frame.metadata["energy"] for frame in selected] == [-index for index in expected]
    assert selected.constant_lattice is True
    assert selected.charge == 1.5
    assert selected.spin == 2.0
    assert selected.spin_multiplicity == 3
    assert selected.time_step == 0.5
    assert selected.coords_are_displacement is True
    assert np.array_equal(selected.base_positions, trajectory.base_positions)


def test_trajectory_slice_roundtrips_metadata_and_is_independent(si_crystal):
    trajectory = _metadata_trajectory(si_crystal)
    selected = trajectory[1:3]

    restored = MontyDecoder().process_decoded(selected.as_dict())
    selected[0].metadata["nested"]["values"].append(99)  # deep-copied view: no effect
    with pytest.raises(ValueError):
        selected.base_positions[0, 0] = 99  # read-only since 0.8.1
    assert [f.metadata["energy"] for f in restored] == [-1, -2]
    assert restored[0].metadata["index"] == 1
    assert trajectory[1].metadata["nested"]["values"] == [1]
    assert trajectory.base_positions[0, 0] != 99


def test_trajectory_integer_selection_remains_independent_crystal(si_crystal):
    trajectory = _metadata_trajectory(si_crystal)

    selected = trajectory[1]
    selected.metadata["nested"]["values"].append(99)
    with pytest.raises(TypeError):
        selected.metadata["index"] = 7  # read-only mapping

    assert isinstance(selected, Crystal)
    assert trajectory[1].metadata["nested"]["values"] == [1]


def test_trajectory_reads_pre_087_extra_properties_block(si_crystal):
    """Files written by <=0.8.6 stored frame data next to the structure."""
    d = Trajectory.from_structures([si_crystal]).as_dict()
    d["frames"][0]["extra_properties"] = {"forces": [[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]}
    restored = Trajectory.from_dict(d)
    assert restored[0].metadata["forces"] == [[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]


def test_trajectory_reads_pre_090_frame_properties(si_crystal):
    """<=0.8.7 files stored per-frame dicts in a parallel "frame_properties" list."""
    d = Trajectory.from_structures([si_crystal, si_crystal]).as_dict()
    d["frame_properties"] = [{"energy": -1.0}, {"energy": -2.0}]
    restored = Trajectory.from_dict(d)
    assert [f.metadata["energy"] for f in restored] == [-1.0, -2.0]
    assert "frame_properties" not in Trajectory.from_structures([si_crystal]).as_dict()


@pytest.mark.parametrize("change", [lambda c: c.remove_atom(0), lambda c: c.substitute(0, "Ge")])
def test_frames_must_have_the_same_atoms(si_crystal, change):
    with pytest.raises(ValueError, match="same atoms"):
        Trajectory([si_crystal, change(si_crystal)])


@pytest.mark.parametrize("kwargs", [
    {"time_step": float("nan")},
    {"time_step": -1.0},
    {"coords_are_displacement": True},  # needs base_positions
    {"base_positions": [[0, 0, 0]]},
    {"base_positions": [[0, 0, 0], [np.nan, 0, 0]]},
])
def test_invalid_scalars_and_base_positions_are_rejected(si_crystal, kwargs):
    with pytest.raises(ValueError):
        Trajectory([si_crystal], **kwargs)


def test_trajectory_is_immutable(si_crystal):
    traj = Trajectory([si_crystal.with_metadata(e={"v": 1}), si_crystal.with_metadata(e={"v": 2})],
                      base_positions=[[0, 0, 0], [1, 1, 1]])
    traj[0].metadata["e"]["v"] = 99
    assert traj[0].metadata["e"]["v"] == 1
    with pytest.raises(ValueError):
        traj.base_positions[0, 0] = 5.0
    with pytest.raises(AttributeError):
        traj.constant_lattice = True
    assert all(f is not g for f, g in zip(list(traj), traj._frames))  # iteration yields copies


def test_trajectory_stays_frozen_after_pickle(si_crystal):
    import pickle

    traj = Trajectory([si_crystal], base_positions=[[0, 0, 0], [1, 1, 1]])
    with pytest.raises(ValueError):
        pickle.loads(pickle.dumps(traj)).base_positions.flags.writeable = True
