"""Tests for VASP input sets.

Uses matsimpy structures and imports.
"""

import ast
from pathlib import Path

import pytest

from matsimpy.calculator.vasp import sets
from matsimpy.calculator.vasp.inputs import Kpoints
from matsimpy.core import Crystal, Lattice


def test_sets_source_has_no_pymatgen_imports():
    tree = ast.parse(Path(sets.__file__).read_text(encoding="utf-8"))
    modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name == "pymatgen" or name.startswith("pymatgen.") for name in modules)


def test_element_reads_existing_quadrupole_data():
    from matsimpy.core import Element

    assert Element("Al").get_nmr_quadrupole_moment("Al-27") == 146.6


def test_automatic_ir_mesh_uses_native_symmetry():
    from matsimpy.calculator.vasp.sets import DictSet

    si_crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    vset = DictSet(
        si_crystal,
        config_dict={
            "INCAR": {"ENCUT": 400},
            "KPOINTS": {"reciprocal_density": 100, "force_gamma": True, "explicit": True},
            "POTCAR": {"Si": "Si"},
        },
    )

    assert isinstance(vset.kpoints, Kpoints)


def test_dictset_rejects_non_native_structure():
    from matsimpy.calculator.vasp.sets import DictSet

    try:
        DictSet("not a structure", config_dict={"INCAR": {"ENCUT": 400}})
    except TypeError as exc:
        assert "VASP input sets require a matsimpy Crystal" in str(exc)
    else:
        raise AssertionError("DictSet should reject non-native structures")


def test_dictset_fails_clearly_when_reduce_structure_requested():
    from matsimpy.calculator.vasp.sets import DictSet

    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))

    try:
        DictSet(
            crystal,
            config_dict={"INCAR": {"ENCUT": 400}},
            reduce_structure="niggli",
        )
    except NotImplementedError as exc:
        assert "Native VASP input sets do not yet support reduce_structure" in str(exc)
    else:
        raise AssertionError("DictSet should fail clearly for reduce_structure")


def test_standardize_structure_rejects_curtarolo_monoclinic_setting():
    from matsimpy.calculator.vasp.sets import standardize_structure

    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))

    try:
        standardize_structure(crystal, international_monoclinic=False)
    except NotImplementedError as exc:
        assert "only supports the international setting" in str(exc)
    else:
        raise AssertionError("standardize_structure should reject unsupported monoclinic setting")


def test_write_input_reraises_vasp_psp_dir_error(tmp_path, monkeypatch):
    from matsimpy.calculator.vasp.inputs import VaspPspDirError
    from matsimpy.calculator.vasp.sets import DictSet

    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    vset = DictSet(crystal, config_dict={"INCAR": {"ENCUT": 400}})

    def fail_without_psp_dir(*, potcar_spec=False):
        raise VaspPspDirError("missing POTCAR root")

    monkeypatch.setattr(vset, "get_input_set", fail_without_psp_dir)

    with pytest.raises(VaspPspDirError, match="PMG_VASP_PSP_DIR is not set"):
        vset.write_input(tmp_path, potcar_spec=False)


class TestDictSet:
    def test_dictset_import(self):
        from matsimpy.calculator.vasp.sets import DictSet
        assert DictSet is not None

    def test_dictset_instantiate(self):
        """DictSet should instantiate with a crystal and config."""
        from matsimpy.calculator.vasp.sets import DictSet
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        vset = DictSet(crystal, config_dict={"INCAR": {"ENCUT": 400, "ISMEAR": 0}})

        assert vset.incar["ENCUT"] == 400
        assert isinstance(vset.poscar.structure, Crystal)
