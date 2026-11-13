"""Tests for the pymatgen and ASE object converters."""

import os

import numpy as np
import pytest

from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Crystal, Molecule
from matsimpy.io import from_ase, from_pymatgen, read_POSCAR, to_ase, to_pymatgen

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")
STRUCTURES = [
    from_prototype("diamond", "Si", 5.43),
    Molecule(["C", "O", "O"], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]),
]


def _mno():
    return read_POSCAR(os.path.join(VASP_DIR, "POSCAR_MnO"))


# --------------------------------------------------------------------------
# pymatgen
# --------------------------------------------------------------------------


@pytest.mark.parametrize("structure", STRUCTURES, ids=["crystal", "molecule"])
def test_pymatgen_round_trip(structure):
    pmg = pytest.importorskip("pymatgen.core")
    converted = to_pymatgen(structure)
    assert isinstance(converted, pmg.Structure if isinstance(structure, Crystal) else pmg.Molecule)
    back = from_pymatgen(converted)
    assert type(back) is type(structure)
    assert back.species == structure.species
    np.testing.assert_allclose(back.positions, structure.positions, atol=1e-10)


def test_pymatgen_keeps_pbc_and_site_properties():
    pmg = pytest.importorskip("pymatgen.io.vasp")
    md = pmg.Poscar.from_file(os.path.join(VASP_DIR, "CONTCAR.MD")).structure
    assert "velocities" in from_pymatgen(md).site_properties[0]
    slab = _mno().set_pbc([True, True, False])
    assert to_pymatgen(slab).lattice.pbc == (True, True, False)
    assert from_pymatgen(to_pymatgen(slab)).pbc == (True, True, False)


def test_pymatgen_oxidation_states_become_a_site_property_and_back():
    pytest.importorskip("pymatgen")
    ps = to_pymatgen(_mno())
    ps.add_oxidation_state_by_element({"Mn": 2, "O": -2})
    back = from_pymatgen(ps)
    assert {p["oxidation_state"] for p in back.site_properties} == {2, -2}
    assert {str(sp) for sp in to_pymatgen(back).species} == {"Mn2+", "O2-"}


# --------------------------------------------------------------------------
# ASE
# --------------------------------------------------------------------------


@pytest.mark.parametrize("structure", STRUCTURES, ids=["crystal", "molecule"])
def test_ase_round_trip(structure):
    pytest.importorskip("ase")
    back = from_ase(to_ase(structure))
    assert type(back) is type(structure)
    assert back.species == structure.species
    np.testing.assert_allclose(back.positions, structure.positions, atol=1e-10)


def test_ase_keeps_magnetic_moments():
    pytest.importorskip("ase")
    c = _mno()
    c = c.with_site_property("magmom", [5.0 if s == "Mn" else 0.0 for s in c.species])
    magmoms = [p["magmom"] for p in c.site_properties]
    atoms = to_ase(c)
    np.testing.assert_allclose(atoms.get_initial_magnetic_moments(), magmoms)
    assert [p["magmom"] for p in from_ase(atoms).site_properties] == magmoms


# --------------------------------------------------------------------------
# Invalid input
# --------------------------------------------------------------------------


@pytest.mark.parametrize("convert", [to_pymatgen, to_ase])
def test_converters_reject_non_structures(convert):
    with pytest.raises(ValueError):
        convert("not a structure")


def test_from_ase_rejects_non_atoms():
    pytest.importorskip("ase")
    with pytest.raises(ValueError):
        from_ase("not an ASE Atoms object")
