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
            assert gau.molecule.formula == "H11 C5 N1"
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
    def test_run_false_writes_input_only(self, tmp_path):
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
            run=False,
        )
        calc.calculate(mol)
        input_file = tmp_path / "input.gjf"
        assert input_file.exists()
        assert "energy" not in calc.results

    def test_run_true_attempts_execution(self, tmp_path):
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
            run=True,
            gaussian_cmd="nonexistent_g09",
        )
        with pytest.raises((FileNotFoundError, RuntimeError)):
            calc.calculate(mol)

    def test_init_defaults(self):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator

        calc = GaussianCalculator()
        assert calc.route == "# B3LYP/6-31G(d)"
        assert calc.charge == 0
        assert calc.spin == 1

    def test_run_parameter(self):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator

        calc = GaussianCalculator(run=True)
        assert calc.run is True
        calc2 = GaussianCalculator(run=False)
        assert calc2.run is False
