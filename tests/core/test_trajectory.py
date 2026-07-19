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
