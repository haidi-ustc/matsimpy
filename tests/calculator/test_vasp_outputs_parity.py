"""Focused parity checks against the optional pinned pymatgen oracle."""

from pathlib import Path

import numpy as np
import pytest

from matsimpy.calculator.vasp.outputs import Vasprun


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
