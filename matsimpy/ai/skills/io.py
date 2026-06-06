"""IO skill — file reading, writing, format conversion."""

from matsimpy.io import read, write
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "io"
SKILL_DESCRIPTION = "File I/O: read and write structures in various formats"


def _read_structure(path, format=None):
    s = read(path, format=format) if format else read(path)
    return {
        "formula": s.formula,
        "num_atoms": len(s),
        "type": type(s).__name__,
    }


def _save_structure(path, format=None):
    """Save the last created/modified structure to a file."""
    from matsimpy.ai.executor import get_last_structure
    structure = get_last_structure()

    if structure is None:
        return {"error": "No structure to save. Create or modify a structure first (e.g., from_prototype, create_vacancy, make_supercell)."}

    write(structure, path, format=format)
    return {
        "saved_to": path,
        "formula": structure.formula,
        "num_atoms": len(structure),
        "format": format or "auto-detected",
    }


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="read_structure",
            description="Read a crystal or molecule structure from a file. Auto-detects format.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to structure file (.vasp, .cif, .xyz, .json, etc.)"},
                    "format": {"type": "string", "description": "Format override (vasp, cif, xyz, json, etc.)"},
                },
                "required": ["path"],
            },
            callable=_read_structure,
            skill=SKILL_NAME,
            help_text="Read a structure file. Format auto-detected from extension.\n"
                      "Supported: VASP, CIF, XYZ, PDB, XSF, MOL, JSON, ASE.",
        ),
        FunctionDef(
            name="save_structure",
            description="Save the last created/modified structure to a file. Use after creating or modifying a structure with builders or transformations.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Output file path (.vasp, .cif, .xyz, etc.)"},
                    "format": {"type": "string", "description": "Output format (vasp, cif, xyz, json, etc.). Auto-detected from extension if omitted."},
                },
                "required": ["path"],
            },
            callable=_save_structure,
            skill=SKILL_NAME,
            help_text="Save the last structure to a file. Creates/overwrites the file.\n"
                      "Format is auto-detected from extension (e.g., .vasp → VASP, .cif → CIF).\n"
                      "Works with the most recently created or modified structure.",
        ),
        FunctionDef(
            name="list_formats",
            description="List all supported file formats for reading and writing",
            parameters={"type": "object", "properties": {}},
            callable=lambda: {
                "readers": ["vasp", "cif", "xyz", "pdb", "xsf", "mol", "json", "ase"],
                "writers": ["vasp", "cif", "xyz", "pdb", "xsf", "mol", "json", "ase"],
            },
            skill=SKILL_NAME,
        ),
    ]
