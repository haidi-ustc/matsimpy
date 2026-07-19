"""Focused parity checks against the optional pinned pymatgen oracle."""

from pathlib import Path

import numpy as np
import pytest

from matsimpy.calculator.vasp.outputs import Vasprun
from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import BandStructure, BandStructureSymmLine, Spin
from matsimpy.io.volumetric import VolumetricData
from matsimpy.io.wannier import Unk


FIXTURE = Path(__file__).parent / "fixtures" / "vasp" / "vasprun.xml"


@pytest.mark.requires_pymatgen
def test_volumetric_parity():
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PymatgenLattice
    from pymatgen.core import Structure as PymatgenStructure
    from pymatgen.electronic_structure.core import Spin as PymatgenSpin
    from pymatgen.io.common import VolumetricData as PymatgenVolumetricData

    grid = np.arange(8.0).reshape(2, 2, 2)
    diff = np.ones_like(grid)
    native_structure = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))
    oracle_structure = PymatgenStructure(PymatgenLattice.cubic(2), ["Si"], [[0, 0, 0]])
    native = VolumetricData(native_structure, {"total": grid, "diff": diff})
    oracle = PymatgenVolumetricData(oracle_structure, {"total": grid, "diff": diff})

    assert native.dim == oracle.dim
    assert native.ngridpts == oracle.ngridpts
    for axis in range(3):
        np.testing.assert_allclose(native.get_average_along_axis(axis), oracle.get_average_along_axis(axis))
    native_integral = native.get_integrated_diff(0, 1, nbins=5)
    oracle_integral = oracle.get_integrated_diff(0, 1, nbins=5)
    np.testing.assert_allclose(native_integral[:-1], oracle_integral[:-1])
    # At the cell-boundary radius pymatgen counts multiple periodic images of
    # the same samples.  The native contract instead assigns one minimum-image
    # distance to each of the eight samples: origin plus three face points gives
    # 4 / 8, with no duplicate boundary images.
    assert native_integral[-1, 1] == pytest.approx(0.5)
    assert oracle_integral[-1, 1] == pytest.approx(0.875)
    np.testing.assert_allclose((native + native).data["total"], (oracle + oracle).data["total"])
    for spin, values in native.spin_data.items():
        np.testing.assert_allclose(values, oracle.spin_data[PymatgenSpin(int(spin))])


@pytest.mark.requires_pymatgen
def test_unk_byte_parity(tmp_path):
    pytest.importorskip("pymatgen")
    from pymatgen.io.wannier90 import Unk as PymatgenUnk

    for name, data in (
        ("collinear", np.arange(16).reshape(2, 2, 2, 2) * (1 + 2j)),
        ("noncollinear", np.arange(16).reshape(1, 2, 2, 2, 2) * (1 - 1j)),
    ):
        native_path = tmp_path / f"native-{name}"
        oracle_path = tmp_path / f"oracle-{name}"
        Unk(2, data).write_file(native_path)
        PymatgenUnk(2, data).write_file(oracle_path)
        assert native_path.read_bytes() == oracle_path.read_bytes()


@pytest.mark.requires_pymatgen
def test_vasprun_dos_parity():
    pytest.importorskip("pymatgen")
    from pymatgen.io.vasp.outputs import Vasprun as PymatgenVasprun

    native = Vasprun(FIXTURE)
    oracle = PymatgenVasprun(FIXTURE, parse_potcar_file=False)

    assert native.tdos.efermi == oracle.tdos.efermi
    np.testing.assert_allclose(native.tdos.energies, oracle.tdos.energies, rtol=1e-10, atol=1e-10)
    for spin, density in oracle.tdos.densities.items():
        np.testing.assert_allclose(native.tdos.densities[int(spin)], density, rtol=1e-10, atol=1e-10)

    native_complete = native.complete_dos
    oracle_complete = oracle.complete_dos
    for index, oracle_site in enumerate(oracle.final_structure):
        native_site = native.final_structure[index]
        for orbital, densities in oracle_complete.pdos[oracle_site].items():
            for spin, density in densities.items():
                np.testing.assert_allclose(
                    native_complete.pdos[native_site][int(orbital)][int(spin)],
                    density,
                    rtol=1e-10,
                    atol=1e-10,
                )


