"""
Graph representation for Crystal and Molecule structures.

Provides object-oriented graph classes for analyzing molecular and crystal
structure connectivity. Supports graph algorithms, ML framework integration,
and topological analysis.

Classes:
    - StructureGraph: Base class for structure graphs
    - MoleculeGraph: Graph representation of molecules
    - CrystalGraph: Graph representation of crystals with PBC support
"""

import numpy as np
from typing import Optional, Union, Dict, Any, List, Tuple, Set
from scipy.spatial.distance import cdist
from abc import ABC, abstractmethod
from .crystal import Crystal
from .molecule import Molecule


class StructureGraph(ABC):
    """
    Abstract base class for structure graph representations.

    Provides common graph algorithms and properties for both molecular
    and crystal structure graphs.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.

    Attributes:
        structure: The underlying structure object.
        cutoff: Edge cutoff distance.

    Examples:
        >>> # Use MoleculeGraph or CrystalGraph subclasses
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> graph = MoleculeGraph(mol, cutoff=2.0)
        >>> print(graph.num_nodes)  # 2
    """

    def __init__(self, structure: Union[Crystal, Molecule], cutoff: float = 3.0):
        """
        Initialize the structure graph.

        Args:
            structure: Crystal or Molecule object.
            cutoff: Cutoff distance in Angstroms for defining edges.
        """
        self.structure = structure
        self.cutoff = cutoff
        self._adjacency_matrix: Optional[np.ndarray] = None
        self._distance_matrix: Optional[np.ndarray] = None
        self._edge_list: Optional[List[Tuple[int, int]]] = None

    @property
    def num_nodes(self) -> int:
        """Get number of nodes (atoms)."""
        return len(self.structure)

    @property
    @abstractmethod
    def adjacency_matrix(self) -> np.ndarray:
        """Get adjacency matrix (computed lazily)."""
        pass

    @property
    @abstractmethod
    def distance_matrix(self) -> np.ndarray:
        """Get distance matrix (computed lazily)."""
        pass

    @property
    def edge_list(self) -> List[Tuple[int, int, float]]:
        """
        Get edge list with distances.

        Returns:
            List of (source, target, distance) tuples.
        """
        if self._edge_list is None:
            edges = []
            adj = self.adjacency_matrix
            dist = self.distance_matrix

            for i in range(self.num_nodes):
                for j in range(i + 1, self.num_nodes):
                    if adj[i, j] == 1:
                        edges.append((i, j, dist[i, j]))

            self._edge_list = edges

        return self._edge_list

    @property
    def num_edges(self) -> int:
        """Get number of edges."""
        return len(self.edge_list)

    @property
    def coordination_numbers(self) -> Dict[int, int]:
        """
        Get coordination number for each atom.

        Returns:
            Dictionary mapping atom index to coordination number.
        """
        adj = self.adjacency_matrix
        return {i: int(adj[i].sum()) for i in range(self.num_nodes)}

    @property
    def degree_distribution(self) -> Dict[int, int]:
        """
        Get degree distribution.

        Returns:
            Dictionary mapping coordination number to count.
        """
        from collections import Counter

        coord = self.coordination_numbers
        return dict(Counter(coord.values()))

    @property
    def is_connected(self) -> bool:
        """
        Check if graph is connected.

        Returns:
            True if there's a path between any two atoms.
        """
        if self.num_nodes <= 1:
            return True

        # BFS
        visited = {0}
        queue = [0]
        adj = self.adjacency_matrix

        while queue:
            node = queue.pop(0)
            for neighbor in range(self.num_nodes):
                if adj[node, neighbor] == 1 and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == self.num_nodes

    @property
    def connected_components(self) -> List[List[int]]:
        """
        Find connected components.

        Returns:
            List of components, each is a list of atom indices.
        """
        if self.num_nodes == 0:
            return []

        adj = self.adjacency_matrix
        visited = set()
        components = []

        for start in range(self.num_nodes):
            if start in visited:
                continue

            # BFS
            component = []
            queue = [start]
            visited.add(start)

            while queue:
                node = queue.pop(0)
                component.append(node)

                for neighbor in range(self.num_nodes):
                    if adj[node, neighbor] == 1 and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            components.append(sorted(component))

        return components

    def get_shortest_path(self, start_idx: int, end_idx: int) -> Optional[List[int]]:
        """
        Find shortest path between two atoms.

        Args:
            start_idx: Starting atom index.
            end_idx: Ending atom index.

        Returns:
            List of atom indices in path, or None if no path exists.

        Raises:
            IndexError: If indices are out of range.
        """
        if not (0 <= start_idx < self.num_nodes):
            raise IndexError(f"start_idx {start_idx} out of range")
        if not (0 <= end_idx < self.num_nodes):
            raise IndexError(f"end_idx {end_idx} out of range")

        if start_idx == end_idx:
            return [start_idx]

        # BFS with path tracking
        adj = self.adjacency_matrix
        visited = {start_idx}
        queue = [(start_idx, [start_idx])]

        while queue:
            node, path = queue.pop(0)

            for neighbor in range(self.num_nodes):
                if adj[node, neighbor] == 1:
                    if neighbor == end_idx:
                        return path + [neighbor]

                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))

        return None

    @property
    def diameter(self) -> Optional[int]:
        """
        Get graph diameter (longest shortest path).

        Returns:
            Diameter as integer, or None if disconnected.
        """
        if not self.is_connected:
            return None

        if self.num_nodes <= 1:
            return 0

        max_dist = 0
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                path = self.get_shortest_path(i, j)
                if path:
                    max_dist = max(max_dist, len(path) - 1)

        return max_dist

    @property
    def node_features(self) -> np.ndarray:
        """
        Get node features for GNN.

        Returns:
            Feature matrix of shape (N, F).
        """
        atomic_numbers = np.array(
            [elem.atomic_no for elem in self.structure.elements]
        ).reshape(-1, 1)

        return atomic_numbers

    @property
    def laplacian(self) -> np.ndarray:
        """
        Get graph Laplacian matrix.

        Returns:
            Laplacian matrix L = D - A.
        """
        adj = self.adjacency_matrix
        degree = adj.sum(axis=1)
        D = np.diag(degree)
        return D - adj

    def get_normalized_laplacian(self) -> np.ndarray:
        """
        Get normalized graph Laplacian.

        Returns:
            Normalized Laplacian L = I - D^(-1/2) A D^(-1/2).
        """
        adj = self.adjacency_matrix
        degree = adj.sum(axis=1)
        D_inv_sqrt = np.diag(1.0 / np.sqrt(degree + 1e-10))
        I = np.eye(self.num_nodes)
        return I - D_inv_sqrt @ adj @ D_inv_sqrt

    @property
    def statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive graph statistics.

        Returns:
            Dictionary with graph properties.
        """
        coord_values = list(self.coordination_numbers.values())

        return {
            "num_nodes": self.num_nodes,
            "num_edges": self.num_edges,
            "is_connected": self.is_connected,
            "num_components": len(self.connected_components),
            "diameter": self.diameter,
            "avg_coordination": np.mean(coord_values) if coord_values else 0.0,
            "max_coordination": max(coord_values) if coord_values else 0,
            "min_coordination": min(coord_values) if coord_values else 0,
            "degree_distribution": self.degree_distribution,
        }

    def to_networkx(self):
        """
        Convert to NetworkX graph.

        Returns:
            NetworkX Graph object.

        Raises:
            ImportError: If networkx is not installed.
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError(
                "NetworkX is required. Install with: pip install networkx"
            )

        G = nx.Graph()

        # Add nodes
        for i, (spec, pos) in enumerate(
            zip(self.structure.species, self.structure.positions)
        ):
            G.add_node(i, species=spec, position=pos.tolist())

        # Add edges
        for i, j, dist in self.edge_list:
            G.add_edge(i, j, distance=dist)

        return G

    def find_rings(self, max_ring_size: int = 10) -> List[List[int]]:
        """
        Find ring structures in the graph.

        Args:
            max_ring_size: Maximum ring size to search for.

        Returns:
            List of rings (each is a list of atom indices).
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError(
                "NetworkX is required for ring finding. "
                "Install with: pip install networkx"
            )

        G = self.to_networkx()

        try:
            cycles = list(nx.simple_cycles(G.to_directed()))
            rings = []
            seen_rings = set()

            for cycle in cycles:
                if 3 <= len(cycle) <= max_ring_size:
                    normalized = tuple(sorted(cycle))
                    if normalized not in seen_rings:
                        seen_rings.add(normalized)
                        rings.append(cycle)

            return rings
        except:
            return []

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"{self.__class__.__name__}(nodes={self.num_nodes}, "
            f"edges={self.num_edges}, cutoff={self.cutoff})"
        )


class MoleculeGraph(StructureGraph):
    """
    Graph representation of a Molecule structure.

    Args:
        molecule: Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import MoleculeGraph
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> graph = MoleculeGraph(mol, cutoff=2.0)
        >>> print(graph.num_nodes)  # 2
        >>> print(graph.num_edges)  # 1
        >>> print(graph.is_connected)  # True
    """

    def __init__(self, molecule: Molecule, cutoff: float = 3.0):
        """
        Initialize molecule graph.

        Args:
            molecule: Molecule object.
            cutoff: Cutoff distance in Angstroms.
        """
        if not isinstance(molecule, Molecule):
            raise TypeError(f"Expected Molecule, got {type(molecule)}")
        super().__init__(molecule, cutoff)

    @property
    def adjacency_matrix(self) -> np.ndarray:
        """
        Get adjacency matrix (cached).

        Returns:
            Binary adjacency matrix of shape (N, N).
        """
        if self._adjacency_matrix is None:
            positions = self.structure.positions
            dist_matrix = cdist(positions, positions)
            self._adjacency_matrix = (dist_matrix < self.cutoff).astype(int)
            np.fill_diagonal(self._adjacency_matrix, 0)

        return self._adjacency_matrix

    @property
    def distance_matrix(self) -> np.ndarray:
        """
        Get distance matrix (cached).

        Returns:
            Distance matrix of shape (N, N).
        """
        if self._distance_matrix is None:
            positions = self.structure.positions
            self._distance_matrix = cdist(positions, positions)

        return self._distance_matrix


class CrystalGraph(StructureGraph):
    """
    Graph representation of a Crystal structure with PBC support.

    Args:
        crystal: Crystal object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions (default: True).

    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.core.graph import CrystalGraph
        >>>
        >>> lat = Lattice(10)
        >>> crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]], lat)
        >>> graph = CrystalGraph(crystal, cutoff=5.0)
        >>> print(graph.num_nodes)  # 2
        >>> coord = graph.coordination_numbers
        >>> print(coord)  # {0: X, 1: Y}
    """

    def __init__(self, crystal: Crystal, cutoff: float = 3.0, use_pbc: bool = True):
        """
        Initialize crystal graph.

        Args:
            crystal: Crystal object.
            cutoff: Cutoff distance in Angstroms.
            use_pbc: Use periodic boundary conditions.
        """
        if not isinstance(crystal, Crystal):
            raise TypeError(f"Expected Crystal, got {type(crystal)}")
        super().__init__(crystal, cutoff)
        self.use_pbc = use_pbc

    @property
    def adjacency_matrix(self) -> np.ndarray:
        """
        Get adjacency matrix with PBC support (cached).

        Returns:
            Binary adjacency matrix of shape (N, N).
        """
        if self._adjacency_matrix is None:
            n_atoms = self.num_nodes
            adj = np.zeros((n_atoms, n_atoms), dtype=int)

            if self.use_pbc:
                neighbors = self.structure.get_neighbor_list(self.cutoff, use_pbc=True)
                for i, neighbor_list in neighbors.items():
                    for j, dist in neighbor_list:
                        adj[i, j] = 1
            else:
                positions = self.structure.cart_positions
                dist_matrix = cdist(positions, positions)
                adj = (dist_matrix < self.cutoff).astype(int)
                np.fill_diagonal(adj, 0)

            self._adjacency_matrix = adj

        return self._adjacency_matrix

    @property
    def distance_matrix(self) -> np.ndarray:
        """
        Get distance matrix with PBC support (cached).

        Returns:
            Distance matrix of shape (N, N).
        """
        if self._distance_matrix is None:
            if self.use_pbc:
                n_atoms = self.num_nodes
                dist_matrix = np.full((n_atoms, n_atoms), np.inf)
                np.fill_diagonal(dist_matrix, 0.0)

                # Use neighbor list with large cutoff
                neighbors = self.structure.get_neighbor_list(cutoff=20.0, use_pbc=True)
                for i, neighbor_list in neighbors.items():
                    for j, dist in neighbor_list:
                        dist_matrix[i, j] = dist

                self._distance_matrix = dist_matrix
            else:
                positions = self.structure.cart_positions
                self._distance_matrix = cdist(positions, positions)

        return self._distance_matrix


# Convenience factory function
def create_structure_graph(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> StructureGraph:
    """
    Factory function to create appropriate graph for structure.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms.
        use_pbc: Use PBC (only for Crystal). If None, defaults to True for Crystal.

    Returns:
        MoleculeGraph or CrystalGraph instance.

    Examples:
        >>> graph = create_structure_graph(molecule, cutoff=2.0)
        >>> # Returns MoleculeGraph automatically
    """
    if isinstance(structure, Molecule):
        return MoleculeGraph(structure, cutoff)
    elif isinstance(structure, Crystal):
        if use_pbc is None:
            use_pbc = True
        return CrystalGraph(structure, cutoff, use_pbc)
    else:
        raise TypeError(f"Expected Crystal or Molecule, got {type(structure)}")


# ============================================================================
# Backward Compatibility: Functional Interface
# ============================================================================
# These functions maintain the old API while using the new OOP implementation


def structure_to_graph_data(
    structure: Union[Crystal, Molecule],
    cutoff: float = 5.0,
    threebody_cutoff: float = 4.0,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convert MatSimPy structure to graph data format.

    Note: This is a legacy function. Consider using create_structure_graph() for OOP API.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff radius for graph construction (Å).
        threebody_cutoff: Cutoff for three-body interactions (Å).
        **kwargs: Additional parameters.

    Returns:
        Dictionary containing graph data.
    """
    if isinstance(structure, Crystal):
        positions = np.array(structure.cart_positions, dtype=np.float64)
        cell = np.array(structure.lattice.lattice_vectors, dtype=np.float64)
        pbc = np.array(structure.pbc, dtype=bool)
        is_crystal = True
    else:
        positions = np.array(structure.positions, dtype=np.float64)
        cell = None
        pbc = np.array([False, False, False], dtype=bool)
        is_crystal = False

    species = list(structure.species)

    return {
        "positions": positions,
        "species": species,
        "cell": cell,
        "pbc": pbc,
        "num_atoms": len(structure),
        "is_crystal": is_crystal,
        "cutoff": cutoff,
        "threebody_cutoff": threebody_cutoff,
    }


