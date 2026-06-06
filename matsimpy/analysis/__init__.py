"""
Analysis tools for structures.

This module provides:
- Neighbor finding (find_points_in_spheres, validate_cutoff)
- Graph representations (StructureGraph, MoleculeGraph, CrystalGraph)
- Graph algorithms (shortest path, connected components, rings)
- Graph properties (adjacency matrix, distance matrix, coordination numbers)
- Structure analysis (distances, angles, etc.)
- Bond analysis
- Atom selection (select_by_species, AtomSelection, etc.)
- Topological analysis

Note:
- Symmetry analysis is in matsimpy.symmetry module.
"""

from .selection import (
    select_by_species,
    select_by_indices,
    select_by_position,
    select_by_box,
    select_by_property,
    select_by_custom,
    combine_selections,
    select_all,
    select_none,
    AtomSelection,
)

from .neighbors import (
    find_points_in_spheres,
    validate_cutoff,
)

from .graph import (
    StructureGraph,
    MoleculeGraph,
    CrystalGraph,
    create_structure_graph,
    structure_to_graph_data,
    get_adjacency_matrix,
    get_distance_matrix,
    get_edge_list,
    get_coordination_numbers,
    get_degree_distribution,
    is_connected,
    get_connected_components,
    get_shortest_path,
    get_graph_diameter,
    get_node_features,
    get_graph_statistics,
    structure_to_networkx,
    get_rings,
    get_graph_laplacian,
)

from .bonding import BondAnalyzer
from .structure import StructureAnalyzer
from .topology import TopologyAnalyzer

__all__ = [
    "find_points_in_spheres",
    "validate_cutoff",
    "StructureGraph",
    "MoleculeGraph",
    "CrystalGraph",
    "create_structure_graph",
    "structure_to_graph_data",
    "get_adjacency_matrix",
    "get_distance_matrix",
    "get_edge_list",
    "get_coordination_numbers",
    "get_degree_distribution",
    "is_connected",
    "get_connected_components",
    "get_shortest_path",
    "get_graph_diameter",
    "get_node_features",
    "get_graph_statistics",
    "structure_to_networkx",
    "get_rings",
    "get_graph_laplacian",
    "select_by_species",
    "select_by_indices",
    "select_by_position",
    "select_by_box",
    "select_by_property",
    "select_by_custom",
    "combine_selections",
    "select_all",
    "select_none",
    "AtomSelection",
    "BondAnalyzer",
    "StructureAnalyzer",
    "TopologyAnalyzer",
]