@pytest.mark.requires_pymatgen
def test_band_structure_parity():
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PymatgenLattice
    from pymatgen.electronic_structure.bandstructure import BandStructureSymmLine as PymatgenBandStructure
    from pymatgen.electronic_structure.core import Spin as PymatgenSpin

    coords = [[0, 0, 0], [.25, 0, 0], [.5, 0, 0], [.5, 0, 0], [.5, .25, 0], [.5, .5, 0]]
    bands = [[-1, -.8, -.5, -.5, -.6, -.7], [1.2, 1.1, 1, 1, 1.3, 1.5]]
    labels = {"G": coords[0], "X": coords[2], "M": coords[-1]}
    native = BandStructureSymmLine(coords, {Spin.up: bands}, Lattice.cubic(1), 0, labels)
    oracle = PymatgenBandStructure(coords, {PymatgenSpin.up: bands}, PymatgenLattice.cubic(1), 0, labels)

    assert native.efermi == oracle.efermi
    np.testing.assert_allclose(native.lattice_rec.matrix, oracle.lattice_rec.matrix, atol=1e-8)
    np.testing.assert_allclose([k.frac_coords for k in native.kpoints], [k.frac_coords for k in oracle.kpoints], atol=1e-8)
    assert [k.label for k in native.kpoints] == [k.label for k in oracle.kpoints]
    assert [(b["start_index"], b["end_index"]) for b in native.branches] == [(b["start_index"], b["end_index"]) for b in oracle.branches]
    np.testing.assert_allclose(native.bands[Spin.up], oracle.bands[PymatgenSpin.up], atol=1e-8)
    assert native.get_vbm()["energy"] == pytest.approx(oracle.get_vbm()["energy"])
    assert native.get_cbm()["energy"] == pytest.approx(oracle.get_cbm()["energy"])
    assert native.get_band_gap()["energy"] == pytest.approx(oracle.get_band_gap()["energy"])


@pytest.mark.requires_pymatgen
def test_vasprun_get_band_structure_parity():
    pytest.importorskip("pymatgen")
    from pymatgen.electronic_structure.core import Spin as PymatgenSpin
    from pymatgen.io.vasp.outputs import Vasprun as PymatgenVasprun

    native = Vasprun(FIXTURE).get_band_structure()
    oracle = PymatgenVasprun(FIXTURE, parse_potcar_file=False).get_band_structure()

    assert isinstance(native, BandStructureSymmLine) == hasattr(oracle, "branches")
    assert type(native) is BandStructure
    assert native.efermi == pytest.approx(oracle.efermi)
    np.testing.assert_allclose(native.lattice_rec.matrix, oracle.lattice_rec.matrix, atol=1e-8)
    np.testing.assert_allclose(
        [point.frac_coords for point in native.kpoints],
        [point.frac_coords for point in oracle.kpoints],
        atol=1e-8,
    )
    assert [point.label for point in native.kpoints] == [point.label for point in oracle.kpoints]
    assert set(map(int, native.bands)) == set(map(int, oracle.bands))
    for spin, bands in native.bands.items():
        np.testing.assert_allclose(bands, oracle.bands[PymatgenSpin(int(spin))], atol=1e-8)
    assert set(map(int, native.projections)) == set(map(int, oracle.projections))
    for spin, projections in native.projections.items():
        np.testing.assert_allclose(projections, oracle.projections[PymatgenSpin(int(spin))], atol=1e-8)
    native_branches = getattr(native, "branches", [])
    oracle_branches = getattr(oracle, "branches", [])
    assert native_branches == oracle_branches
    native_gap = native.get_band_gap()
    oracle_gap = oracle.get_band_gap()
    assert native_gap["energy"] == pytest.approx(oracle_gap["energy"])
    assert native_gap["direct"] == oracle_gap["direct"]
    assert native_gap["transition"] == oracle_gap["transition"]


@pytest.mark.requires_pymatgen
def test_vasprun_entry_parity():
    pytest.importorskip("pymatgen")
    from pymatgen.io.vasp.outputs import Vasprun as PymatgenVasprun

    native_run = Vasprun(FIXTURE)
    oracle_run = PymatgenVasprun(FIXTURE, parse_potcar_file=False)
    native = native_run.get_computed_entry(entry_id="fixture")
    oracle = oracle_run.get_computed_entry(entry_id="fixture")

    assert dict(native.composition.composition) == oracle.composition.as_dict()
    assert native.uncorrected_energy == pytest.approx(oracle.uncorrected_energy)
    assert native.correction == pytest.approx(oracle.correction)
    assert native.parameters == oracle.parameters
    assert native.data == oracle.data
    assert native.entry_id == oracle.entry_id


@pytest.mark.requires_pymatgen
def test_vasprun_trajectory_parity():
    pytest.importorskip("pymatgen")
    from pymatgen.io.vasp.outputs import Vasprun as PymatgenVasprun

    native = Vasprun(FIXTURE).get_trajectory()
    oracle = PymatgenVasprun(FIXTURE, parse_potcar_file=False).get_trajectory()

    assert len(native) == len(oracle)
    for native_frame, oracle_frame in zip(native, oracle):
        np.testing.assert_allclose(native_frame.lattice.matrix, oracle_frame.lattice.matrix)
        assert list(native_frame.species) == [str(specie) for specie in oracle_frame.species]
        coordinate_delta = native_frame.frac_positions - oracle_frame.frac_coords
        np.testing.assert_allclose(coordinate_delta - np.round(coordinate_delta), 0, atol=1e-8)
