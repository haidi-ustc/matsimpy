"""Tests for VASP output file parsing.

Test data copied from thirds/pymatgen-core/test-files/io/vasp/outputs/.
Uses matsimpy constructs. May import pymatgen as optional reference oracle.
"""

import os
import pytest
import numpy as np

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")


class TestOutcar:
    def test_from_file(self):
        """Parse OUTCAR from real VASP fixture."""
        from matsimpy.calculator.vasp.outputs import Outcar

        outcar = Outcar(os.path.join(FIXTURES_DIR, "OUTCAR"))
        assert outcar is not None
        assert outcar.final_energy == pytest.approx(-34.007267)

    def test_import(self):
        from matsimpy.calculator.vasp.outputs import Outcar
        assert Outcar is not None


class TestOszicar:
    def test_from_file(self):
        """Parse OSZICAR from real VASP fixture."""
        from matsimpy.calculator.vasp.outputs import Oszicar

        oszicar = Oszicar(os.path.join(FIXTURES_DIR, "OSZICAR"))
        assert len(oszicar.ionic_steps) >= 1
        # Last step should have energy keys
        last_step = oszicar.ionic_steps[-1]
        assert "E0" in last_step or "F" in last_step

    def test_import(self):
        from matsimpy.calculator.vasp.outputs import Oszicar
        assert Oszicar is not None


class TestVasprun:
    def test_from_file_basic(self):
        """Parse vasprun.xml from real VASP fixture with basic assertions."""
        from matsimpy.calculator.vasp.outputs import Vasprun

        vr = Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        assert vr is not None
        assert vr.final_energy == pytest.approx(-269.38319884, abs=1e-7)
        assert len(vr.ionic_steps) == 29

    def test_has_incar_and_kpoints(self):
        """Vasprun should parse INCAR and KPOINTS from vasprun.xml."""
        from matsimpy.calculator.vasp.outputs import Vasprun
        from matsimpy.calculator.vasp.inputs import Incar, Kpoints

        vr = Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        assert isinstance(vr.incar, Incar)
        assert isinstance(vr.kpoints, Kpoints)

    def test_structure_parsing(self):
        """Vasprun should parse initial and final structures."""
        from matsimpy.calculator.vasp.outputs import Vasprun

        vr = Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        assert vr.initial_structure is not None
        assert vr.final_structure is not None
        assert len(vr.initial_structure) > 0
        assert len(vr.final_structure) > 0

    def test_ionic_steps_have_structure(self):
        """Each ionic step should have a structure."""
        from matsimpy.calculator.vasp.outputs import Vasprun

        vr = Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        for step in vr.ionic_steps:
            assert "structure" in step

    def test_import(self):
        from matsimpy.calculator.vasp.outputs import Vasprun
        assert Vasprun is not None

    def test_parameters(self):
        """Vasprun should parse calculation parameters."""
        from matsimpy.calculator.vasp.outputs import Vasprun

        vr = Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        # parameters may be Incar (dict-like) or plain dict
        assert vr.parameters is not None
        assert vr.parameters["NELM"] == 60

    @pytest.mark.requires_pymatgen
    def test_optional_pymatgen_reference(self):
        """Compare matsimpy Vasprun parsing against pymatgen as reference oracle."""
        pytest.importorskip("pymatgen")
        from pymatgen.io.vasp.outputs import Vasprun as PmgVasprun
        from matsimpy.calculator.vasp.outputs import Vasprun

        fixture = os.path.join(FIXTURES_DIR, "vasprun.xml")
        pmg_vr = PmgVasprun(fixture, parse_potcar_file=False)
        ms_vr = Vasprun(fixture)

        # Compare energies
        assert ms_vr.final_energy == pytest.approx(pmg_vr.final_energy, abs=1e-5)
        # Compare number of ionic steps
        assert len(ms_vr.ionic_steps) == len(pmg_vr.ionic_steps)
