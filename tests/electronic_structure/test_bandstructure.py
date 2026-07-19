import numpy as np
import pytest
from monty.json import MontyDecoder
from pathlib import Path

from matsimpy.core import Lattice
from matsimpy.electronic_structure import (
    BandStructure,
    BandStructureSymmLine,
    Kpoint,
    Spin,
    get_reconstructed_band_structure,
)
from matsimpy.calculator.vasp.outputs import Vasprun


def test_band_structure_edges_and_gap():
    reciprocal = Lattice.cubic(1.0)
    bands = {Spin.up: np.array([[-1.0, -0.5], [1.0, 1.5]])}
    bs = BandStructure([[0, 0, 0], [0.5, 0, 0]], bands, reciprocal, 0.0)
    assert bs.nb_bands == 2
    assert bs.is_metal() is False
    assert bs.get_band_gap()["energy"] == pytest.approx(1.5)
    assert bs.get_vbm()["energy"] == pytest.approx(-0.5)
    assert bs.get_cbm()["energy"] == pytest.approx(1.0)


def test_metal_detection_requires_values_on_both_sides_of_fermi():
    lattice = Lattice.cubic(1)
    touching = BandStructure([[0, 0, 0], [.5, 0, 0]], {Spin.up: [[-1, 0], [1, 2]]}, lattice, 0)
    crossing = BandStructure([[0, 0, 0], [.5, 0, 0]], {Spin.up: [[-1, 1], [2, 3]]}, lattice, 0)
    assert not touching.is_metal()
    assert crossing.is_metal()
    assert crossing.get_band_gap() == {"energy": 0.0, "direct": False, "transition": None}


def test_spin_channels_and_shapes_are_validated():
    lattice = Lattice.cubic(1)
    kpoints = [[0, 0, 0], [.5, 0, 0]]
    bs = BandStructure(kpoints, {1: [[-2, -1], [2, 3]], -1: [[-1, -.5], [1, 2]]}, lattice, 0)
    assert set(bs.bands) == {Spin.up, Spin.down}
    assert bs.is_spin_polarized
    with pytest.raises(ValueError, match="shape"):
        BandStructure(kpoints, {Spin.up: [[1, 2, 3]]}, lattice, 0)
    with pytest.raises(ValueError, match="projection"):
        BandStructure(kpoints, {Spin.up: [[-1, -1], [1, 1]]}, lattice, 0,
                      projections={Spin.up: np.zeros((2, 1, 3, 1))})


def test_kpoint_and_symmetry_line_labels_branches_and_round_trip():
    lattice = Lattice.cubic(2)
    kp = Kpoint([1, 0, 0], lattice, coords_are_cartesian=True, label="X")
    np.testing.assert_allclose(kp.frac_coords, [.5, 0, 0])
    restored_kp = Kpoint.from_dict(kp.as_dict())
    assert restored_kp == kp

    coords = [[0, 0, 0], [.25, 0, 0], [.5, 0, 0], [.5, 0, 0], [.5, .25, 0]]
    bs = BandStructureSymmLine(coords, {Spin.up: [[-1] * 5, [1] * 5]}, lattice, 0,
                               {"G": coords[0], "X": coords[2], "M": coords[-1]})
    assert [k.label for k in bs.kpoints] == ["G", None, "X", "X", "M"]
    assert bs.branches == [
        {"start_index": 0, "end_index": 2, "name": "G-X"},
        {"start_index": 3, "end_index": 4, "name": "X-M"},
    ]
    data = bs.as_dict()
    assert set(data["bands"]) == {"1"}
    restored = MontyDecoder().process_decoded(data)
    assert isinstance(restored, BandStructureSymmLine)
    assert restored.branches == bs.branches


def test_reconstruction_preserves_labels_spins_and_projections():
    lattice = Lattice.cubic(1)
    first = BandStructureSymmLine([[0, 0, 0], [.5, 0, 0]],
        {Spin.up: [[-1, -2]], Spin.down: [[-3, -4]]}, lattice, 0,
        {"G": [0, 0, 0], "X": [.5, 0, 0]}, projections={Spin.up: np.ones((1, 2, 1, 1)), Spin.down: np.ones((1, 2, 1, 1))})
    second = BandStructureSymmLine([[.5, 0, 0], [.5, .5, 0]],
        {Spin.up: [[-5, -6]], Spin.down: [[-7, -8]]}, lattice, 0,
        {"X": [.5, 0, 0], "M": [.5, .5, 0]}, projections={Spin.up: np.full((1, 2, 1, 1), 2), Spin.down: np.full((1, 2, 1, 1), 2)})
    merged = get_reconstructed_band_structure([first, second], efermi=.2)
    assert merged.efermi == .2
    assert [k.label for k in merged.kpoints] == ["G", "X", "X", "M"]
    assert merged.branches[1]["name"] == "X-M"
    assert merged.bands[Spin.up].shape == (1, 4)
    assert merged.projections[Spin.down].shape == (1, 4, 1, 1)
    with pytest.raises(ValueError, match="at least one"):
        get_reconstructed_band_structure([])


def test_vasprun_returns_native_band_structure():
    fixture = Path(__file__).parents[1] / "calculator" / "fixtures" / "vasp" / "vasprun.xml"
    result = Vasprun(fixture).get_band_structure()
    assert type(result) is BandStructure
    assert result.bands[Spin.up].shape == (result.nb_bands, len(result.kpoints))
