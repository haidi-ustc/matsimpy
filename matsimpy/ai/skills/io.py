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


def _write_structure(path, formula_hint=None):
    return {"error": "write requires a live structure object — use in combination with a builder"}


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
