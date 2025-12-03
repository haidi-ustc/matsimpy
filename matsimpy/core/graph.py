"""
Graph module for MatSimPy.

This module provides graph representations for Crystal and Molecule structures,
enabling connectivity analysis, graph algorithms, and machine learning integration.

The module provides:
- Object-oriented graph classes (StructureGraph, MoleculeGraph, CrystalGraph)
- Graph algorithms (shortest path, connected components, rings)
- Graph properties (adjacency matrix, distance matrix, coordination numbers)
- NetworkX integration
- Functional API for backward compatibility

Example:
    >>> from matsimpy.core import Crystal, Molecule, Lattice
    >>> from matsimpy.core.graph import MoleculeGraph, CrystalGraph, create_structure_graph
    >>>
    >>> # Create molecule graph
    >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
    >>> graph = MoleculeGraph(mol, cutoff=2.0)
    >>> print(graph.num_nodes)  # 2
    >>> print(graph.is_connected)  # True
    >>>
    >>> # Create crystal graph with PBC
    >>> lat = Lattice.cubic(10)
    >>> crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]], lat)
    >>> graph = CrystalGraph(crystal, cutoff=5.0, use_pbc=True)
    >>> coord = graph.coordination_numbers
    >>>
    >>> # Factory function
    >>> graph = create_structure_graph(mol, cutoff=2.0)
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
    and crystal structure graphs. This class should not be instantiated
    directly - use :class:`MoleculeGraph` or :class:`CrystalGraph` instead.

    The StructureGraph class provides:
    - Graph construction from atomic structures
    - Adjacency and distance matrices
    - Graph algorithms (shortest path, connected components, rings)
    - Graph properties (coordination numbers, degree distribution)
    - NetworkX integration
    - Graph statistics

    Attributes:
        structure (Union[Crystal, Molecule]): The underlying structure object.
        cutoff (float): Edge cutoff distance in Angstroms.
        num_nodes (int): Number of nodes (atoms) in the graph (property).
        num_edges (int): Number of edges in the graph (property).
        adjacency_matrix (np.ndarray): Binary adjacency matrix (property).
        distance_matrix (np.ndarray): Distance matrix in Angstroms (property).
        edge_list (List[Tuple[int, int, float]]): List of edges with distances (property).
        coordination_numbers (Dict[int, int]): Coordination number for each atom (property).
        degree_distribution (Dict[int, int]): Degree distribution (property).
        is_connected (bool): Whether graph is connected (property).
        connected_components (List[List[int]]): List of connected components (property).
        diameter (Optional[int]): Graph diameter (property).
        node_features (np.ndarray): Node features for GNN (property).
        laplacian (np.ndarray): Graph Laplacian matrix (property).
        statistics (Dict[str, Any]): Comprehensive graph statistics (property).

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).

    Note:
        This is an abstract class. Subclasses must implement:
        - :meth:`adjacency_matrix`: Compute adjacency matrix
        - :meth:`distance_matrix`: Compute distance matrix

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import MoleculeGraph
        >>>
        >>> # Use MoleculeGraph or CrystalGraph subclasses
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> graph = MoleculeGraph(mol, cutoff=2.0)
        >>> print(graph.num_nodes)  # 2
        >>> print(graph.num_edges)  # 1
        >>> print(graph.is_connected)  # True
        >>> print(graph.coordination_numbers)  # {0: 1, 1: 1}
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
        """
        Get the number of nodes (atoms) in the graph.

        Returns:
            int: Number of nodes, equal to the number of atoms in the structure.

        Example:
            >>> graph.num_nodes
            2
        """
        return len(self.structure)

    @property
    @abstractmethod
    def adjacency_matrix(self) -> np.ndarray:
        """
        Get the adjacency matrix (abstract method, computed lazily).

        Returns:
            np.ndarray: Binary adjacency matrix of shape (N, N) where N is the
                       number of atoms. Entry (i, j) is 1 if atoms i and j are
                       within cutoff distance, 0 otherwise.

        Note:
            This is an abstract method that must be implemented by subclasses.
            The matrix is typically cached for performance.
        """
        pass

    @property
    @abstractmethod
    def distance_matrix(self) -> np.ndarray:
        """
        Get the distance matrix (abstract method, computed lazily).

        Returns:
            np.ndarray: Distance matrix of shape (N, N) where N is the number
                       of atoms. Entry (i, j) is the distance between atoms i
                       and j in Angstroms.

        Note:
            This is an abstract method that must be implemented by subclasses.
            The matrix is typically cached for performance.
        """
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
        """
        Get the number of edges in the graph.

        Returns:
            int: Number of edges (bonds) in the graph.

        Example:
            >>> graph.num_edges
            1
        """
        return len(self.edge_list)

    @property
    def coordination_numbers(self) -> Dict[int, int]:
        """
        Get coordination number for each atom.

        The coordination number is the number of neighbors within the cutoff distance.

        Returns:
            Dict[int, int]: Dictionary mapping atom index to coordination number
                           (number of neighbors).

        Example:
            >>> coord = graph.coordination_numbers
            >>> coord[0]  # Coordination number of atom 0
            4
        """
        adj = self.adjacency_matrix
        return {i: int(adj[i].sum()) for i in range(self.num_nodes)}

    @property
    def degree_distribution(self) -> Dict[int, int]:
        """
        Get the degree distribution of the graph.

        Returns:
            Dict[int, int]: Dictionary mapping coordination number (degree) to
                           the count of atoms with that coordination number.

        Example:
            >>> dist = graph.degree_distribution
            >>> dist[4]  # Number of atoms with coordination number 4
            8
        """
        from collections import Counter

        coord = self.coordination_numbers
        return dict(Counter(coord.values()))

    @property
    def is_connected(self) -> bool:
        """
        Check if the graph is connected.

        A graph is connected if there exists a path between any two atoms.

        Returns:
            bool: True if the graph is connected, False otherwise.

        Example:
            >>> graph.is_connected
            True
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
        Find all connected components in the graph.

        Returns:
            List[List[int]]: List of connected components. Each component is
                            a list of atom indices belonging to that component.

        Example:
            >>> components = graph.connected_components
            >>> len(components)  # Number of components
            1
            >>> components[0]  # First component
            [0, 1, 2, 3]
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
        Get the graph diameter (longest shortest path).

        The diameter is the maximum shortest path length between any two atoms.

        Returns:
            Optional[int]: Graph diameter as integer, or None if the graph is
                          disconnected. Returns 0 for graphs with 1 or fewer nodes.

        Example:
            >>> graph.diameter
            3
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
        Get node features for graph neural networks (GNN).

        Currently returns atomic numbers as node features.

        Returns:
            np.ndarray: Feature matrix of shape (N, F) where N is the number
                       of nodes and F is the number of features (currently 1).

        Example:
            >>> features = graph.node_features
            >>> features.shape
            (10, 1)  # 10 atoms, 1 feature (atomic number)
            >>> features[0]  # Atomic number of first atom
            array([6])  # Carbon
        """
        atomic_numbers = np.array(
            [elem.atomic_no for elem in self.structure.elements]
        ).reshape(-1, 1)

        return atomic_numbers

    @property
    def laplacian(self) -> np.ndarray:
        """
        Get the graph Laplacian matrix.

        The Laplacian matrix is defined as L = D - A, where D is the degree
        matrix and A is the adjacency matrix.

        Returns:
            np.ndarray: Laplacian matrix of shape (N, N) where N is the number
                       of nodes.

        Example:
            >>> L = graph.laplacian
            >>> L.shape
            (10, 10)
        """
        adj = self.adjacency_matrix
        degree = adj.sum(axis=1)
        D = np.diag(degree)
        return D - adj

    def get_normalized_laplacian(self) -> np.ndarray:
        """
        Get the normalized graph Laplacian matrix.

        The normalized Laplacian is defined as L = I - D^(-1/2) A D^(-1/2),
        where I is the identity matrix, D is the degree matrix, and A is the
        adjacency matrix.

        Returns:
            np.ndarray: Normalized Laplacian matrix of shape (N, N) where N
                       is the number of nodes.

        Example:
            >>> L_norm = graph.get_normalized_laplacian()
            >>> L_norm.shape
            (10, 10)
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
            Dict[str, Any]: Dictionary containing:
                - num_nodes: Number of nodes
                - num_edges: Number of edges
                - is_connected: Whether graph is connected
                - num_components: Number of connected components
                - diameter: Graph diameter
                - avg_coordination: Average coordination number
                - max_coordination: Maximum coordination number
                - min_coordination: Minimum coordination number
                - degree_distribution: Degree distribution dictionary

        Example:
            >>> stats = graph.statistics
            >>> stats['num_nodes']
            10
            >>> stats['avg_coordination']
            4.0
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
        """
        Get unambiguous string representation for debugging.

        Returns:
            str: String representation with class name, number of nodes,
                number of edges, and cutoff distance.

        Example:
            >>> repr(graph)
            'MoleculeGraph(nodes=2, edges=1, cutoff=2.0)'
        """
        return (
            f"{self.__class__.__name__}(nodes={self.num_nodes}, "
            f"edges={self.num_edges}, cutoff={self.cutoff})"
        )


