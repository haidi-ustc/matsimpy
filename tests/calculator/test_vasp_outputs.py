"""Tests for VASP output file parsing.

Test data copied from thirds/pymatgen-core/test-files/io/vasp/outputs/.
Uses matsimpy constructs. May import pymatgen as optional reference oracle.
"""

import os
import pytest
import numpy as np

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")


def test_projected_magnetisation_migration_wrappers_are_absent():
    from matsimpy.calculator.vasp.outputs import KpointOptProps, Vasprun

    assert not hasattr(KpointOptProps, "projected_magnetisation")
    assert not hasattr(Vasprun, "projected_magnetisation")


def test_multiple_branch_band_structure_requires_branch_directories(tmp_path):
    from matsimpy.calculator.vasp.outputs import get_band_structure_from_vasp_multiple_branches

    (tmp_path / "vasprun.xml").write_text("<modeling></modeling>", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="branch_0"):
        get_band_structure_from_vasp_multiple_branches(tmp_path)


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


class TestProcar:
    def test_get_projection_on_elements_accepts_native_crystal_species(self):
        from matsimpy.calculator.vasp.outputs import Procar
        from matsimpy.core import Crystal, Lattice
        from matsimpy.electronic_structure import Spin

        procar = Procar.__new__(Procar)
        procar.data = {
            Spin.up: np.array(
                [
                    [
                        [
                            [1.0, 2.0],
                            [3.0, 4.0],
                        ]
                    ]
                ]
            )
        }
        procar.nkpoints = 1
        procar.nbands = 1
        procar.nions = 2
        crystal = Crystal(
            ["Si", "O"],
            [[0, 0, 0], [0.25, 0.25, 0.25]],
            Lattice.cubic(4.0),
        )

        projection = procar.get_projection_on_elements(crystal)

        assert projection[Spin.up][0][0]["Si"] == pytest.approx(3.0)
        assert projection[Spin.up][0][0]["O"] == pytest.approx(7.0)
