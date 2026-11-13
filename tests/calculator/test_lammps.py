"""Tests for the LAMMPS calculator and data files."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice


def _triclinic_nacl():
    lat = Lattice.from_parameters(4.1, 4.6, 5.3, 81.0, 97.0, 104.0)
    return Crystal(["Na", "Cl", "Na"], [[0.0, 0.0, 0.0], [0.5, 0.4, 0.6], [0.95, 0.1, 0.3]], lat)


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
    assert box.tilt is not None
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
    """read_results(directory) returns Results with the ``pe`` column, not ``etotal``."""
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


def test_lammps_data_header_accepts_trailing_comments(tmp_path):
    # pymatgen's test files contain no LAMMPS data file, so this small one is written here
    pytest.importorskip("pandas")
    from matsimpy.calculator.lammps.data import LammpsData

    path = tmp_path / "comments.data"
    path.write_text(
        "LAMMPS data file  # header\n\n"
        "2 atoms   # two Ar atoms\n1 atom types\n\n"
        "0.0 10.0 xlo xhi   # box x\n0.0 10.0 ylo yhi\n0.0 10.0 zlo zhi\n\n"
        "Masses\n\n1 39.948\n\n"
        "Atoms  # atomic\n\n1 1 0.0 0.0 0.0\n2 1 5.0 5.0 5.0\n"
    )
    data = LammpsData.from_file(str(path), atom_style="atomic")
    assert len(data.atoms) == 2
    assert data.box.bounds == [[0.0, 10.0]] * 3
