"""Tests for VASP input sets.

Uses matsimpy structures and imports.
"""

import ast
from pathlib import Path

from matsimpy.core import Crystal, Lattice
from matsimpy.calculator.vasp import sets
from matsimpy.calculator.vasp.inputs import Kpoints


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
