"""Core skill — Crystal, Molecule, Structure domain operations. Always loaded."""

from matsimpy.core import Crystal, Molecule, Lattice, Composition, Element
from matsimpy.ai.skill import FunctionDef
import numpy as np

SKILL_NAME = "core"
SKILL_DESCRIPTION = "Core crystal and molecular structure creation and editing"


def _create_crystal(species, positions, a=5.0, lattice_type="cubic"):
    """Create a periodic crystal structure."""
    lat = getattr(Lattice, lattice_type, Lattice.cubic)(a)
    return Crystal(species, positions, lat)


def _create_molecule(species, positions):
    """Create a non-periodic molecular structure."""
    return Molecule(species, positions)


def _add_atom(structure, species, position):
    """Add an atom to a structure. Returns a new structure."""
    if isinstance(structure, dict) and "formula" in structure:
        # Reconstruct from serialized form — caller should pass fresh objects
        raise ValueError("Structure must be a live object, not a serialized dict")
    return structure.add_atom(species, position)


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="create_crystal",
            description="Create a periodic crystal structure with a lattice",
            parameters={
                "type": "object",
                "properties": {
                    "species": {"type": "array", "items": {"type": "string"},
                                "description": "Element symbols e.g. ['Na','Cl']"},
                    "positions": {"type": "array", "items": {"type": "array",
                                "items": {"type": "number"}},
                                "description": "Fractional coordinates"},
                    "a": {"type": "number", "description": "Lattice constant in Angstrom", "default": 5.0},
                    "lattice_type": {"type": "string",
                                     "enum": ["cubic", "tetragonal", "orthorhombic", "hexagonal"],
                                     "default": "cubic"},
                },
                "required": ["species", "positions"],
            },
            callable=_create_crystal,
            skill=SKILL_NAME,
            help_text="Create a Crystal with given species, fractional positions, and lattice.\n"
                      "Example: create_crystal(['Na','Cl'], [[0,0,0],[0.5,0.5,0.5]], a=5.64)",
        ),
        FunctionDef(
            name="create_molecule",
            description="Create a non-periodic molecular structure",
            parameters={
                "type": "object",
                "properties": {
                    "species": {"type": "array", "items": {"type": "string"},
                                "description": "Element symbols"},
                    "positions": {"type": "array", "items": {"type": "array",
                                "items": {"type": "number"}},
                                "description": "Cartesian coordinates in Angstrom"},
                },
                "required": ["species", "positions"],
            },
            callable=_create_molecule,
            skill=SKILL_NAME,
            help_text="Create a Molecule with given species and Cartesian positions.\n"
                      "Example: create_molecule(['O','H','H'], [[0,0,0],[0.96,0,0],[-0.24,0.93,0]])",
        ),
        FunctionDef(
            name="get_formula",
            description="Get the chemical formula of a structure",
            parameters={
                "type": "object",
                "properties": {},
            },
            callable=lambda: "Use structure.formula attribute directly",
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="get_composition",
            description="Get the elemental composition with counts",
            parameters={
                "type": "object",
                "properties": {},
            },
            callable=lambda: "Use structure.composition attribute",
            skill=SKILL_NAME,
        ),
    ]
