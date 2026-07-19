"""Focused parity checks against the optional pinned pymatgen oracle."""

from pathlib import Path

import numpy as np
import pytest

from matsimpy.calculator.vasp.outputs import Vasprun
from matsimpy.core import Lattice
from matsimpy.electronic_structure import BandStructureSymmLine, Spin


FIXTURE = Path(__file__).parent / "fixtures" / "vasp" / "vasprun.xml"


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
