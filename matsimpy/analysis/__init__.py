"""
Analysis tools for structures.

This module provides:
- Graph representations (StructureGraph, MoleculeGraph, CrystalGraph)
- Graph algorithms (shortest path, connected components, rings)
- Graph properties (adjacency matrix, distance matrix, coordination numbers)
- Structure analysis (distances, angles, etc.)
- Bond analysis
- Topological analysis

Note:
- Symmetry analysis is in matsimpy.symmetry module.
"""

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

__all__ = [
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
]
