"""IO skill - file IO, object conversion, and LaTeX export helpers."""

from __future__ import annotations

from matsimpy.ai.executor import get_last_structure
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import sig_to_schema

SKILL_NAME = "io"
SKILL_DESCRIPTION = "Unified IO: read/write structures, convert objects, and export LaTeX tables"
SKILL_KEYWORDS: list[str] = [
    "read",
    "write",
    "save",
    "load",
    "file",
    "format",
    "convert",
    "conversion",
    "io",
    "ase",
    "atoms",
    "pymatgen",
    "latex",
    "table",
    "report",
]


def _read_structure(path, format=None):
    from matsimpy import io

    structure = io.read(path, format=format) if format else io.read(path)
    return _summarize_structure(structure)


def _write_structure(path, structure=None, format=None):
    from matsimpy import io

    structure = _require_structure(structure)
    io.write(structure, path, format=format)
    return {
        "saved_to": path,
        "format": format or "auto-detected",
        **_summarize_structure(structure),
    }


def _to_ase(structure=None):
    from matsimpy import io

    structure = _require_structure(structure)
    return _summarize_external_object(io.to_ase(structure))


def _from_ase(ase_atoms):
    from matsimpy import io

    return io.from_ase(ase_atoms)


def _to_pymatgen(structure=None):
    from matsimpy import io

    structure = _require_structure(structure)
    return _summarize_external_object(io.to_pymatgen(structure))


def _from_pymatgen(pymatgen_obj):
    from matsimpy import io

    return io.from_pymatgen(pymatgen_obj)


def _structures_to_latex_table(
    structures=None,
    caption: str = "Structures",
    label: str = "tab:structures",
    separate_by_type: bool = True,
    use_mhchem: bool = False,
):
    from matsimpy import io

    return {
        "latex": io.structures_to_latex_table(
            _default_structures(structures),
            caption=caption,
            label=label,
            separate_by_type=separate_by_type,
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
    from matsimpy import io

    structures = _default_structures(structures)
    io.save_latex_table(
        structures,
        path,
        caption=caption,
        label=label,
        separate_by_type=separate_by_type,
        use_mhchem=use_mhchem,
    )
    return {
        "saved_to": path,
        "format": "latex",
        "num_structures": len(structures),
    }


def _require_structure(structure):
    if structure is not None:
        return structure
    structure = get_last_structure()
    if structure is None:
        raise ValueError("No structure available. Create or read a structure first.")
    return structure


def _default_structures(structures):
    if structures is not None:
        return structures
    return [_require_structure(None)]


def _summarize_structure(structure):
    return {
        "formula": structure.formula,
        "num_atoms": len(structure),
        "type": type(structure).__name__,
    }


def _summarize_external_object(obj):
    return {
        "type": type(obj).__name__,
        "module": type(obj).__module__,
        "repr": repr(obj)[:500],
    }


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="read_structure",
            description="Read a crystal or molecule structure from a file. Auto-detects format.",
            parameters=sig_to_schema(_read_structure),
            callable=_read_structure,
            skill=SKILL_NAME,
            help_text="Read a structure file. Format auto-detected from extension.\n"
                      "Supported: VASP, CIF, XYZ, PDB, XSF, MOL, JSON, ASE.",
        ),
        FunctionDef(
            name="write_structure",
            description="Write a MatSimPy structure reference to a file. Uses the last structure when none is provided.",
            parameters=sig_to_schema(_write_structure),
            callable=_write_structure,
            skill=SKILL_NAME,
            help_text="Save the last structure to a file. Creates/overwrites the file.\n"
                      "Format is auto-detected from extension (e.g., .vasp → VASP, .cif → CIF).\n"
                      "Works with the most recently created or modified structure.",
        ),
        FunctionDef(
            name="to_ase",
            description="Convert a MatSimPy structure reference to an ASE Atoms summary",
            parameters=sig_to_schema(_to_ase),
            callable=_to_ase,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="from_ase",
            description="Convert an ASE Atoms object to a MatSimPy structure",
            parameters=sig_to_schema(_from_ase),
            callable=_from_ase,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="to_pymatgen",
            description="Convert a MatSimPy structure reference to a pymatgen object summary",
            parameters=sig_to_schema(_to_pymatgen),
            callable=_to_pymatgen,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="from_pymatgen",
            description="Convert a pymatgen Structure or Molecule to a MatSimPy structure",
            parameters=sig_to_schema(_from_pymatgen),
            callable=_from_pymatgen,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="structures_to_latex_table",
            description="Create a LaTeX table for MatSimPy structure references",
            parameters=sig_to_schema(_structures_to_latex_table),
            callable=_structures_to_latex_table,
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
