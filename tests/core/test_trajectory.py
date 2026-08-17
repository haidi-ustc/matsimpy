import pytest

from matsimpy.core import Crystal, Lattice, Trajectory


@pytest.fixture
def si_crystal():
    return Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))


def test_trajectory_roundtrip_preserves_native_structures(si_crystal):
    trajectory = Trajectory.from_structures(
        [si_crystal, si_crystal.copy()], constant_lattice=False
    )
    restored = Trajectory.from_dict(trajectory.as_dict())
    assert len(restored) == 2
    assert all(isinstance(frame, Crystal) for frame in restored)
    assert restored.constant_lattice is False


def test_trajectory_supports_iteration_and_indexing(si_crystal):
    second_frame = si_crystal.copy()
    trajectory = Trajectory.from_structures([si_crystal, second_frame])

    assert len(trajectory) == 2
    assert list(trajectory) == [si_crystal, second_frame]
    assert trajectory[0] is si_crystal
    assert trajectory[1] is second_frame


def test_trajectory_rejects_empty_structures():
    with pytest.raises(ValueError, match="Trajectory requires at least one structure"):
        Trajectory.from_structures([])
