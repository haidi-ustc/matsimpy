import inspect
from collections.abc import Mapping

import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import CompleteDos, Dos, Orbital, Spin


class _UnhashableSiteMapping(Mapping):
    def __init__(self, pairs):
        self._pairs = pairs

    def __getitem__(self, key):
        for candidate, value in self._pairs:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (site for site, _ in self._pairs)

    def __len__(self):
        return len(self._pairs)


def test_dos_density_interpolation_gap_and_roundtrip():
    dos = Dos(0.0, [-2, -1, 0, 1, 2], {Spin.up: [1, 0, 0, 0, 1]})

    assert dos.get_densities(Spin.up).shape == (5,)
    assert dos.get_interpolated_value(1.5)[Spin.up] == 0.5
    assert dos.get_gap(tol=1e-8) == 4.0
    restored = MontyDecoder().process_decoded(dos.as_dict())
    assert np.array_equal(restored.energies, dos.energies)


def test_dos_validates_equal_length_one_dimensional_arrays():
    with pytest.raises(ValueError, match="equal-length 1D arrays"):
        Dos(0, [[0, 1]], {Spin.up: [1, 2]})
    with pytest.raises(ValueError, match="equal-length 1D arrays"):
        Dos(0, [0, 1], {Spin.up: [1]})


def test_complete_dos_site_projection_normalization_and_roundtrip():
    structure = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))
    total = Dos(0, [-1, 1], {Spin.up: [8, 16]})
    pdos = [{Orbital.s: {Spin.up: np.array([4, 12])}}]

    complete = CompleteDos(structure, total, pdos, normalize=True)

    assert complete.get_normalized() is complete
    assert complete.norm_vol == pytest.approx(8)
    np.testing.assert_allclose(complete.densities[Spin.up], [1, 2])
    np.testing.assert_allclose(
        complete.get_site_orbital_dos(structure[0], Orbital.s).densities[Spin.up],
        [0.5, 1.5],
    )
    restored = MontyDecoder().process_decoded(complete.as_dict())
    assert isinstance(restored, CompleteDos)
    assert restored.norm_vol == pytest.approx(8)
    np.testing.assert_allclose(restored.densities[Spin.up], [1, 2])
    np.testing.assert_allclose(
        restored.get_site_orbital_dos(restored.structure[0], Orbital.s).densities[Spin.up],
        [0.5, 1.5],
    )


def test_complete_dos_pdos_has_full_mapping_semantics_for_unhashable_sites():
    structure = Crystal(["Si", "Ge"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(4))
    complete = CompleteDos(
        structure,
        Dos(0, [-1, 1], {Spin.up: [1, 2]}),
        [
            {Orbital.s: {Spin.up: [10, 11]}},
            {Orbital.s: {Spin.up: [20, 21]}},
        ],
    )

    assert isinstance(complete.pdos, Mapping)
    assert list(complete.pdos) == list(structure)
    assert list(complete.pdos.keys()) == list(structure)
    assert list(complete.pdos.values()) == [complete.pdos[site] for site in structure]
    assert list(complete.pdos.items()) == [(site, complete.pdos[site]) for site in structure]
    assert complete.pdos.get(structure[0]) is complete.pdos[structure[0]]
    assert complete.pdos.get(object(), "missing") == "missing"
    assert structure[0] in complete.pdos
    assert object() not in complete.pdos
    assert len(complete.pdos) == len(structure)


def test_complete_dos_mapping_input_is_resolved_by_site_not_insertion_order():
    structure = Crystal(["Si", "Ge"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(4))
    equal_structure = Crystal.from_dict(structure.as_dict())
    first = {Orbital.s: {Spin.up: [10, 11]}}
    second = {Orbital.s: {Spin.up: [20, 21]}}
    reversed_pdos = _UnhashableSiteMapping([
        (equal_structure[1], second),
        (equal_structure[0], first),
    ])

    complete = CompleteDos(structure, Dos(0, [-1, 1], {Spin.up: [1, 2]}), reversed_pdos)

    np.testing.assert_array_equal(complete.pdos[structure[0]][Orbital.s][Spin.up], [10, 11])
    np.testing.assert_array_equal(complete.pdos[structure[1]][Orbital.s][Spin.up], [20, 21])


@pytest.mark.parametrize("density", ([[1, 2]], [1]))
def test_complete_dos_validates_each_projected_spin_density(density):
    structure = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))
    total = Dos(0, [-1, 1], {Spin.up: [1, 2]})

    with pytest.raises(ValueError, match="equal-length 1D arrays"):
        CompleteDos(structure, total, [{Orbital.s: {Spin.up: density}}])


def test_dos_implementation_uses_python_39_compatible_zip():
    import matsimpy.electronic_structure.dos as dos_module

    assert "strict=True" not in inspect.getsource(dos_module)
