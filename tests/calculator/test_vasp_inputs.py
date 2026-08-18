"""Tests for VASP input file classes.

Test data copied from thirds/pymatgen-core/test-files/io/vasp/.
Uses matsimpy Crystal/Lattice classes and matsimpy imports.
May import pymatgen only as an optional reference oracle.
"""

import os
import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice, Composition

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")


def test_vasp_inputs_use_canonical_magmom():
    from matsimpy.calculator.vasp import inputs
    from matsimpy.electronic_structure import Magmom

    assert inputs.Magmom is Magmom


def test_incar_formats_scalar_and_vector_magmoms_exactly():
    from matsimpy.calculator.vasp.inputs import Incar, Magmom

    scalar = Incar({"MAGMOM": [1.0, 1.0, -2.0]})
    assert scalar.get_str() == "MAGMOM = 2*1.0 1*-2.0\n"

    vector = Incar({"LSORBIT": True, "MAGMOM": [Magmom([1, 2, 3])]})
    assert "MAGMOM = 1.0 2.0 3.0\n" in vector.get_str()


def test_vasp_inputs_expose_potcar_specific_names_only():
    from matsimpy.calculator.vasp import inputs

    assert inputs.PotcarOrbital is not None
    assert inputs.PotcarOrbitalDescription is not None
    assert inputs.VaspPspDirError is not None
    assert not hasattr(inputs, "Orbital")
    assert not hasattr(inputs, "OrbitalDescription")
    assert not hasattr(inputs, "PmgVaspPspDirError")