class MoleculeGraph(StructureGraph):
    """
    Graph representation of a Molecule structure.

    MoleculeGraph extends :class:`StructureGraph` to provide graph representation
    for non-periodic molecular structures. Distances are computed using Cartesian
    coordinates without periodic boundary conditions.

    Attributes:
        structure (Molecule): The underlying Molecule object.
        cutoff (float): Edge cutoff distance in Angstroms.
        All properties from :class:`StructureGraph` are available.

    Args:
        molecule: Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).

    Raises:
        TypeError: If molecule is not a Molecule instance.

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import MoleculeGraph
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> graph = MoleculeGraph(mol, cutoff=2.0)
        >>> print(graph.num_nodes)  # 2
        >>> print(graph.num_edges)  # 1
        >>> print(graph.is_connected)  # True
        >>> print(graph.coordination_numbers)  # {0: 1, 1: 1}
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

    CrystalGraph extends :class:`StructureGraph` to provide graph representation
    for periodic crystal structures. Supports both periodic and non-periodic
    neighbor finding.

    Attributes:
        structure (Crystal): The underlying Crystal object.
        cutoff (float): Edge cutoff distance in Angstroms.
        use_pbc (bool): Whether to use periodic boundary conditions.
        All properties from :class:`StructureGraph` are available.

    Args:
        crystal: Crystal object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (default: True).
                If True, distances are computed with PBC; if False, only
                within-unit-cell distances are considered.

    Raises:
        TypeError: If crystal is not a Crystal instance.

    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.core.graph import CrystalGraph
        >>>
        >>> lat = Lattice.cubic(10)
        >>> crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]], lat)
        >>> graph = CrystalGraph(crystal, cutoff=5.0, use_pbc=True)
        >>> print(graph.num_nodes)  # 2
        >>> coord = graph.coordination_numbers
        >>> print(coord)  # {0: 4, 1: 4}
        >>>
        >>> # Without PBC
        >>> graph_no_pbc = CrystalGraph(crystal, cutoff=5.0, use_pbc=False)
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
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> StructureGraph:
    """
    Factory function to create appropriate graph for structure.

    Automatically creates a :class:`MoleculeGraph` for molecules or a
    :class:`CrystalGraph` for crystals.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        StructureGraph: A :class:`MoleculeGraph` or :class:`CrystalGraph` instance.

    Raises:
        TypeError: If structure is not a Crystal or Molecule instance.

    Examples:
        >>> from matsimpy.core import Molecule, Crystal, Lattice
        >>> from matsimpy.core.graph import create_structure_graph
        >>>
        >>> # Automatically creates MoleculeGraph
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> graph = create_structure_graph(mol, cutoff=2.0)
        >>> type(graph).__name__
        'MoleculeGraph'
        >>>
        >>> # Automatically creates CrystalGraph
        >>> crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(10))
        >>> graph = create_structure_graph(crystal, cutoff=5.0)
        >>> type(graph).__name__
        'CrystalGraph'
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
    Convert MatSimPy structure to graph data format (legacy functional API).

    This is a legacy function that converts a structure to a dictionary format
    suitable for graph-based machine learning. For new code, consider using
    the OOP API (:class:`MoleculeGraph` or :class:`CrystalGraph`) instead.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff radius in Angstroms for graph construction (default: 5.0).
        threebody_cutoff: Cutoff for three-body interactions in Angstroms (default: 4.0).
        **kwargs: Additional parameters (currently unused).

    Returns:
        Dict[str, Any]: Dictionary containing:
            - positions: Numpy array of positions (shape: n_atoms, 3)
            - species: List of species symbols
            - cell: Lattice vectors as numpy array (Crystal only, None for Molecule)
            - pbc: Periodic boundary conditions as numpy array (Crystal only)
            - num_atoms: Number of atoms
            - is_crystal: Boolean indicating if structure is a Crystal
            - cutoff: Cutoff distance used
            - threebody_cutoff: Three-body cutoff distance

    Note:
        This is a legacy function. For new code, use :func:`create_structure_graph`
        or the OOP API directly.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import structure_to_graph_data
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> data = structure_to_graph_data(mol, cutoff=2.0)
        >>> data['num_atoms']
        2
        >>> data['is_crystal']
        False
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
    structure: Union[Crystal, Molecule], use_pbc: Optional[bool] = None
) -> np.ndarray:
    """
    Get distance matrix (functional API).

    This is a convenience function that creates a graph and returns its distance matrix.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        np.ndarray: Distance matrix of shape (N, N) where N is the number of atoms.
                   Entry (i, j) is the distance between atoms i and j in Angstroms.

    Note:
        Uses a large cutoff (20.0 Å) to capture all distances. For very large
        structures, this may be memory-intensive.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_distance_matrix
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> dist = get_distance_matrix(mol)
        >>> dist[0, 1]  # Distance between atoms 0 and 1
        1.2
    """
    graph = create_structure_graph(structure, cutoff=20.0, use_pbc=use_pbc)
    return graph.distance_matrix


