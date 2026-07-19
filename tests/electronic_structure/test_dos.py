import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import CompleteDos, Dos, Orbital, Spin


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
