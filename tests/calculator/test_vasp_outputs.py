"""Tests for VASP output file parsing.

Test data copied from thirds/pymatgen-core/test-files/io/vasp/outputs/.
Uses matsimpy constructs. May import pymatgen as optional reference oracle.
"""

import json
import os
from types import SimpleNamespace

import pytest
import numpy as np

from monty.json import MontyDecoder

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "vasp")


def test_chgcar_native_arithmetic_and_serialization():
    from matsimpy.calculator.vasp.outputs import Chgcar
    from matsimpy.core import Crystal, Lattice

    chgcar = Chgcar(Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2)), {"total": np.ones((2, 2, 2))})
    doubled = chgcar + chgcar
    assert type(doubled) is Chgcar
    np.testing.assert_array_equal(doubled.data["total"], 2)
    decoded = MontyDecoder().process_decoded(doubled.as_dict())
    assert type(decoded) is Chgcar
    np.testing.assert_array_equal(decoded.data["total"], 2)

    cached = Chgcar(
        chgcar.structure,
        {"total": np.ones((2, 2, 2))},
        distance_matrix=np.full((1, 2, 2, 2), 99.0),
    )
    assert cached.get_integrated_diff(0, 1.0)[-1, 1] == 0
    restored = MontyDecoder().process_decoded(json.loads(json.dumps(cached.as_dict())))
    assert type(restored) is Chgcar
    assert restored.get_integrated_diff(0, 1.0)[-1, 1] == 0


@pytest.mark.parametrize("volumetric_cls_name", ["Chgcar", "Locpot", "Elfcar"])
def test_scalar_volumetric_native_write_and_read(tmp_path, volumetric_cls_name):
    from matsimpy.calculator.vasp import outputs
    from matsimpy.core import Crystal, Lattice

    volumetric_cls = getattr(outputs, volumetric_cls_name)
    structure = Crystal(["Si"], [[0.125, 0.25, 0.375]], Lattice.cubic(2))
    total = np.arange(8, dtype=float).reshape(2, 2, 2)
    path = tmp_path / volumetric_cls_name.upper()

    volumetric_cls(structure, {"total": total}).write_file(path)
    restored = volumetric_cls.from_file(path)

    np.testing.assert_allclose(restored.structure.frac_positions, structure.frac_positions)
    np.testing.assert_allclose(restored.data["total"], total)


def test_noncollinear_chgcar_native_write_and_read(tmp_path):
    from matsimpy.calculator.vasp.outputs import Chgcar
    from matsimpy.core import Crystal, Lattice

    structure = Crystal(["Fe"], [[0.125, 0.25, 0.375]], Lattice.cubic(2))
    total = np.arange(8, dtype=float).reshape(2, 2, 2)
    components = {
        "diff_x": np.full((2, 2, 2), 1.0),
        "diff_y": np.full((2, 2, 2), 2.0),
        "diff_z": np.full((2, 2, 2), 3.0),
    }
    path = tmp_path / "CHGCAR"

    Chgcar(structure, {"total": total, **components}).write_file(path)
    restored = Chgcar.from_file(path)

    assert path.read_text().count("   2   2   2\n") == 4
    np.testing.assert_allclose(restored.data["total"], total)
    for key, values in components.items():
        np.testing.assert_allclose(restored.data[key], values)


def test_noncollinear_chgcar_rejects_partial_components(tmp_path):
    from matsimpy.calculator.vasp.outputs import Chgcar
    from matsimpy.core import Crystal, Lattice

    structure = Crystal(["Fe"], [[0, 0, 0]], Lattice.cubic(2))
    data = {"total": np.ones((1, 1, 1)), "diff_x": np.ones((1, 1, 1))}

    with pytest.raises(ValueError, match="missing diff_y, diff_z"):
        Chgcar(structure, data).write_file(tmp_path / "CHGCAR")


