"""Analysis skill — bond, structure, topology, and neighbor analysis."""

from matsimpy.analysis.bonding import BondAnalyzer
from matsimpy.analysis.structure import StructureAnalyzer
from matsimpy.analysis.topology import TopologyAnalyzer
from matsimpy.analysis.neighbors import find_points_in_spheres
from matsimpy.io import read as io_read
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "analysis"
SKILL_DESCRIPTION = "Structure analysis: bonds, geometry, connectivity, symmetry, neighbors"


def _load_structure(path):
    return io_read(path)


def _analyze_bonds(path, cutoff=2.0):
    s = _load_structure(path)
    ba = BondAnalyzer(s, cutoff)
    bonds = ba.find_bonds()
    angles = ba.get_bond_angles()
    cn = ba.get_coordination_numbers()
    return {
        "formula": s.formula,
        "num_bonds": len(bonds),
        "num_angles": len(angles),
        "shortest_bond": min(b[2] for b in bonds) if bonds else None,
        "coordination_numbers": cn,
    }


def _analyze_structure(path):
    s = _load_structure(path)
    sa = StructureAnalyzer(s)
    com = sa.center_of_mass().tolist()
    rgyr = sa.radius_of_gyration()
    density = sa.density()
    return {
        "formula": s.formula,
        "num_atoms": len(s),
        "center_of_mass": com,
        "radius_of_gyration": rgyr,
        "density": density,
    }


def _analyze_connectivity(path, cutoff=2.0):
    s = _load_structure(path)
    ta = TopologyAnalyzer(s, cutoff)
    return {
        "formula": s.formula,
        "is_connected": ta.is_connected(),
        "num_components": len(ta.connected_components()),
        "coordination": ta.coordination_numbers(),
    }


def _analyze_symmetry(path):
    s = _load_structure(path)
    if hasattr(s, "get_symmetry_info"):
        return s.get_symmetry_info()
    return {"error": "Symmetry analysis requires Crystal with spglib installed"}


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="analyze_bonds",
            description="Analyze bonds, angles, and coordination in a structure",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to structure file"},
                    "cutoff": {"type": "number", "description": "Bond cutoff in Angstrom", "default": 2.0},
                },
                "required": ["path"],
            },
            callable=_analyze_bonds,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="analyze_structure",
            description="Analyze global geometric properties (COM, radius of gyration, density)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to structure file"},
                },
                "required": ["path"],
            },
            callable=_analyze_structure,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="analyze_connectivity",
            description="Analyze structural connectivity (connected components, rings, paths)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to structure file"},
                    "cutoff": {"type": "number", "description": "Bond cutoff in Angstrom", "default": 2.0},
                },
                "required": ["path"],
            },
            callable=_analyze_connectivity,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="analyze_symmetry",
            description="Get space group, point group, and crystal system information",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to structure file"},
                },
                "required": ["path"],
            },
            callable=_analyze_symmetry,
            skill=SKILL_NAME,
        ),
    ]
