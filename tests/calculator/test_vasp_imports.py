"""Tests for VASP calculator — imports and basic functionality."""

import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice


class TestVaspImports:
    def test_import_incar(self):
        from matsimpy.calculator.vasp.inputs import Incar
        incar = Incar({"ENCUT": 400, "ISMEAR": 0})
        assert incar["ENCUT"] == 400

    def test_import_poscar(self):
        from matsimpy.calculator.vasp.inputs import Poscar
        # POSCAR from string works without requiring pymatgen Structure
        poscar = Poscar.from_str(
            "Si test\n1.0\n5.43 0 0\n0 5.43 0\n0 0 5.43\nSi\n1\nDirect\n0 0 0"
        )
        assert poscar is not None
        assert "Si" in str(poscar)

    def test_import_kpoints(self):
        from matsimpy.calculator.vasp.inputs import Kpoints
        kpt = Kpoints.automatic([2, 2, 2])
        assert kpt.style.value == 0  # Automatic enum

    def test_import_outcar(self):
        from matsimpy.calculator.vasp.outputs import Outcar
        assert Outcar is not None

    def test_import_vasprun(self):
        from matsimpy.calculator.vasp.outputs import Vasprun
        assert Vasprun is not None

    def test_vasp_calculator_init(self):
        from matsimpy.calculator.vasp.calculator import VaspCalculator
        calc = VaspCalculator(
            directory="/tmp/vasp_test",
            incar={"ENCUT": 300, "ISMEAR": -5},
            kpoints=[1, 1, 1],
        )
        assert calc.incar_params["ENCUT"] == 300
        assert calc.kpoints_grid == [1, 1, 1]


class TestGaussianImports:
    def test_import_gaussian_input(self):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput
        assert GaussianInput is not None

    def test_gaussian_calculator_init(self):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator
        calc = GaussianCalculator(
            directory="/tmp/g09_test",
            route="# B3LYP/6-31G(d)",
        )
        assert "B3LYP" in calc.route


class TestLammpsImports:
    def test_import_lammps_data(self):
        from matsimpy.calculator.lammps.data import LammpsData
        assert LammpsData is not None

    def test_import_lammps_input(self):
        from matsimpy.calculator.lammps.inputs import LammpsInputFile
        assert LammpsInputFile is not None

    def test_lammps_calculator_init(self):
        from matsimpy.calculator.lammps.calculator import LammpsCalculator
        calc = LammpsCalculator(
            directory="/tmp/lammps_test",
            pair_style="lj/cut 10.0",
        )
        assert "lj/cut" in calc.pair_style
