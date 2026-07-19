import json

import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import ComputedEntry, ComputedStructureEntry


@pytest.fixture
def si_crystal():
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.4))


def test_computed_structure_entry_energy_and_roundtrip(si_crystal):
    entry = ComputedStructureEntry(si_crystal, -10.0, correction=0.25, entry_id="si")
    assert entry.energy == -9.75
    assert entry.energy_per_atom == pytest.approx(-4.875)
    decoded = MontyDecoder().process_decoded(entry.as_dict())
    assert decoded.structure == si_crystal
    assert decoded.uncorrected_energy == -10.0
    assert decoded.entry_id == "si"


def test_computed_entry_preserves_metadata_without_aliasing():
    parameters = {"run_type": "GGA"}
    data = {"tag": [1]}
    entry = ComputedEntry("Si2", -4, parameters=parameters, data=data)
    parameters["run_type"] = "changed"
    data["tag"].append(2)
    assert entry.parameters == {"run_type": "GGA"}
    assert entry.data == {"tag": [1]}
    decoded = MontyDecoder().process_decoded(entry.as_dict())
    assert decoded.composition == entry.composition
    assert decoded.parameters == entry.parameters
    assert decoded.data == entry.data


@pytest.mark.parametrize("entry_type", [ComputedEntry, ComputedStructureEntry])
def test_computed_entries_recursively_serialize_metadata(entry_type, si_crystal):
    parameters = {"nested": [{"lattice": Lattice.cubic(3), "values": np.array([1, 2])}]}
    data = {"label": "Si", "scalar": np.float64(1.5)}
    subject = si_crystal if entry_type is ComputedStructureEntry else "Si2"
    entry = entry_type(subject, -4, parameters=parameters, data=data)

    serialized = entry.as_dict()
    json.dumps(serialized)
    restored = MontyDecoder().process_decoded(serialized)

    assert restored.parameters["nested"][0]["lattice"] == Lattice.cubic(3)
    assert restored.parameters["nested"][0]["values"] == [1, 2]
    assert restored.data["label"] == "Si"
    assert restored.data["scalar"] == 1.5
    assert isinstance(parameters["nested"][0]["lattice"], Lattice)
    assert isinstance(parameters["nested"][0]["values"], np.ndarray)
