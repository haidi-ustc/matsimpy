"""Regression tests for 0.8.2: ported-code API drift in the VASP/LAMMPS layers."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, SymmOp
from matsimpy.transformation import make_supercell


def _si():
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.43))


def _triclinic_nacl():
    lat = Lattice.from_parameters(4.1, 4.6, 5.3, 81.0, 97.0, 104.0)
    return Crystal(["Na", "Cl", "Na"], [[0.0, 0.0, 0.0], [0.5, 0.4, 0.6], [0.95, 0.1, 0.3]], lat)


# --------------------------------------------------------------------------
# SymmOp additions used by ported code
# --------------------------------------------------------------------------

def test_symmop_operate_multi_matches_operate():
    op = SymmOp.from_rotation_and_translation(
        SymmOp.from_origin_axis_angle([0, 0, 0], [1, 1, 0], 37.0).rotation_matrix, [0.1, -0.2, 0.3]
    )
    pts = np.random.default_rng(1).random((5, 3))
    expected = np.array([op.operate(p) for p in pts])
    assert np.allclose(op.operate_multi(pts), expected, atol=1e-14, rtol=0)
    assert np.array_equal(SymmOp.from_rotation_and_translation(np.eye(3)).translation_vector, np.zeros(3))


# --------------------------------------------------------------------------
# VASP
# --------------------------------------------------------------------------

def test_recommended_lreal_uses_len():
    from matsimpy.calculator.vasp.sets import _get_recommended_lreal

    assert _get_recommended_lreal(_si()) is False
    big = make_supercell(_si(), [3, 3, 3])
    assert _get_recommended_lreal(big) == "Auto"


@pytest.mark.parametrize("as_array", [False, True])
def test_poscar_selective_dynamics_and_velocities_are_written(as_array):
    from matsimpy.calculator.vasp.inputs import Poscar

    sd = [[True, False, True], [True, True, True]]
    vel = [[0.1, 0.0, 0.0], [0.0, 0.1, 0.0]]
    if as_array:
        sd, vel = np.array(sd), np.array(vel)
    text = Poscar(_si(), selective_dynamics=sd, velocities=vel).get_str()
    assert "Selective dynamics" in text
    assert " T F T " in text
    back = Poscar.from_str(text)
    assert np.array_equal(np.asarray(back.selective_dynamics), np.asarray(sd))
    assert np.allclose(np.asarray(back.velocities, dtype=float), np.asarray(vel, dtype=float))


def test_poscar_reads_per_site_data_from_structure_and_keeps_other_props():
    from matsimpy.calculator.vasp.inputs import Poscar

    slab = _si().with_site_properties(
        [
            {"selective_dynamics": [False, False, False], "magmom": 0.5},
            {"selective_dynamics": [True, True, True], "magmom": -0.5},
        ]
    )
    p = Poscar(slab)
    assert "Selective dynamics" in p.get_str()  # 0.8.1 silently dropped it
    p2 = Poscar(slab, velocities=[[0.1, 0, 0], [0, 0.1, 0]])
    assert [d["magmom"] for d in p2.structure.site_properties] == [0.5, -0.5]


def test_poscar_backing_arrays_follow_sorted_structure():
    from matsimpy.calculator.vasp.inputs import Poscar

    c = Crystal(["O", "Si"], [[0.5, 0.5, 0.5], [0, 0, 0]], Lattice.cubic(4.0))
    p = Poscar(c, selective_dynamics=[[False, False, False], [True, True, True]], sort_structure=True)
    assert p.structure.species == ("O", "Si")  # O (Z=8) before Si (Z=14)
    by_species = dict(zip(p.structure.species, np.asarray(p.selective_dynamics).tolist()))
    assert by_species == {"O": [False, False, False], "Si": [True, True, True]}


def test_poscar_set_temperature():
    from matsimpy.calculator.vasp.inputs import Poscar

    p = Poscar(_si(), selective_dynamics=[[True, False, True], [True, True, True]])
    original = p.structure
    p.set_temperature(300)
    text = p.get_str()
    assert "Selective dynamics" not in text
    assert np.asarray(p.velocities).shape == (2, 3)
    assert all("velocities" in d for d in p.structure.site_properties)
    assert original.site_properties[0].get("velocities") is None  # immutable input untouched


# --------------------------------------------------------------------------
# LAMMPS
# --------------------------------------------------------------------------

def _read_data_file(path):
    lines = path.read_text().splitlines()
    n_types = int(next(l for l in lines if l.endswith("atom types")).split()[0])
    i = lines.index("Masses") + 2
    masses = [float(l.split()[1]) for l in lines[i:i + n_types]]
    j = next(k for k, l in enumerate(lines) if l.startswith("Atoms")) + 2
    atoms = [l.split() for l in lines[j:] if l.strip()]
    bounds = [float(next(l for l in lines if l.endswith(f"{a}lo {a}hi")).split()[1]) for a in "xyz"]
    tilt_line = next((l for l in lines if l.endswith("xy xz yz")), None)
    tilt = [float(x) for x in tilt_line.split()[:3]] if tilt_line else [0.0, 0.0, 0.0]
    return n_types, masses, atoms, bounds, tilt


def test_lammps_calculator_writes_types_masses_and_triclinic_cell(tmp_path):
    from matsimpy.calculator.lammps import LammpsCalculator
    from matsimpy.core import Element

    c = _triclinic_nacl()
    LammpsCalculator(directory=tmp_path).write_input(c)
    n_types, masses, atoms, (lx, ly, lz), (xy, xz, yz) = _read_data_file(tmp_path / "data.lammps")
    assert n_types == 2
    assert masses == pytest.approx([Element("Na").atomic_mass, Element("Cl").atomic_mass])
    assert [int(a[1]) for a in atoms] == [1, 2, 1]
    # The LAMMPS cell is a rotation of the original: same metric tensor ...
    cell = np.array([[lx, 0, 0], [xy, ly, 0], [xz, yz, lz]])
    assert np.allclose(cell @ cell.T, c.lattice.matrix @ c.lattice.matrix.T, atol=1e-9)
    # ... and atoms sit at the same fractional coordinates (wrapped into the cell).
    pos = np.array([[float(x) for x in a[2:5]] for a in atoms])
    assert np.allclose(pos @ np.linalg.inv(cell), np.mod(c.frac_positions, 1.0), atol=1e-10)
    assert "boundary p p p" in (tmp_path / "in.lammps").read_text()


def test_lattice_2_lmpbox_keeps_tilt_for_triclinic_cells():
    pytest.importorskip("pandas")
    pytest.importorskip("ruamel.yaml")
    from matsimpy.calculator.lammps.data import lattice_2_lmpbox

    box, _ = lattice_2_lmpbox(_triclinic_nacl().lattice)
    assert box.tilt is not None  # 0.8.1: always None (bound method is truthy)
    box_cubic, _ = lattice_2_lmpbox(Lattice.cubic(4.0))
    assert box_cubic.tilt is None


def test_lammps_data_structure_roundtrip():
    pytest.importorskip("pandas")
    pytest.importorskip("ruamel.yaml")
    from matsimpy.calculator.lammps import LammpsData

    c = _triclinic_nacl()
    ld = LammpsData.from_structure(c, atom_style="atomic")
    back = ld.structure
    assert sorted(back.species) == sorted(c.species)
    assert np.allclose(back.lattice.matrix @ back.lattice.matrix.T,
                       c.lattice.matrix @ c.lattice.matrix.T, atol=1e-8)
    # same fractional coordinates, matched by species after LAMMPS' re-ordering
    got = sorted((s, tuple(np.round(np.mod(f, 1.0), 8))) for s, f in zip(back.species, back.frac_positions))
    exp = sorted((s, tuple(np.round(np.mod(f, 1.0), 8))) for s, f in zip(c.species, c.frac_positions))
    assert got == exp
    assert "atoms" in ld.get_str()


def test_topology_accepts_explicit_bonds():
    pytest.importorskip("pandas")
    pytest.importorskip("ruamel.yaml")
    from matsimpy.calculator.lammps.data import Topology
    from matsimpy.core import Molecule

    water = Molecule(["O", "H", "H"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
    topo = Topology(water, topologies={"Bonds": [[0, 1], [0, 2]]})
    assert topo.type_by_sites == ["O", "H", "H"]


def test_lammps_read_results_returns_potential_energy(tmp_path):
    """0.9.0: read_results(directory) -> Results; the ``pe`` column, not ``etotal``."""
    from matsimpy.calculator.lammps.calculator import LammpsCalculator

    (tmp_path / "log.lammps").write_text(
        "Step PotEng KinEng TotEng Temp Press\n"
        "       0   -1.25    0.5   -0.75    0    12.0\n"
        "Loop time of 1e-06 on 1 procs\n"
    )
    r = LammpsCalculator(directory=tmp_path / "other").read_results(tmp_path)
    assert r.energy == -1.25 and r.forces is None
    with pytest.raises(FileNotFoundError):
        LammpsCalculator(directory=tmp_path / "missing").read_results()
