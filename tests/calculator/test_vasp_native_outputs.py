"""Native result contracts for VASP output parsing."""

from __future__ import annotations

import ast
from pathlib import Path

from matsimpy.calculator.vasp import outputs
import pytest

from matsimpy.calculator.vasp.outputs import Vasprun, get_adjusted_fermi_level
from matsimpy.core import Crystal, Lattice
from matsimpy.core.entries import ComputedStructureEntry
from matsimpy.core.trajectory import Trajectory
from matsimpy.electronic_structure import (
    BandStructure,
    BandStructureSymmLine,
    CompleteDos,
    Spin,
)


VASP_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vasp"


def test_vasprun_advanced_results_are_native():
    run = Vasprun(VASP_FIXTURES / "vasprun.xml")

    assert isinstance(run.get_computed_entry(), ComputedStructureEntry)
    assert isinstance(run.get_trajectory(), Trajectory)
    assert isinstance(run.complete_dos, CompleteDos)


def test_vasprun_get_band_structure_returns_native_model():
    run = Vasprun(VASP_FIXTURES / "vasprun.xml")

    band_structure = run.get_band_structure()

    assert isinstance(band_structure, BandStructure)


def test_adjusted_fermi_level_returns_in_gap_candidate():
    structure = Crystal(["Si"], [[0.0, 0.0, 0.0]], Lattice.cubic(4.0))
    band_structure = BandStructureSymmLine(
        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
        {Spin.up: [[-0.1, 0.04], [0.25, 0.3]]},
        structure.lattice.get_reciprocal_lattice(),
        0.0,
        labels_dict={"G": [0.0, 0.0, 0.0]},
        structure=structure,
    )

    adjusted = get_adjusted_fermi_level(
        efermi=0.0,
        cbm=0.2,
        band_structure=band_structure,
        energy_step=0.05,
    )

    assert adjusted == pytest.approx(0.05)


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