def test_xdatcar_native_get_str_write_and_roundtrip(tmp_path):
    from matsimpy.calculator.vasp.outputs import Xdatcar
    from matsimpy.core import Crystal, Lattice

    lattice = Lattice.cubic(3)
    frames = [
        Crystal(["Si", "O"], [[0.0, 0.0, 0.0], [0.25, 0.5, 0.75]], lattice),
        Crystal(["Si", "O"], [[0.1, 0.2, 0.3], [0.35, 0.6, 0.85]], lattice),
    ]
    xdatcar = Xdatcar.__new__(Xdatcar)
    xdatcar.structures = frames
    xdatcar.comment = "native trajectory"
    path = tmp_path / "XDATCAR"

    text = xdatcar.get_str(significant_figures=6)
    xdatcar.write_file(path, significant_figures=6)
    restored = Xdatcar(path)

    assert path.read_text() == text
    assert "Si O\n1 1\n" in text
    assert len(restored.structures) == len(frames)
    for actual, expected in zip(restored.structures, frames):
        assert list(actual.species) == list(expected.species)
        np.testing.assert_allclose(actual.frac_positions, expected.frac_positions)


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

    def test_run_type_detects_hse06_with_hfscreen_0207(self):
        """The fixture is an HSE06 run with HFSCREEN=0.207 (not exactly 0.2).

        An exact ``isclose(HFSCREEN, 0.2)`` check labelled it as
        "PBEO or other Hybrid Functional".
        """
        from matsimpy.calculator.vasp.outputs import Vasprun

        vr = Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        assert vr.parameters["HFSCREEN"] == pytest.approx(0.207)
        assert vr.run_type == "HSE06"

    @pytest.mark.parametrize(
        ("hfscreen", "expected"),
        [
            (0.2, "HSE06"),
            (0.207, "HSE06"),
            (0.21, "HSE06"),
            (0.3, "HSE03"),
            (0.25, "PBEO or other Hybrid Functional"),
        ],
    )
    def test_run_type_hfscreen_ranges(self, hfscreen, expected):
        import copy

        from matsimpy.calculator.vasp.outputs import Vasprun

        vr = copy.copy(Vasprun(os.path.join(FIXTURES_DIR, "vasprun.xml")))
        vr.parameters = {**vr.parameters, "HFSCREEN": hfscreen}
        assert vr.run_type == expected

    @pytest.mark.parametrize("parser_name", ["Vasprun", "BSVasprun"])
    def test_as_dict_uses_native_reciprocal_lattice(self, parser_name):
        """Both XML serializers must use MatSimPy's reciprocal-lattice API."""
        from matsimpy.calculator.vasp import outputs

        parser = getattr(outputs, parser_name)(os.path.join(FIXTURES_DIR, "vasprun.xml"))
        data = parser.as_dict()

        expected = parser.final_structure.lattice.get_reciprocal_lattice().matrix
        actual = np.asarray(data["input"]["lattice_rec"]["lattice_vectors"])
        np.testing.assert_allclose(actual, expected, atol=1e-8)

    def test_update_charge_from_potcar_uses_native_composition(self):
        """POTCAR charge updates must consume Composition.composition."""
        from matsimpy.calculator.vasp.inputs import Incar
        from matsimpy.calculator.vasp.outputs import Vasprun
        from matsimpy.core import Crystal, Lattice

        structure = Crystal(
            ["Si", "O"],
            [[0, 0, 0], [0.25, 0.25, 0.25]],
            Lattice.cubic(5.0),
        )
        vasprun = Vasprun.__new__(Vasprun)
        vasprun.initial_structure = structure
        vasprun.final_structure = structure.copy()
        vasprun.ionic_steps = [
            {"structure": structure},
            {"structure": vasprun.final_structure},
        ]
        vasprun.atomic_symbols = ["Si", "O"]
        vasprun.incar = Incar({})
        vasprun.parameters = {"NELECT": 9.0}
        potcar = [
            SimpleNamespace(element="Si", ZVAL=4.0),
            SimpleNamespace(element="O", ZVAL=6.0),
        ]
        vasprun.get_potcars = lambda _path: potcar

        vasprun.update_charge_from_potcar(False)

        assert vasprun.initial_structure._charge == pytest.approx(1.0)
        assert vasprun.final_structure._charge == pytest.approx(1.0)

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


class TestProcarProjectionOnElements:
    """Procar.get_projection_on_elements had no coverage and crashed with
    AttributeError: species are plain symbol strings, not Element objects."""

    @staticmethod
    def _procar(nions):
        from matsimpy.calculator.vasp.outputs import Procar
        from matsimpy.electronic_structure.core import Spin

        procar = Procar.__new__(Procar)
        procar.nkpoints, procar.nbands, procar.nions = 1, 2, nions
        # data[kpoint, band, ion, orbital]; ion i carries weight i + 1 per orbital
        data = np.zeros((1, 2, nions, 3))
        for ion in range(nions):
            data[:, :, ion, :] = ion + 1
        procar.data = {Spin.up: data}
        return procar, Spin

    def test_sums_projections_per_element_symbol(self):
        from matsimpy.core import Crystal, Lattice

        crystal = Crystal(
            ["Fe", "O", "Fe"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0]], Lattice.cubic(4)
        )
        procar, Spin = self._procar(3)
        proj = procar.get_projection_on_elements(crystal)

        for band in range(2):
            assert dict(proj[Spin.up][band][0]) == {"Fe": 3 * (1 + 3), "O": 3 * 2}

    def test_rejects_structure_with_wrong_atom_count(self):
        from matsimpy.core import Crystal, Lattice

        procar, _ = self._procar(3)
        with pytest.raises(ValueError, match="2 atoms but the PROCAR has 3 ions"):
            procar.get_projection_on_elements(
                Crystal(["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(4))
            )


class TestOutcarOnDemandReaders:
    """The read_* methods built on micro_pyawk all failed with "could not be parsed":
    micro_pyawk expected a {key: pattern} dict, its callers pass pymatgen records."""

    @pytest.fixture
    def outcar(self):
        from matsimpy.calculator.vasp.outputs import Outcar

        return Outcar(os.path.join(FIXTURES_DIR, "OUTCAR"))

    def test_read_pseudo_zval(self, outcar):
        outcar.read_pseudo_zval()
        assert outcar.zval_dict == {"Li": 1.0, "Ni": 10.0, "O": 6.0}

    @pytest.mark.parametrize(
        "method", ["read_igpar", "read_lepsilon", "read_lepsilon_ionic", "read_internal_strain_tensor"]
    )
    def test_reader_runs_on_a_real_outcar(self, outcar, method):
        getattr(outcar, method)()

    @pytest.mark.requires_pymatgen
    def test_lepsilon_matches_pymatgen(self, outcar):
        pytest.importorskip("pymatgen")
        from pymatgen.io.vasp.outputs import Outcar as PymatgenOutcar

        reference = PymatgenOutcar(os.path.join(FIXTURES_DIR, "OUTCAR"))
        outcar.read_lepsilon()
        reference.read_lepsilon()
        np.testing.assert_allclose(
            np.asarray(outcar.dielectric_tensor, float), np.asarray(reference.dielectric_tensor, float)
        )
