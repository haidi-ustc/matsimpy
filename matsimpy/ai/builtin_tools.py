"""Tools that exist only for the agent.

Library functions are tools where they are defined (``@tool`` in
:mod:`matsimpy.builders`, :mod:`matsimpy.transformation`, ...).  This module
adds the few operations that have no single library function: building a
structure from explicit coordinates, summaries of analyses, a Lennard-Jones
calculation, VASP input files, and a per-session structure database.
"""

from __future__ import annotations

from typing import Any

from ..analysis.bonding import BondAnalyzer
from ..analysis.structure import StructureAnalyzer
from ..core import Crystal, Lattice, Molecule, Structure
from ..utils.tooling import tool
from .tools import ToolContext, ToolError

__all__ = [
    "analyze_bonds",
    "analyze_structure",
    "calculate_lennard_jones",
    "create_crystal",
    "create_molecule",
    "list_workspace_files",
    "query_structures",
    "retrieve_structure",
    "store_structure",
    "write_vasp_input",
]


@tool
def create_crystal(species: list[str], positions: list[list[float]], lattice: Lattice) -> Crystal:
    """Create a crystal from explicit species, fractional coordinates and lattice.

    Use this only when the user gives the coordinates.  It does not establish a
    named prototype: use ``from_prototype`` for fcc, rocksalt, perovskite, etc.

    Args:
        species: Element symbol of each site, e.g. ["Na", "Cl"].
        positions: Fractional coordinates of each site.
    """
    return Crystal(species, positions, lattice)


@tool
def create_molecule(species: list[str], positions: list[list[float]]) -> Molecule:
    """Create a molecule from species and Cartesian coordinates in Angstrom.

    Args:
        species: Element symbol of each atom, e.g. ["O", "H", "H"].
        positions: Cartesian coordinates of each atom in Angstrom.
    """
    return Molecule(species, positions)


@tool
def analyze_bonds(structure: Structure, cutoff: float = 2.0) -> dict[str, Any]:
    """Count bonds and bond angles and report coordination numbers.

    Args:
        structure: Structure to analyze.
        cutoff: Largest bond length in Angstrom.

    Returns:
        num_bonds, num_angles, shortest_bond (Angstrom) and coordination_numbers per site.
    """
    analyzer = BondAnalyzer(structure, cutoff)
    bonds = analyzer.find_bonds()
    return {
        "formula": str(structure.formula),
        "num_bonds": len(bonds),
        "num_angles": len(analyzer.get_bond_angles()),
        "shortest_bond": min(bond[2] for bond in bonds) if bonds else None,
        "coordination_numbers": analyzer.get_coordination_numbers(),
    }


@tool
def analyze_structure(structure: Structure) -> dict[str, Any]:
    """Global geometry of a structure: center of mass, radius of gyration and density.

    Args:
        structure: Structure to analyze.
    """
    analyzer = StructureAnalyzer(structure)
    return {
        "formula": str(structure.formula),
        "num_atoms": len(structure),
        "center_of_mass": analyzer.center_of_mass(),
        "radius_of_gyration": analyzer.radius_of_gyration(),
        "density": analyzer.density(),
    }


@tool
def calculate_lennard_jones(structure: Structure, sigma: float = 3.4, epsilon: float = 0.0104) -> dict[str, Any]:
    """Lennard-Jones energy (eV), forces (eV/Angstrom) and, for crystals, stress (eV/Angstrom^3).

    Args:
        structure: Structure to calculate.
        sigma: Distance parameter in Angstrom (3.4 is argon).
        epsilon: Well depth in eV (0.0104 is argon).
    """
    from ..calculator import LennardJones

    results = LennardJones(sigma=sigma, epsilon=epsilon).compute(structure)
    data: dict[str, Any] = {"formula": str(structure.formula), "num_atoms": len(structure),
                            "energy": results.energy}
    if results.forces is not None:
        data["forces"] = results.forces
    if results.stress is not None:
        data["stress"] = results.stress
    return data


@tool(paths=("directory",))
def write_vasp_input(
    structure: Crystal,
    directory: str = "vasp_calc",
    incar: dict[str, Any] | None = None,
    kpoints: list[int] | None = None,
) -> dict[str, Any]:
    """Write VASP input files (INCAR, KPOINTS, POSCAR) without running VASP.

    No POTCAR is written; add one from your licensed VASP pseudopotentials.

    Args:
        structure: Crystal to calculate.
        directory: Output directory in the workspace.
        incar: INCAR tags, e.g. {"ENCUT": 520, "ISMEAR": 0}.
        kpoints: Monkhorst-Pack grid, e.g. [6, 6, 6].
    """
    from ..calculator import VaspCalculator

    calculator = VaspCalculator(directory=directory, incar=incar, kpoints=kpoints, copy_potcar=False)
    path = calculator.write_input(structure, directory)
    return {"directory": path, "files": sorted(item.name for item in path.iterdir())}


@tool
def list_workspace_files(context: ToolContext, pattern: str = "*") -> list[str]:
    """Files in the workspace that match a glob pattern, e.g. "*.cif" or "**/*.vasp".

    Args:
        pattern: Glob pattern relative to the workspace.
    """
    root = context.workspace
    return sorted(str(path.relative_to(root)) for path in root.glob(pattern) if path.is_file())


def _database(context: ToolContext):
    from ..storage import DataStorage, MemoryBackend

    database = context.state.get("storage")
    if database is None:
        database = context.state["storage"] = DataStorage(backend=MemoryBackend())
    return database


@tool
def store_structure(structure: Structure, context: ToolContext, metadata: dict[str, Any] | None = None) -> dict:
    """Store a structure in this session's database and return its document id.

    Args:
        structure: Structure to store.
        metadata: Key-value metadata for queries, e.g. {"project": "demo"}.
    """
    doc_id = _database(context).store_data(structure, metadata=metadata or {})
    return {"doc_id": doc_id, "formula": str(structure.formula), "num_atoms": len(structure)}


@tool
def retrieve_structure(doc_id: str, context: ToolContext) -> Structure:
    """Retrieve a stored structure by document id.

    Args:
        doc_id: Id returned by ``store_structure``.
    """
    structure = _database(context).retrieve_data(doc_id)
    if not isinstance(structure, Structure):
        raise ToolError(f"document {doc_id!r} is not a structure")
    return structure


@tool
def query_structures(context: ToolContext, metadata: dict[str, Any], limit: int = 20) -> list[dict]:
    """Find stored structures whose metadata matches all given key-value pairs.

    Args:
        metadata: Metadata to match, e.g. {"project": "demo"}.
        limit: Maximum number of results.
    """
    criteria = {f"metadata.{key}": value for key, value in metadata.items()}
    found = _database(context).query(criteria, limit=limit)
    return [{"formula": str(item.formula), "num_atoms": len(item)} if isinstance(item, Structure)
            else {"document": str(item)[:200]} for item in found]

