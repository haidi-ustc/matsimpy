"""Tests for VASP calculator — imports and basic functionality."""

import os

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")


class TestVaspImports:
    def test_import_incar(self):
        from matsimpy.calculator.vasp.inputs import Incar
        incar = Incar.from_file(os.path.join(FIXTURES_DIR, "INCAR"))
        assert incar["ENCUT"] == 500

    def test_import_poscar(self):
        from matsimpy.calculator.vasp.inputs import Poscar
        # POSCAR from string works without requiring pymatgen Structure
        with open(os.path.join(FIXTURES_DIR, "POSCAR_C2")) as fh:
            poscar = Poscar.from_str(fh.read())
        assert poscar.site_symbols == ["C"]
        assert "C" in str(poscar)

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
        assert calc.parameters["incar"]["ENCUT"] == 300
        assert calc.parameters["kpoints"] == [1, 1, 1]


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
        assert "B3LYP" in calc.parameters["route"]


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
        assert "lj/cut" in calc.parameters["pair_style"]