def get_edge_list(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
    include_distances: bool = False,
) -> Union[List[Tuple[int, int]], List[Tuple[int, int, float]]]:
    """
    Get edge list (functional API).

    This is a convenience function that creates a graph and returns its edge list.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.
        include_distances: If True, return edges with distances as (i, j, dist).
                          If False, return edges as (i, j) tuples (default).

    Returns:
        Union[List[Tuple[int, int]], List[Tuple[int, int, float]]]:
            - If include_distances=False: List of (source, target) tuples
            - If include_distances=True: List of (source, target, distance) tuples

        Distances are in Angstroms.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_edge_list
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> edges = get_edge_list(mol, cutoff=2.0)
        >>> edges
        [(0, 1)]
        >>>
        >>> edges_with_dist = get_edge_list(mol, cutoff=2.0, include_distances=True)
        >>> edges_with_dist
        [(0, 1, 1.2)]
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    edges = graph.edge_list

    if not include_distances:
        return [(i, j) for i, j, d in edges]
    return edges


def get_coordination_numbers(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> Dict[int, int]:
    """
    Get coordination numbers (functional API).

    This is a convenience function that creates a graph and returns coordination numbers.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        Dict[int, int]: Dictionary mapping atom index to coordination number
                       (number of neighbors within cutoff).

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_coordination_numbers
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> coord = get_coordination_numbers(mol, cutoff=2.0)
        >>> coord
        {0: 1, 1: 1}
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.coordination_numbers