class TestIncar:
    def test_from_file(self):
        """Parse INCAR from real VASP INCAR fixture."""
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar.from_file(os.path.join(FIXTURES_DIR, "INCAR"))
        assert incar["ALGO"] == "Damped"
        assert float(incar["EDIFF"]) == pytest.approx(1e-4)
        assert isinstance(incar["LORBIT"], int)

    def test_from_dict_and_get(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar({"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05})
        assert incar["ENCUT"] == 400
        assert incar["ISMEAR"] == 0

    def test_write_read_roundtrip(self, tmp_path):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar({"ENCUT": 400, "ISMEAR": 0})
        fpath = tmp_path / "INCAR"
        incar.write_file(fpath)
        text = fpath.read_text()
        assert "ENCUT" in text
        assert "400" in text

    def test_diff(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar1 = Incar({"ENCUT": 400, "ISMEAR": 0})
        incar2 = Incar({"ENCUT": 500, "ISMEAR": 0})
        diff = incar1.diff(incar2)
        # diff returns dict with 'Different' key for things that differ
        assert "Different" in diff
        assert "ENCUT" in diff["Different"]

    def test_get_str(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar({"ENCUT": 400, "ISMEAR": 0})
        s = incar.get_str()
        assert "ENCUT" in s
        assert "400" in s

    def test_key_case_insensitive(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar.from_str("ALGO = Fast\nENCUT = 480\nEDIFF = 1e-07\n")
        incar["encut"] = 490
        assert incar["ENCUT"] == 490
        assert incar.get("encut") == 490

    def test_check_params(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar({"ENCUT": 400, "LWAVE": False})
        incar.check_params()

    def test_incar_set_and_get(self):
        from matsimpy.calculator.vasp.inputs import Incar

        incar = Incar({})
        incar["ENCUT"] = 500
        assert incar["ENCUT"] == 500


class TestKpoints:
    def test_from_file(self):
        """Parse KPOINTS from real VASP KPOINTS fixture."""
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.from_file(os.path.join(FIXTURES_DIR, "KPOINTS"))
        assert kpt is not None
        assert kpt.kpts is not None

    def test_automatic(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.automatic([4, 4, 4])
        assert kpt.style.value == 0  # Automatic enum

    def test_gamma_automatic(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.gamma_automatic([2, 2, 2])
        assert kpt.style.value == 1  # Gamma enum

    def test_monkhorst_pack(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.monkhorst_automatic([6, 6, 6])
        assert kpt is not None

    def test_write_file(self, tmp_path):
        from matsimpy.calculator.vasp.inputs import Kpoints

        kpt = Kpoints.automatic([3, 3, 3])
        fpath = tmp_path / "KPOINTS"
        kpt.write_file(fpath)
        text = fpath.read_text()
        assert "3 3 3" in text or "Automatic" in text

    def test_automatic_density_tetragonal_even_mesh_uses_monkhorst_pack(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.tetragonal(3.0, 6.0))

        kpt = Kpoints.automatic_density(crystal, 41)

        assert kpt.kpts == [(4, 4, 2)]
        assert kpt.style == Kpoints.supported_modes.Monkhorst

    def test_automatic_density_by_lengths_tetragonal_even_mesh_uses_monkhorst_pack(self):
        from matsimpy.calculator.vasp.inputs import Kpoints

        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.tetragonal(3.0, 6.0))

        kpt = Kpoints.automatic_density_by_lengths(crystal, [10.0, 10.0, 10.0])

        assert kpt.kpts == [(4, 4, 2)]
        assert kpt.style == Kpoints.supported_modes.Monkhorst

    def test_automatic_density_propagates_symmetry_failures(self, monkeypatch):
        import matsimpy.calculator.vasp.inputs as inputs
        from matsimpy.calculator.vasp.inputs import Kpoints

        class FailingSymmetryAnalyzer:
            def __init__(self, *args, **kwargs):
                pass

            def analyze_crystal(self, structure):
                raise RuntimeError("native symmetry failure")

        monkeypatch.setattr(inputs, "SymmetryAnalyzer", FailingSymmetryAnalyzer)
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.tetragonal(3.0, 6.0))

        with pytest.raises(RuntimeError, match="native symmetry failure"):
            Kpoints.automatic_density(crystal, 41)


class TestPoscar:
    @pytest.fixture
    def si_crystal(self):
        return Crystal(
            ["Si", "Si"],
            [[0, 0, 0], [0.25, 0.25, 0.25]],
            Lattice.cubic(5.43),
        )

    def test_from_file(self):
        """Parse POSCAR from real VASP POSCAR fixture."""
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar.from_file(
            os.path.join(FIXTURES_DIR, "POSCAR"),
            check_for_potcar=False,
            read_velocities=False,
        )
        assert poscar is not None
        assert poscar.structure is not None
        # POSCAR fixture contains LiFePO4
        assert len(poscar.structure) > 0
        assert "Fe" in poscar.site_symbols or "Li" in poscar.site_symbols

    def test_from_str_basic(self):
        """Parse POSCAR from string (VASP 5 format)."""
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar_str = """Si test
1.0
5.43 0 0
0 5.43 0
0 0 5.43
Si
1
Direct
0 0 0
"""
        poscar = Poscar.from_str(poscar_str)
        assert poscar is not None
        assert "Si" in str(poscar)
        assert poscar.structure.formula == "Si"

    def test_from_str_vasp4_with_symbols(self):
        """VASP 4 type with symbols at the end."""
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar_str = """Test1
1.0
3.840198 0.000000 0.000000
1.920099 3.325710 0.000000
0.000000 -2.217138 3.135509
1 1
direct
0.000000 0.000000 0.000000 Si
0.750000 0.500000 0.750000 F
"""
        poscar = Poscar.from_str(poscar_str)
        assert poscar is not None
        # Verify the structure has both Si and F
        formula = poscar.structure.formula
        assert "Si" in formula
        assert "F" in formula

    def test_from_str_selective_dynamics(self):
        """POSCAR with selective dynamics."""
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar_str = """Test3
1.0
3.840198 0.000000 0.000000
1.920099 3.325710 0.000000
0.000000 -2.217138 3.135509
1 1
Selective dynamics
direct
0.000000 0.000000 0.000000 T T T Si
0.750000 0.500000 0.750000 F F F O
"""
        poscar = Poscar.from_str(poscar_str)
        selective_dynamics = [list(x) for x in poscar.selective_dynamics]
        assert selective_dynamics == [[True, True, True], [False, False, False]]

    def test_from_str_empty_raises(self):
        from matsimpy.calculator.vasp.inputs import Poscar

        with pytest.raises(ValueError, match="Empty POSCAR"):
            Poscar.from_str("")

    def test_site_symbols(self, si_crystal):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(si_crystal)
        assert "Si" in poscar.site_symbols

    def test_comment_default(self, si_crystal):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(si_crystal)
        assert poscar.comment == si_crystal.formula

    def test_comment_custom(self, si_crystal):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(si_crystal, comment="Custom POSCAR")
        assert poscar.comment == "Custom POSCAR"

    def test_write_file(self, si_crystal, tmp_path):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(si_crystal)
        fpath = tmp_path / "POSCAR"
        poscar.write_file(fpath)
        text = fpath.read_text()
        assert "Si" in text

    def test_get_str_format(self, si_crystal):
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar = Poscar(si_crystal)
        s = poscar.get_str()
        # Should contain comment line, scale, lattice, species, coords
        assert "Si" in s
        lines = s.split("\n")
        assert len(lines) > 5

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(FIXTURES_DIR, "POSCAR")),
        reason="Fixture not available",
    )
    def test_optional_pymatgen_reference(self):
        """Compare matsimpy Poscar parsing against pymatgen as reference oracle."""
        pytest.importorskip("pymatgen")
        from pymatgen.io.vasp.inputs import Poscar as PmgPoscar
        from matsimpy.calculator.vasp.inputs import Poscar

        poscar_path = os.path.join(FIXTURES_DIR, "POSCAR")
        pmg_poscar = PmgPoscar.from_file(poscar_path, check_for_potcar=False, read_velocities=False)
        ms_poscar = Poscar.from_file(poscar_path, check_for_potcar=False, read_velocities=False)

        # Compare site symbols
        assert ms_poscar.site_symbols == pmg_poscar.site_symbols
        # Compare natoms
        assert ms_poscar.natoms == pmg_poscar.natoms
