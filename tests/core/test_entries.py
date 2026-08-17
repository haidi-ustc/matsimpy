import pytest

from matsimpy.core import (
    Composition,
    Crystal,
    ComputedEntry,
    ComputedStructureEntry,
    Lattice,
)


@pytest.fixture
def si_crystal():
    return Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))


def test_computed_entry_defensively_copies_metadata():
    parameters = {"run_type": "GGA"}
    data = {"efermi": 5.1}

    entry = ComputedEntry(Composition("Si"), -5.0, parameters=parameters, data=data)
    parameters["run_type"] = "LDA"
    data["efermi"] = 4.8

    assert entry.parameters == {"run_type": "GGA"}
    assert entry.data == {"efermi": 5.1}


def test_computed_structure_entry_uses_native_crystal(si_crystal):
    entry = ComputedStructureEntry(si_crystal, -5.0, parameters={"run_type": "GGA"})
    assert entry.structure is si_crystal
    assert entry.composition == si_crystal.composition
    assert entry.energy == -5.0
    assert entry.parameters == {"run_type": "GGA"}


def test_computed_structure_entry_roundtrip_restores_native_crystal(si_crystal):
    entry = ComputedStructureEntry(
        si_crystal,
        -5.0,
        parameters={"run_type": "GGA"},
        data={"task_id": "vasp-1"},
        entry_id="entry-1",
    )

    restored = ComputedStructureEntry.from_dict(entry.as_dict())

    assert isinstance(restored.structure, Crystal)
    assert restored.composition == si_crystal.composition
    assert restored.energy == -5.0
    assert restored.parameters == {"run_type": "GGA"}
    assert restored.data == {"task_id": "vasp-1"}
    assert restored.entry_id == "entry-1"
