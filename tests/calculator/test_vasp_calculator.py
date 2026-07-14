"""Tests for VaspCalculator driver."""

import pytest
from matsimpy.core import Crystal, Lattice


class TestVaspCalculator:
    def test_run_false_writes_input_only(self, tmp_path):
        from matsimpy.calculator.vasp import VaspCalculator
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = VaspCalculator(
            directory=str(tmp_path),
            incar={"ENCUT": 400},
            kpoints=[1, 1, 1],
            run=False,
        )
        calc.calculate(crystal)
        incar_path = tmp_path / "INCAR"
        poscar_path = tmp_path / "POSCAR"
        kpoints_path = tmp_path / "KPOINTS"
        assert incar_path.exists()
        assert poscar_path.exists()
        assert kpoints_path.exists()
        # No energy since we didn't run
        assert "energy" not in calc.results

    def test_run_default_is_true(self):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator()
        assert calc.run is True

    def test_read_results_with_real_vasprun(self):
        """read_results should parse an existing vasprun.xml (uses real fixture)."""
        import os
        from matsimpy.calculator.vasp import VaspCalculator

        fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")
        calc = VaspCalculator(directory=fixtures)
        calc.read_results()
        assert calc.results.get("energy") is not None
        assert calc.results["forces"].shape == (25, 3)
        assert calc.results["stress"].shape == (3, 3)

    def test_init_with_defaults(self):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator()
        assert calc.incar_params["ENCUT"] == 400
        assert calc.kpoints_grid == [1, 1, 1]
        assert calc.vasp_cmd == "vasp"

    def test_init_with_custom_params(self):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator(
            directory="/tmp/custom",
            incar={"ENCUT": 500, "EDIFF": 1e-6},
            kpoints=[2, 2, 2],
            vasp_cmd="/usr/local/bin/vasp_std",
        )
        assert calc.incar_params["EDIFF"] == 1e-6
        assert calc.kpoints_grid == [2, 2, 2]

    def test_potcar_symbols_preserve_poscar_order(self, tmp_path, monkeypatch):
        from matsimpy.calculator.vasp import VaspCalculator
        import matsimpy.calculator.vasp.inputs as inputs

        captured = {}

        class DummyPotcar:
            def __init__(self, symbols, functional=None):
                captured["symbols"] = list(symbols)
                captured["functional"] = functional

            def write_file(self, filename):
                captured["filename"] = filename

        monkeypatch.setenv("VASP_PP_PATH", str(tmp_path / "potcars"))
        monkeypatch.setattr(inputs, "Potcar", DummyPotcar)

        calc = VaspCalculator(directory=str(tmp_path), run=True)
        poscar = type("DummyPoscar", (), {"site_symbols": ["Na", "Cl", "O"]})()

        calc._write_potcar(poscar)

        assert captured["symbols"] == ["Na", "Cl", "O"]
        assert captured["functional"] == "PBE"
