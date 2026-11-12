"""Tests for Gaussian input/output and calculator.

Test data copied from thirds/pymatgen-core/test-files/io/gaussian/.
Rewritten to matsimpy style using matsimpy Molecule class and matsimpy imports.
May import pymatgen as optional reference oracle.
"""

import os
import pytest
import numpy as np
from matsimpy.core import Molecule

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "gaussian")


class TestGaussianInput:
    @pytest.fixture
    def ch4_mol(self):
        coords = [
            [0, 0, 0],
            [0, 0, 1.089],
            [1.026719, 0, -0.363],
            [-0.513360, -0.889165, -0.363],
            [-0.513360, 0.889165, -0.363],
        ]
        return Molecule(["C", "H", "H", "H", "H"], coords)

    def test_init(self, ch4_mol):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput

        gau = GaussianInput(
            ch4_mol,
            route_parameters={"SP": "", "SCF": "Tight"},
            input_parameters={"EPS": 12},
        )
        assert gau.functional == "HF"
        assert gau.basis_set == "6-31G(d)"
        assert gau.charge == 0
        assert gau.spin_multiplicity == 1

    def test_init_with_charge(self, ch4_mol):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput

        # Molecule with charge -1
        mol = Molecule(
            ["C", "H", "H", "H", "H"],
            ch4_mol.positions,
        )
        gau = GaussianInput(mol, charge=1, route_parameters={"SP": ""})
        assert gau.spin_multiplicity == 2

    def test_to_str(self, ch4_mol):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput

        gau = GaussianInput(
            ch4_mol,
            route_parameters={"SP": "", "SCF": "Tight"},
            input_parameters={"EPS": 12},
        )
        output = str(gau)
        assert "HF/6-31G(d)" in output
        assert "SCF=Tight" in output
        assert "SP" in output

    def test_to_str_cart_coords(self, ch4_mol):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput

        gau = GaussianInput(
            ch4_mol,
            route_parameters={"SP": "", "SCF": "Tight"},
            input_parameters={"EPS": 12},
        )
        output = gau.to_str(cart_coords=True)
        assert "0.000000 0.000000 0.000000" in output
        assert "EPS=12" in output

    def test_from_str(self, ch4_mol):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput

        gau = GaussianInput(
            ch4_mol,
            route_parameters={"SP": "", "SCF": "Tight"},
            input_parameters={"EPS": 12},
        )
        s = str(gau)
        gau2 = GaussianInput.from_str(s)
        assert gau2.functional == "HF"
        assert gau2.charge == 0

    def test_from_file(self):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput

        filepath = os.path.join(FIXTURES_DIR, "MethylPyrrolidine_drawn.gjf")
        # SymmOp is not supported in matsimpy — this fixture needs it for Z-matrix parsing
        try:
            gau = GaussianInput.from_file(filepath)
            assert "H" in gau.molecule.formula and "C" in gau.molecule.formula and "N" in gau.molecule.formula
            assert "opt" in gau.route_parameters
        except NotImplementedError:
            pytest.skip("SymmOp not available in matsimpy — Z-matrix parsing unsupported")

    def test_import(self):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput
        assert GaussianInput is not None


class TestGaussianOutput:
    def test_from_file(self):
        from matsimpy.calculator.gaussian.gaussian import GaussianOutput

        filepath = os.path.join(FIXTURES_DIR, "methane.log")
        gout = GaussianOutput(filepath)
        assert gout.final_energy is not None

    def test_import(self):
        from matsimpy.calculator.gaussian.gaussian import GaussianOutput
        assert GaussianOutput is not None

    @pytest.mark.requires_pymatgen
    def test_optional_pymatgen_reference(self):
        """Compare matsimpy GaussianOutput against pymatgen as reference oracle."""
        pytest.importorskip("pymatgen")
        from pymatgen.io.gaussian import GaussianOutput as PmgGaussianOutput
        from matsimpy.calculator.gaussian.gaussian import GaussianOutput

        filepath = os.path.join(FIXTURES_DIR, "methane.log")
        pmg_out = PmgGaussianOutput(filepath)
        ms_out = GaussianOutput(filepath)
        assert ms_out.final_energy == pytest.approx(pmg_out.final_energy)


class TestGaussianCalculator:
    def test_write_input_then_read_results(self, tmp_path):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator

        mol = Molecule(
            ["O", "H", "H"],
            [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]],
        )
        calc = GaussianCalculator(
            directory=str(tmp_path),
            route="# B3LYP/6-31G(d)",
            charge=0,
            spin=1,
        )
        calc.write_input(mol)
        input_file = tmp_path / "input.gjf"
        assert input_file.exists()
        assert not (tmp_path / "output.log").exists()
        (tmp_path / "output.log").write_text(" SCF Done:  E(RB3LYP) =  -76.4089   A.U. after 9 cycles\n")
        r = calc.read_results()
        assert r.energy == pytest.approx(-76.4089 * 27.211386245988)  # eV (0.8.x returned Hartree)
        assert r.extra["energy_hartree"] == -76.4089

    def test_read_results_from_real_log_is_last_scf_energy_in_ev(self, tmp_path):
        """A real multi-step log: the calculator reports the final SCF energy in eV,
        consistent with the native GaussianOutput parser (which reports Hartree)."""
        import shutil

        from matsimpy.calculator.gaussian.calculator import GaussianCalculator
        from matsimpy.calculator.gaussian.gaussian import GaussianOutput

        source = os.path.join(FIXTURES_DIR, "methane.log")
        shutil.copy(source, tmp_path / "output.log")
        r = GaussianCalculator(directory=str(tmp_path)).read_results()

        hartree = GaussianOutput(source).final_energy
        assert hartree == pytest.approx(-39.9768775602)
        assert r.extra["energy_hartree"] == pytest.approx(hartree)
        assert r.energy == pytest.approx(hartree * 27.211386245988)
        assert r.forces is None and r.stress is None

    def test_compute_attempts_execution(self, tmp_path):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator

        mol = Molecule(
            ["O", "H", "H"],
            [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]],
        )
        calc = GaussianCalculator(
            directory=str(tmp_path),
            route="# B3LYP/6-31G(d)",
            charge=0,
            spin=1,
            gaussian_cmd="nonexistent_g09",
        )
        with pytest.raises((FileNotFoundError, RuntimeError)):
            calc.compute(mol)

    def test_init_defaults(self):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator

        calc = GaussianCalculator()
        assert calc.parameters["route"] == "# B3LYP/6-31G(d)"
        assert calc.parameters["charge"] == 0
        assert calc.parameters["spin"] == 1

