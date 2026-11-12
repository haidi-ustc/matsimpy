"""Tests for VaspCalculator driver."""

import pytest
from matsimpy.core import Crystal, Lattice


class TestVaspCalculator:
    def test_write_input_writes_input_only(self, tmp_path):
        from matsimpy.calculator.vasp import VaspCalculator
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = VaspCalculator(
            directory=str(tmp_path / "unused"),
            incar={"ENCUT": 400},
            kpoints=[1, 1, 1],
            copy_potcar=False,
        )
        assert calc.write_input(crystal, tmp_path) == tmp_path
        incar_path = tmp_path / "INCAR"
        poscar_path = tmp_path / "POSCAR"
        kpoints_path = tmp_path / "KPOINTS"
        assert incar_path.exists()
        assert poscar_path.exists()
        assert kpoints_path.exists()
        assert not (tmp_path / "POTCAR").exists()
        assert not (tmp_path / "unused").exists()  # explicit directory wins

    def test_compute_runs_the_executable(self, tmp_path):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator(directory=tmp_path, vasp_cmd="nonexistent_vasp", copy_potcar=False)
        with pytest.raises((FileNotFoundError, RuntimeError)):
            calc.compute(Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43)))

    def test_read_results_with_real_vasprun(self):
        """read_results should parse an existing vasprun.xml (uses real fixture)."""
        import os
        from matsimpy.calculator.vasp import VaspCalculator

        fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")
        if not os.path.isfile(os.path.join(fixtures, "vasprun.xml")):
            pytest.skip("repository asset not available: tests/calculator/fixtures/vasp")
        import numpy as np
        from matsimpy.calculator.vasp.outputs import Vasprun

        calc = VaspCalculator(directory=fixtures)
        r = calc.read_results()
        last = Vasprun(os.path.join(fixtures, "vasprun.xml")).ionic_steps[-1]

        assert r.energy == pytest.approx(-269.38319884, abs=1e-7)
        # forces: final ionic step, as written (eV/A); 0.8.x returned None here
        assert r.forces.shape == (25, 3)
        np.testing.assert_array_equal(r.forces, np.asarray(last["forces"]))
        # stress: kBar (pressure positive) -> eV/A^3 (tension positive)
        kbar_to_ev_per_a3 = 0.1 / 160.21766208
        assert r.stress.shape == (3, 3)
        np.testing.assert_allclose(
            r.stress, -np.asarray(last["stress"]) * kbar_to_ev_per_a3, rtol=1e-6
        )
        assert r.stress[2, 2] > 0  # raw zz = -1.159 kBar (tensile) -> positive

    def test_init_with_defaults(self):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator()
        assert calc.parameters["incar"]["ENCUT"] == 400
        assert calc.parameters["kpoints"] == [1, 1, 1]
        assert calc.parameters["vasp_cmd"] == "vasp"
        assert VaspCalculator.from_dict(calc.as_dict()).parameters == calc.parameters

    def test_init_with_custom_params(self):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator(
            directory="/tmp/custom",
            incar={"ENCUT": 500, "EDIFF": 1e-6},
            kpoints=[2, 2, 2],
            vasp_cmd="/usr/local/bin/vasp_std",
        )
        assert calc.parameters["incar"]["EDIFF"] == 1e-6
        assert calc.parameters["kpoints"] == [2, 2, 2]

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

        poscar = type("DummyPoscar", (), {"site_symbols": ["Na", "Cl", "O"]})()

        VaspCalculator._write_potcar(poscar, tmp_path)

        assert captured["symbols"] == ["Na", "Cl", "O"]
        assert captured["functional"] == "PBE"
