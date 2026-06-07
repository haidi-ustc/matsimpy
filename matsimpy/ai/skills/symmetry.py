"""Symmetry skill — structure-reference wrappers around symmetry analysis."""

from __future__ import annotations

from matsimpy.ai.executor import get_last_structure
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import sig_to_schema
from matsimpy.symmetry import analyze_symmetry as _analyze_symmetry_api
from matsimpy.symmetry import get_conventional_cell as _get_conventional_cell_api

SKILL_NAME = "symmetry"
SKILL_DESCRIPTION = "Symmetry analysis: space groups, point groups, operations, and conventional cells"
SKILL_KEYWORDS: list[str] = [
    "symmetry",
    "space group",
    "spacegroup",
    "point group",
    "conventional",
    "wyckoff",
    "spglib",
]


def _require_structure(structure):
    if structure is not None:
        return structure
    structure = get_last_structure()
    if structure is None:
        raise ValueError("No structure available. Create or read a structure first.")
    return structure


def _analyze_symmetry(structure=None, symprec: float = 1e-5, angle_tolerance: float = -1.0):
    structure = _require_structure(structure)
    return _analyze_symmetry_api(
        structure,
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    )


def _get_conventional_cell(structure=None, symprec: float = 1e-5):
    structure = _require_structure(structure)
    return _get_conventional_cell_api(structure, symprec=symprec)


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="analyze_symmetry",
            description="Analyze space group, point group, Wyckoff positions, and symmetry operations",
            parameters=sig_to_schema(_analyze_symmetry),
            callable=_analyze_symmetry,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="get_conventional_cell",
            description="Return the conventional cell for a crystal structure reference",
            parameters=sig_to_schema(_get_conventional_cell),
            callable=_get_conventional_cell,
            skill=SKILL_NAME,
        ),
    ]