def get_adjacency_matrix(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> np.ndarray:
    """Get adjacency matrix (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.adjacency_matrix


def get_distance_matrix(
    structure: Union[Crystal, Molecule], use_pbc: bool = None
) -> np.ndarray:
    """Get distance matrix (functional API)."""
    graph = create_structure_graph(structure, cutoff=20.0, use_pbc=use_pbc)
    return graph.distance_matrix


def get_edge_list(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None,
    include_distances: bool = False,
) -> Union[List[Tuple[int, int]], List[Tuple[int, int, float]]]:
    """Get edge list (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    edges = graph.edge_list

    if not include_distances:
        return [(i, j) for i, j, d in edges]
    return edges


def get_coordination_numbers(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> Dict[int, int]:
    """Get coordination numbers (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.coordination_numbers


def get_degree_distribution(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> Dict[int, int]:
    """Get degree distribution (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.degree_distribution


def is_connected(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> bool:
    """Check if graph is connected (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.is_connected


def get_connected_components(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> List[List[int]]:
    """Get connected components (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.connected_components


def get_shortest_path(
    structure: Union[Crystal, Molecule],
    start_idx: int,
    end_idx: int,
    cutoff: float = 3.0,
    use_pbc: bool = None,
) -> Optional[List[int]]:
    """Get shortest path (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.get_shortest_path(start_idx, end_idx)


def get_graph_diameter(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> Optional[int]:
    """Get graph diameter (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.diameter


def get_node_features(
    structure: Union[Crystal, Molecule], include_properties: bool = True
) -> np.ndarray:
    """Get node features (functional API)."""
    graph = create_structure_graph(structure, cutoff=3.0)
    return graph.node_features


def get_graph_statistics(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
) -> Dict[str, Any]:
    """Get graph statistics (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.statistics


def structure_to_networkx(
    structure: Union[Crystal, Molecule], cutoff: float = 3.0, use_pbc: bool = None
):
    """Convert to NetworkX graph (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.to_networkx()


def get_rings(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    max_ring_size: int = 10,
    use_pbc: bool = None,
) -> List[List[int]]:
    """Find rings (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.find_rings(max_ring_size)


def get_graph_laplacian(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None,
    normalized: bool = False,
) -> np.ndarray:
    """Get graph Laplacian (functional API)."""
    graph = create_structure_graph(structure, cutoff, use_pbc)
    if normalized:
        return graph.get_normalized_laplacian()
    return graph.laplacian


__all__ = [
    # OOP API (recommended)
    "StructureGraph",
    "MoleculeGraph",
    "CrystalGraph",
    "create_structure_graph",
    # Functional API (backward compatibility)
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
