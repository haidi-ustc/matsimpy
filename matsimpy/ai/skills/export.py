"""Export skill — presentation helpers for LaTeX output."""

from __future__ import annotations

from matsimpy.ai.executor import get_last_structure
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import sig_to_schema
from matsimpy.export import (
    crystals_to_latex_table as _crystals_to_latex_table_api,
    molecules_to_latex_table as _molecules_to_latex_table_api,
    save_latex_table as _save_latex_table_api,
    structures_to_latex_table as _structures_to_latex_table_api,
)

SKILL_NAME = "export"
SKILL_DESCRIPTION = "Export and presentation: LaTeX tables for structures"
SKILL_KEYWORDS: list[str] = [
    "export",
    "latex",
    "table",
    "presentation",
    "report",
]


def _default_structures(structures):
    if structures is not None:
        return structures
    structure = get_last_structure()
    if structure is None:
        raise ValueError("No structure available. Create or read a structure first.")
    return [structure]


def _structures_to_latex_table(
    structures=None,
    caption: str = "Structures",
    label: str = "tab:structures",
    separate_by_type: bool = True,
    use_mhchem: bool = False,
):
    return {
        "latex": _structures_to_latex_table_api(
            _default_structures(structures),
            caption=caption,
            label=label,
            separate_by_type=separate_by_type,
            use_mhchem=use_mhchem,
        )
    }


def _crystals_to_latex_table(
    structures=None,
    caption: str = "Crystal Structures",
    label: str = "tab:crystals",
    use_mhchem: bool = False,
):
    return {
        "latex": _crystals_to_latex_table_api(
            _default_structures(structures),
            caption=caption,
            label=label,
            use_mhchem=use_mhchem,
        )
    }


def _molecules_to_latex_table(
    structures=None,
    caption: str = "Molecular Structures",
    label: str = "tab:molecules",
    use_mhchem: bool = False,
):
    return {
        "latex": _molecules_to_latex_table_api(
            _default_structures(structures),
            caption=caption,
            label=label,
            use_mhchem=use_mhchem,
        )
    }


def _save_latex_table(
    path: str,
    structures=None,
    caption: str | None = None,
    label: str | None = None,
    separate_by_type: bool = True,
    use_mhchem: bool = False,
):
    structures = _default_structures(structures)
    _save_latex_table_api(
        structures,
        path,
        caption=caption,
        label=label,
        separate_by_type=separate_by_type,
        use_mhchem=use_mhchem,
    )
    return {"saved_to": path, "format": "latex", "num_structures": len(structures)}


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="structures_to_latex_table",
            description="Create a LaTeX table for MatSimPy structure references",
            parameters=sig_to_schema(_structures_to_latex_table),
            callable=_structures_to_latex_table,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="crystals_to_latex_table",
            description="Create a LaTeX table for crystal structure references",
            parameters=sig_to_schema(_crystals_to_latex_table),
            callable=_crystals_to_latex_table,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="molecules_to_latex_table",
            description="Create a LaTeX table for molecule structure references",
            parameters=sig_to_schema(_molecules_to_latex_table),
            callable=_molecules_to_latex_table,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="save_latex_table",
            description="Save a LaTeX table for structure references to a file",
            parameters=sig_to_schema(_save_latex_table),
            callable=_save_latex_table,
            skill=SKILL_NAME,
        ),
    ]
