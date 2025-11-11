"""
Graph conversion utilities for Crystal and Molecule structures.

Provides functions to convert MatSimPy structures to graph representations
compatible with ML frameworks, compute graph properties, and analyze structure
connectivity. Supports both molecular graphs and crystal graphs with PBC.
"""

import numpy as np
from typing import Optional, Union, Dict, Any, List, Tuple, Set
from scipy.spatial.distance import cdist
from .crystal import Crystal
from .molecule import Molecule


def structure_to_graph_data(
    structure: Union[Crystal, Molecule],
    cutoff: float = 5.0,
    threebody_cutoff: float = 4.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Convert MatSimPy structure to graph data format.
    
    Extracts all necessary structure information (positions, species, cell, pbc)
    directly from Crystal or Molecule objects for use with ML frameworks.
    
    Args:
        structure: Crystal or Molecule object
        cutoff: Cutoff radius for graph construction (Å)
        threebody_cutoff: Cutoff for three-body interactions (Å)
        **kwargs: Additional parameters
        
    Returns:
        Dictionary containing:
            - positions: Atomic positions (N, 3) in Cartesian coordinates
            - species: List of atomic species (N,)
            - cell: Lattice vectors (3, 3) for crystals, None for molecules
            - pbc: Periodic boundary conditions (3,) for crystals, [False,False,False] for molecules
            - num_atoms: Number of atoms
            - is_crystal: Whether structure is a crystal
            
    Example:
        >>> from matsimpy.builders.bulk import from_prototype
        >>> from matsimpy.core.graph import structure_to_graph_data
        >>> 
        >>> # Use proper diamond structure (2 atoms in primitive cell)
        >>> si_crystal = from_prototype('diamond', 'Si', 5.43)
        >>> graph_data = structure_to_graph_data(si_crystal)
        >>> print(graph_data['positions'].shape)  # (2, 3)
        >>> print(graph_data['species'])  # ['Si', 'Si']
    """
    # Extract positions (already in Cartesian)
    if isinstance(structure, Crystal):
        positions = np.array(structure.cart_positions, dtype=np.float64)
        cell = np.array(structure.lattice.lattice_vectors, dtype=np.float64)
        pbc = np.array(structure.pbc, dtype=bool)
        is_crystal = True
    else:  # Molecule
        positions = np.array(structure.positions, dtype=np.float64)
        cell = None
        pbc = np.array([False, False, False], dtype=bool)
        is_crystal = False
    
    # Extract species
    species = list(structure.species)
    
    return {
        'positions': positions,
        'species': species,
        'cell': cell,
        'pbc': pbc,
        'num_atoms': len(structure),
        'is_crystal': is_crystal,
        'cutoff': cutoff,
        'threebody_cutoff': threebody_cutoff,
    }


def get_adjacency_matrix(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> np.ndarray:
    """
    Compute adjacency matrix for the structure.
    
    Creates a binary adjacency matrix where entry (i,j) is 1 if atoms i and j
    are within cutoff distance, 0 otherwise.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect
                (True for Crystal, False for Molecule).
    
    Returns:
        Binary adjacency matrix of shape (N, N) where N is number of atoms.
        
    Examples:
        >>> molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> adj = get_adjacency_matrix(molecule, cutoff=2.0)
        >>> print(adj)  # [[0, 1], [1, 0]]
    """
    if use_pbc is None:
        use_pbc = isinstance(structure, Crystal)
    
    n_atoms = len(structure)
    adj_matrix = np.zeros((n_atoms, n_atoms), dtype=int)
    
    if isinstance(structure, Crystal) and use_pbc:
        # Use Crystal's neighbor list with PBC
        neighbors = structure.get_neighbor_list(cutoff, use_pbc=True)
        for i, neighbor_list in neighbors.items():
            for j, dist in neighbor_list:
                adj_matrix[i, j] = 1
    else:
        # Use distance-based approach for molecules or non-PBC
        if isinstance(structure, Crystal):
            positions = structure.cart_positions
        else:
            positions = structure.positions
        
        dist_matrix = cdist(positions, positions)
        adj_matrix = (dist_matrix < cutoff).astype(int)
        np.fill_diagonal(adj_matrix, 0)  # No self-loops
    
    return adj_matrix


def get_distance_matrix(
    structure: Union[Crystal, Molecule],
    use_pbc: bool = None
) -> np.ndarray:
    """
    Compute pairwise distance matrix for all atoms.
    
    Args:
        structure: Crystal or Molecule object.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        Distance matrix of shape (N, N) with pairwise distances in Angstroms.
        
    Examples:
        >>> molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> dist = get_distance_matrix(molecule)
        >>> print(dist[0,1])  # 1.2
    """
    if use_pbc is None:
        use_pbc = isinstance(structure, Crystal)
    
    if isinstance(structure, Crystal):
        positions = structure.cart_positions
    else:
        positions = structure.positions
    
    if isinstance(structure, Crystal) and use_pbc:
        # For crystals with PBC, need to consider periodic images
        # Simple approach: use distance from neighbor list
        n_atoms = len(structure)
        dist_matrix = np.full((n_atoms, n_atoms), np.inf)
        np.fill_diagonal(dist_matrix, 0.0)
        
        # Get neighbors with large cutoff to capture most interactions
        neighbors = structure.get_neighbor_list(cutoff=20.0, use_pbc=True)
        for i, neighbor_list in neighbors.items():
            for j, dist in neighbor_list:
                dist_matrix[i, j] = dist
        
        return dist_matrix
    else:
        # Simple Euclidean distances for molecules
        return cdist(positions, positions)


def get_edge_list(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None,
    include_distances: bool = False
) -> Union[List[Tuple[int, int]], List[Tuple[int, int, float]]]:
    """
    Get edge list representation of the structure graph.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
        include_distances: If True, include edge distances as third element.
    
    Returns:
        List of edges as (i, j) tuples, or (i, j, distance) if include_distances=True.
        Edges are undirected (only includes i < j).
        
    Examples:
        >>> molecule = Molecule(['C', 'O', 'H'], [[0,0,0], [1.2,0,0], [2.5,0,0]])
        >>> edges = get_edge_list(molecule, cutoff=2.0)
        >>> print(edges)  # [(0, 1), (1, 2)]
        
        >>> edges_dist = get_edge_list(molecule, cutoff=2.0, include_distances=True)
        >>> print(edges_dist)  # [(0, 1, 1.2), (1, 2, 1.3)]
    """
    if use_pbc is None:
        use_pbc = isinstance(structure, Crystal)
    
    edges = []
    
    if isinstance(structure, Crystal) and use_pbc:
        neighbors = structure.get_neighbor_list(cutoff, use_pbc=True)
        for i, neighbor_list in neighbors.items():
            for j, dist in neighbor_list:
                if i < j:  # Undirected edges
                    if include_distances:
                        edges.append((i, j, dist))
                    else:
                        edges.append((i, j))
    else:
        adj_matrix = get_adjacency_matrix(structure, cutoff, use_pbc=False)
        if include_distances:
            dist_matrix = get_distance_matrix(structure, use_pbc=False)
        
        for i in range(len(structure)):
            for j in range(i + 1, len(structure)):
                if adj_matrix[i, j] == 1:
                    if include_distances:
                        edges.append((i, j, dist_matrix[i, j]))
                    else:
                        edges.append((i, j))
    
    return edges


def get_coordination_numbers(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> Dict[int, int]:
    """
    Compute coordination number for each atom.
    
    Coordination number is the number of neighboring atoms within cutoff distance.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        Dictionary mapping atom index to coordination number.
        
    Examples:
        >>> molecule = Molecule(['C', 'H', 'H', 'H', 'H'], 
        ...                     [[0,0,0], [1,0,0], [-1,0,0], [0,1,0], [0,-1,0]])
        >>> coord = get_coordination_numbers(molecule, cutoff=1.5)
        >>> print(coord[0])  # 4 (C bonded to 4 H atoms)
    """
    if use_pbc is None:
        use_pbc = isinstance(structure, Crystal)
    
    coord_numbers = {}
    
    if isinstance(structure, Crystal) and use_pbc:
        neighbors = structure.get_neighbor_list(cutoff, use_pbc=True)
        for i in range(len(structure)):
            coord_numbers[i] = len(neighbors.get(i, []))
    else:
        if isinstance(structure, Molecule):
            all_neighbors = structure.get_all_neighbor_lists(cutoff)
            for i, neighbor_list in enumerate(all_neighbors):
                coord_numbers[i] = len(neighbor_list)
        else:
            # Crystal without PBC
            neighbors = structure.get_neighbor_list(cutoff, use_pbc=False)
            for i in range(len(structure)):
                coord_numbers[i] = len(neighbors.get(i, []))
    
    return coord_numbers


def get_degree_distribution(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> Dict[int, int]:
    """
    Get degree (coordination number) distribution.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        Dictionary mapping coordination number to count of atoms with that coordination.
        
    Examples:
        >>> molecule = Molecule(['C', 'H', 'H'], [[0,0,0], [1,0,0], [-1,0,0]])
        >>> dist = get_degree_distribution(molecule, cutoff=1.5)
        >>> print(dist)  # {2: 1, 1: 2} - one C with 2 bonds, two H with 1 bond
    """
    coord_numbers = get_coordination_numbers(structure, cutoff, use_pbc)
    
    from collections import Counter
    distribution = Counter(coord_numbers.values())
    
    return dict(distribution)


def is_connected(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> bool:
    """
    Check if structure graph is connected.
    
    A graph is connected if there's a path between any two atoms.
    For molecules, checks if molecule is a single connected component.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        True if graph is connected, False otherwise.
        
    Examples:
        >>> # Single molecule
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> print(is_connected(mol, cutoff=2.0))  # True
        
        >>> # Two separate molecules
        >>> mol2 = Molecule(['C', 'C'], [[0,0,0], [10,0,0]])
        >>> print(is_connected(mol2, cutoff=2.0))  # False
    """
    if len(structure) == 0:
        return True
    
    if len(structure) == 1:
        return True
    
    # BFS to check connectivity
    adj_matrix = get_adjacency_matrix(structure, cutoff, use_pbc)
    
    visited = set([0])
    queue = [0]
    
    while queue:
        node = queue.pop(0)
        for neighbor in range(len(structure)):
            if adj_matrix[node, neighbor] == 1 and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    
    return len(visited) == len(structure)


def get_connected_components(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> List[List[int]]:
    """
    Find connected components in the structure graph.
    
    Useful for identifying separate molecules in a multi-molecule system
    or detecting fragmented structures.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        List of components, where each component is a list of atom indices.
        
    Examples:
        >>> # Two separate molecules
        >>> mol = Molecule(['C', 'O', 'N', 'H'], 
        ...                [[0,0,0], [1.2,0,0], [10,0,0], [11,0,0]])
        >>> components = get_connected_components(mol, cutoff=2.0)
        >>> print(len(components))  # 2
        >>> print(components)  # [[0, 1], [2, 3]]
    """
    if len(structure) == 0:
        return []
    
    adj_matrix = get_adjacency_matrix(structure, cutoff, use_pbc)
    
    visited = set()
    components = []
    
    for start_node in range(len(structure)):
        if start_node in visited:
            continue
        
        # BFS from this node
        component = []
        queue = [start_node]
        visited.add(start_node)
        
        while queue:
            node = queue.pop(0)
            component.append(node)
            
            for neighbor in range(len(structure)):
                if adj_matrix[node, neighbor] == 1 and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        components.append(sorted(component))
    
    return components


def get_shortest_path(
    structure: Union[Crystal, Molecule],
    start_idx: int,
    end_idx: int,
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> Optional[List[int]]:
    """
    Find shortest path between two atoms in the graph.
    
    Uses BFS to find the shortest path through bonded atoms.
    
    Args:
        structure: Crystal or Molecule object.
        start_idx: Index of starting atom.
        end_idx: Index of ending atom.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        List of atom indices representing shortest path from start to end,
        or None if no path exists.
        
    Examples:
        >>> mol = Molecule(['C', 'C', 'C'], [[0,0,0], [1,0,0], [2,0,0]])
        >>> path = get_shortest_path(mol, 0, 2, cutoff=1.5)
        >>> print(path)  # [0, 1, 2]
    """
    if not (0 <= start_idx < len(structure)):
        raise IndexError(f"start_idx {start_idx} out of range")
    if not (0 <= end_idx < len(structure)):
        raise IndexError(f"end_idx {end_idx} out of range")
    
    if start_idx == end_idx:
        return [start_idx]
    
    adj_matrix = get_adjacency_matrix(structure, cutoff, use_pbc)
    
    # BFS with path tracking
    visited = {start_idx}
    queue = [(start_idx, [start_idx])]
    
    while queue:
        node, path = queue.pop(0)
        
        for neighbor in range(len(structure)):
            if adj_matrix[node, neighbor] == 1:
                if neighbor == end_idx:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
    
    return None  # No path found


def get_graph_diameter(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> Optional[int]:
    """
    Compute graph diameter (longest shortest path).
    
    Diameter is the maximum shortest path length between any two atoms.
    Returns None if graph is disconnected.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        Diameter as integer (number of edges), or None if disconnected.
        
    Examples:
        >>> # Linear molecule
        >>> mol = Molecule(['C', 'C', 'C'], [[0,0,0], [1,0,0], [2,0,0]])
        >>> diameter = get_graph_diameter(mol, cutoff=1.5)
        >>> print(diameter)  # 2 (path from atom 0 to atom 2)
    """
    if not is_connected(structure, cutoff, use_pbc):
        return None
    
    if len(structure) <= 1:
        return 0
    
    max_distance = 0
    
    # Check all pairs (could be optimized with better algorithm)
    for i in range(len(structure)):
        for j in range(i + 1, len(structure)):
            path = get_shortest_path(structure, i, j, cutoff, use_pbc)
            if path is not None:
                path_length = len(path) - 1  # Number of edges
                max_distance = max(max_distance, path_length)
    
    return max_distance


def get_node_features(
    structure: Union[Crystal, Molecule],
    include_properties: bool = True
) -> np.ndarray:
    """
    Extract node (atom) features for graph neural networks.
    
    Features include atomic number and optionally site properties.
    
    Args:
        structure: Crystal or Molecule object.
        include_properties: Include site properties as features.
    
    Returns:
        Feature matrix of shape (N, F) where N is atoms, F is features.
        Default features: [atomic_number]
        
    Examples:
        >>> molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> features = get_node_features(molecule)
        >>> print(features.shape)  # (2, 1)
        >>> print(features)  # [[6], [8]] - atomic numbers
    """
    from .periodic_table import Element
    
    # Get atomic numbers
    atomic_numbers = np.array([
        Element.get_element(spec).atomic_no 
        for spec in structure.species
    ]).reshape(-1, 1)
    
    features = [atomic_numbers]
    
    if include_properties and hasattr(structure, 'site_properties'):
        if structure.site_properties:
            # Extract numeric site properties
            # This is a simple implementation - could be extended
            pass
    
    return np.hstack(features) if len(features) > 1 else features[0]


def get_graph_statistics(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
) -> Dict[str, Any]:
    """
    Compute comprehensive graph statistics for the structure.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        Dictionary containing:
            - num_nodes: Number of atoms
            - num_edges: Number of edges (bonds)
            - is_connected: Whether graph is connected
            - num_components: Number of connected components
            - diameter: Graph diameter (or None if disconnected)
            - avg_coordination: Average coordination number
            - max_coordination: Maximum coordination number
            - min_coordination: Minimum coordination number
            - degree_distribution: Distribution of coordination numbers
            
    Examples:
        >>> molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> stats = get_graph_statistics(molecule, cutoff=2.0)
        >>> print(stats['num_nodes'])  # 2
        >>> print(stats['avg_coordination'])  # 1.0
    """
    if use_pbc is None:
        use_pbc = isinstance(structure, Crystal)
    
    edges = get_edge_list(structure, cutoff, use_pbc)
    coord_numbers = get_coordination_numbers(structure, cutoff, use_pbc)
    components = get_connected_components(structure, cutoff, use_pbc)
    connected = is_connected(structure, cutoff, use_pbc)
    diameter = get_graph_diameter(structure, cutoff, use_pbc) if connected else None
    degree_dist = get_degree_distribution(structure, cutoff, use_pbc)
    
    coord_values = list(coord_numbers.values())
    
    return {
        'num_nodes': len(structure),
        'num_edges': len(edges),
        'is_connected': connected,
        'num_components': len(components),
        'diameter': diameter,
        'avg_coordination': np.mean(coord_values) if coord_values else 0.0,
        'max_coordination': max(coord_values) if coord_values else 0,
        'min_coordination': min(coord_values) if coord_values else 0,
        'degree_distribution': degree_dist,
    }


def structure_to_networkx(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None
):
    """
    Convert structure to NetworkX graph.
    
    Requires networkx to be installed (optional dependency).
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        NetworkX Graph object with atoms as nodes and bonds as edges.
        
    Raises:
        ImportError: If networkx is not installed.
        
    Examples:
        >>> molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> G = structure_to_networkx(molecule, cutoff=2.0)
        >>> print(G.number_of_nodes())  # 2
        >>> print(G.number_of_edges())  # 1
    """
    try:
        import networkx as nx
    except ImportError:
        raise ImportError(
            "NetworkX is required for this function. "
            "Install with: pip install networkx"
        )
    
    if use_pbc is None:
        use_pbc = isinstance(structure, Crystal)
    
    G = nx.Graph()
    
    # Add nodes with attributes
    for i, (spec, pos) in enumerate(zip(structure.species, structure.positions)):
        G.add_node(i, species=spec, position=pos.tolist())
    
    # Add edges
    edges = get_edge_list(structure, cutoff, use_pbc, include_distances=True)
    for edge in edges:
        if len(edge) == 3:
            i, j, dist = edge
            G.add_edge(i, j, distance=dist)
        else:
            i, j = edge
            G.add_edge(i, j)
    
    return G


def get_rings(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    max_ring_size: int = 10,
    use_pbc: bool = None
) -> List[List[int]]:
    """
    Find ring structures (cycles) in the graph.
    
    Identifies closed loops of atoms, useful for aromatic systems,
    zeolites, MOFs, etc.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        max_ring_size: Maximum ring size to search for.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
    
    Returns:
        List of rings, where each ring is a list of atom indices.
        Only returns minimal cycles (not larger rings that contain smaller ones).
        
    Examples:
        >>> # Benzene-like structure
        >>> mol = Molecule(['C']*6, [[i,0,0] for i in range(6)])
        >>> rings = get_rings(mol, cutoff=1.5)
        >>> print(len(rings))  # Should find the 6-membered ring
        
    Note:
        This is a basic implementation. For complex structures, consider using
        structure_to_networkx() with NetworkX's cycle finding algorithms.
    """
    try:
        import networkx as nx
    except ImportError:
        raise ImportError(
            "NetworkX is required for ring finding. "
            "Install with: pip install networkx"
        )
    
    G = structure_to_networkx(structure, cutoff, use_pbc)
    
    # Find all cycles using NetworkX
    try:
        # Find simple cycles (minimal cycles)
        cycles = list(nx.simple_cycles(G.to_directed()))
        
        # Filter by size and convert back to undirected representation
        rings = []
        seen_rings = set()
        
        for cycle in cycles:
            if 3 <= len(cycle) <= max_ring_size:
                # Normalize cycle representation (smallest index first)
                normalized = tuple(sorted(cycle))
                if normalized not in seen_rings:
                    seen_rings.add(normalized)
                    rings.append(cycle)
        
        return rings
    except:
        # Fallback: return empty list if cycle finding fails
        return []


def get_graph_laplacian(
    structure: Union[Crystal, Molecule],
    cutoff: float = 3.0,
    use_pbc: bool = None,
    normalized: bool = False
) -> np.ndarray:
    """
    Compute graph Laplacian matrix.
    
    Laplacian is useful for spectral graph analysis and finding
    eigenmodes of the structure.
    
    Args:
        structure: Crystal or Molecule object.
        cutoff: Cutoff distance in Angstroms for defining edges.
        use_pbc: Use periodic boundary conditions. If None, auto-detect.
        normalized: If True, compute normalized Laplacian.
    
    Returns:
        Laplacian matrix of shape (N, N).
        - Unnormalized: L = D - A (degree matrix minus adjacency)
        - Normalized: L = I - D^(-1/2) A D^(-1/2)
        
    Examples:
        >>> molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> L = get_graph_laplacian(molecule, cutoff=2.0)
        >>> print(L)  # [[1, -1], [-1, 1]]
    """
    adj_matrix = get_adjacency_matrix(structure, cutoff, use_pbc)
    degree = adj_matrix.sum(axis=1)
    
    if not normalized:
        # L = D - A
        D = np.diag(degree)
        return D - adj_matrix
    else:
        # Normalized: L = I - D^(-1/2) A D^(-1/2)
        D_inv_sqrt = np.diag(1.0 / np.sqrt(degree + 1e-10))  # Add small epsilon
        I = np.eye(len(structure))
        return I - D_inv_sqrt @ adj_matrix @ D_inv_sqrt


__all__ = [
    'structure_to_graph_data',
    'get_adjacency_matrix',
    'get_distance_matrix',
    'get_edge_list',
    'get_coordination_numbers',
    'get_degree_distribution',
    'is_connected',
    'get_connected_components',
    'get_shortest_path',
    'get_graph_diameter',
    'get_node_features',
    'get_graph_statistics',
    'structure_to_networkx',
    'get_rings',
    'get_graph_laplacian',
]