def get_degree_distribution(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> Dict[int, int]:
    """
    Get degree distribution (functional API).

    This is a convenience function that creates a graph and returns its degree distribution.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        Dict[int, int]: Dictionary mapping coordination number (degree) to the count
                       of atoms with that coordination number.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_degree_distribution
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> dist = get_degree_distribution(mol, cutoff=2.0)
        >>> dist
        {1: 2}  # Both atoms have coordination number 1
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.degree_distribution


def is_connected(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> bool:
    """
    Check if graph is connected (functional API).

    This is a convenience function that creates a graph and checks if it's connected.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        bool: True if the graph is connected, False otherwise.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import is_connected
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> is_connected(mol, cutoff=2.0)
        True
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.is_connected


def get_connected_components(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> List[List[int]]:
    """
    Get connected components (functional API).

    This is a convenience function that creates a graph and returns its connected components.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        List[List[int]]: List of connected components. Each component is a list
                        of atom indices belonging to that component.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_connected_components
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> components = get_connected_components(mol, cutoff=2.0)
        >>> components
        [[0, 1]]  # Single connected component
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.connected_components


def get_shortest_path(
    structure: Union[Crystal, Molecule],
    start_idx: int,
    end_idx: int,
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> Optional[List[int]]:
    """
    Get shortest path between two atoms (functional API).

    This is a convenience function that creates a graph and finds the shortest path.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        start_idx: Starting atom index.
        end_idx: Ending atom index.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        Optional[List[int]]: List of atom indices in the shortest path, or None
                            if no path exists.

    Raises:
        IndexError: If start_idx or end_idx is out of range.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_shortest_path
        >>>
        >>> mol = Molecule(['C', 'O', 'H'], [[0,0,0], [1.2,0,0], [2.0,0,0]])
        >>> path = get_shortest_path(mol, 0, 2, cutoff=2.0)
        >>> path
        [0, 1, 2]  # Path through atom 1
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.get_shortest_path(start_idx, end_idx)


def get_graph_diameter(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> Optional[int]:
    """
    Get graph diameter (functional API).

    This is a convenience function that creates a graph and returns its diameter.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        Optional[int]: Graph diameter (longest shortest path), or None if the
                      graph is disconnected. Returns 0 for graphs with 1 or fewer nodes.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_graph_diameter
        >>>
        >>> mol = Molecule(['C', 'O', 'H'], [[0,0,0], [1.2,0,0], [2.0,0,0]])
        >>> diameter = get_graph_diameter(mol, cutoff=2.0)
        >>> diameter
        2  # Longest shortest path has 2 edges
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.diameter


def get_node_features(
    structure: Union[Crystal, Molecule], include_properties: bool = True
) -> np.ndarray:
    """
    Get node features for graph neural networks (functional API).

    This is a convenience function that creates a graph and returns node features.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        include_properties: Currently unused, kept for API compatibility.

    Returns:
        np.ndarray: Feature matrix of shape (N, F) where N is the number of nodes
                   and F is the number of features (currently 1: atomic number).

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_node_features
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> features = get_node_features(mol)
        >>> features.shape
        (2, 1)
        >>> features[0]  # Atomic number of C
        array([6])
    """
    graph = create_structure_graph(structure, cutoff=3.0)
    return graph.node_features


def get_graph_statistics(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Get comprehensive graph statistics (functional API).

    This is a convenience function that creates a graph and returns statistics.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        Dict[str, Any]: Dictionary containing comprehensive graph statistics:
            - num_nodes: Number of nodes
            - num_edges: Number of edges
            - is_connected: Whether graph is connected
            - num_components: Number of connected components
            - diameter: Graph diameter
            - avg_coordination: Average coordination number
            - max_coordination: Maximum coordination number
            - min_coordination: Minimum coordination number
            - degree_distribution: Degree distribution dictionary

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_graph_statistics
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> stats = get_graph_statistics(mol, cutoff=2.0)
        >>> stats['num_nodes']
        2
        >>> stats['avg_coordination']
        1.0
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.statistics


def structure_to_networkx(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
):
    """
    Convert structure to NetworkX graph (functional API).

    This is a convenience function that creates a graph and converts it to NetworkX.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        networkx.Graph: NetworkX Graph object with nodes and edges.

    Raises:
        ImportError: If networkx is not installed.

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import structure_to_networkx
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> G = structure_to_networkx(mol, cutoff=2.0)
        >>> G.number_of_nodes()
        2
        >>> G.number_of_edges()
        1
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.to_networkx()


def get_rings(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    max_ring_size: int = 10,
    use_pbc: Optional[bool] = None,
) -> List[List[int]]:
    """
    Find ring structures in the graph (functional API).

    This is a convenience function that creates a graph and finds rings.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        max_ring_size: Maximum ring size to search for (default: 10).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.

    Returns:
        List[List[int]]: List of rings. Each ring is a list of atom indices
                        forming a cycle in the graph.

    Raises:
        ImportError: If networkx is not installed (required for ring finding).

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_rings
        >>>
        >>> # Create a ring molecule (benzene-like)
        >>> mol = Molecule(['C'] * 6, [[0,0,0], [1.4,0,0], [2.1,1.2,0],
        ...                 [1.4,2.4,0], [0,2.4,0], [-0.7,1.2,0]])
        >>> rings = get_rings(mol, cutoff=1.5, max_ring_size=6)
        >>> len(rings)
        1
    """
    graph = create_structure_graph(structure, cutoff, use_pbc)
    return graph.find_rings(max_ring_size)


def get_graph_laplacian(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: Optional[bool] = None,
    normalized: bool = False,
) -> np.ndarray:
    """
    Get graph Laplacian matrix (functional API).

    This is a convenience function that creates a graph and returns its Laplacian.
    For better performance with multiple operations, consider using the OOP API
    (:class:`MoleculeGraph` or :class:`CrystalGraph`) directly.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges (default: 3.0).
        use_pbc: Use periodic boundary conditions (only for Crystal).
                If None, defaults to True for Crystal. Ignored for Molecule.
        normalized: If True, return normalized Laplacian; if False, return standard
                   Laplacian (default: False).

    Returns:
        np.ndarray: Laplacian matrix of shape (N, N) where N is the number of nodes.
                   - If normalized=False: L = D - A (standard Laplacian)
                   - If normalized=True: L = I - D^(-1/2) A D^(-1/2) (normalized)

    Example:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.core.graph import get_graph_laplacian
        >>>
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> L = get_graph_laplacian(mol, cutoff=2.0)
        >>> L.shape
        (2, 2)
        >>>
        >>> L_norm = get_graph_laplacian(mol, cutoff=2.0, normalized=True)
    """
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
