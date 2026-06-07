"""Adapter skill — convert between MatSimPy and optional external structure objects."""

from __future__ import annotations

from matsimpy.ai.executor import get_last_structure
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import sig_to_schema

SKILL_NAME = "adapters"
SKILL_DESCRIPTION = "External adapters: ASE and pymatgen conversion helpers"
SKILL_KEYWORDS: list[str] = [
    "adapter",
    "adapters",
    "convert",
    "conversion",
    "ase",
    "atoms",
    "pymatgen",
]


def _require_structure(structure):
    if structure is not None:
        return structure
    structure = get_last_structure()
    if structure is None:
        raise ValueError("No structure available. Create or read a structure first.")
    return structure


def _summarize_external_object(obj):
    return {
        "type": type(obj).__name__,
        "module": type(obj).__module__,
        "repr": repr(obj)[:500],
    }


def _to_ase(structure=None):
    from matsimpy.adapters.ase import to_ase as to_ase_api

    structure = _require_structure(structure)
    return _summarize_external_object(to_ase_api(structure))


def _from_ase(ase_atoms):
    from matsimpy.adapters.ase import from_ase as from_ase_api

    return from_ase_api(ase_atoms)


def _to_pymatgen(structure=None):
    from matsimpy.adapters.pymatgen import to_pymatgen as to_pymatgen_api

    structure = _require_structure(structure)
    return _summarize_external_object(to_pymatgen_api(structure))


def _from_pymatgen(pymatgen_obj):
    from matsimpy.adapters.pymatgen import from_pymatgen as from_pymatgen_api

    return from_pymatgen_api(pymatgen_obj)


def get_functions() -> list[FunctionDef]:
    return [
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
    ]
