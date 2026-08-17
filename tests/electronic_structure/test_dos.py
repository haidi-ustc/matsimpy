import json

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import CompleteDos, Dos, Orbital, OrbitalType, Spin


@pytest.fixture
def si_crystal():
    return Crystal(["Si"], [[0.0, 0.0, 0.0]], Lattice.cubic(4.0))


def test_complete_dos_normalizes_by_native_volume(si_crystal):
    total = Dos(0.0, [-1.0, 1.0], {Spin.up: [2.0, 4.0]})
    complete = CompleteDos(si_crystal, total, {}, normalize=True)

    assert complete.total_dos.densities[Spin.up] == pytest.approx(
        np.array([2.0, 4.0]) / si_crystal.volume
    )


def test_complete_dos_normalizes_projected_dos_by_native_volume(si_crystal):
    total = Dos(0.0, [-1.0, 1.0], {Spin.up: [2.0, 4.0]})
    complete = CompleteDos(
        si_crystal,
        total,
        {0: {OrbitalType.p: {Spin.up: [8.0, 16.0]}}},
        normalize=True,
    )

    assert complete.pdos[0][OrbitalType.p][Spin.up] == pytest.approx(
        np.array([8.0, 16.0]) / si_crystal.volume
    )


def test_dos_roundtrip_serializes_spin_keys_by_name():
    dos = Dos(1.5, [-2.0, 0.0, 2.0], {Spin.up: [0.0, 1.0, 0.0]})

    data = dos.as_dict()
    restored = Dos.from_dict(data)

    assert data["densities"] == {"up": [0.0, 1.0, 0.0]}
    assert restored.efermi == 1.5
    assert restored.densities[Spin.up] == pytest.approx([0.0, 1.0, 0.0])


def test_dos_rejects_density_length_mismatch():
    with pytest.raises(ValueError, match="Density length"):
        Dos(0.0, [-1.0, 1.0], {Spin.up: [2.0]})


def test_complete_dos_roundtrip_restores_projected_dos_key_types(si_crystal):
    complete = CompleteDos(
        si_crystal,
        Dos(0.0, [-1.0, 1.0], {Spin.up: [2.0, 4.0]}),
        {0: {Orbital.py: {Spin.up: np.array([0.25, 0.5])}}},
    )

    data = json.loads(json.dumps(complete.as_dict()))
    restored = CompleteDos.from_dict(data)

    assert set(restored.pdos) == {0}
    assert set(restored.pdos[0]) == {Orbital.py}
    assert set(restored.pdos[0][Orbital.py]) == {Spin.up}
    assert isinstance(restored.pdos[0][Orbital.py][Spin.up], np.ndarray)
    np.testing.assert_allclose(restored.pdos[0][Orbital.py][Spin.up], [0.25, 0.5])
