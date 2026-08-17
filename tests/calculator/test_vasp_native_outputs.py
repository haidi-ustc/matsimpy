"""Native result contracts for VASP output parsing."""

from __future__ import annotations

import ast
from pathlib import Path

from matsimpy.calculator.vasp import outputs
from matsimpy.calculator.vasp.outputs import Vasprun
from matsimpy.core.entries import ComputedStructureEntry
from matsimpy.core.trajectory import Trajectory
from matsimpy.electronic_structure import CompleteDos


VASP_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vasp"


def test_vasprun_advanced_results_are_native():
    run = Vasprun(VASP_FIXTURES / "vasprun.xml")

    assert isinstance(run.get_computed_entry(), ComputedStructureEntry)
    assert isinstance(run.get_trajectory(), Trajectory)
    assert isinstance(run.complete_dos, CompleteDos)


def test_outputs_source_has_no_pymatgen_imports():
    tree = ast.parse(Path(outputs.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert not any(
        name == "pymatgen" or name.startswith("pymatgen.") for name in imported
    )
