"""
Graph conversion utilities for Crystal and Molecule structures.

Provides functions to convert MatSimPy structures to graph representations
compatible with ML frameworks like MatterSim, without external dependencies.
"""

import numpy as np
from typing import Optional, Union, Dict, Any
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
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.core.graph import structure_to_graph_data
        >>> 
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> graph_data = structure_to_graph_data(crystal)
        >>> print(graph_data['positions'].shape)  # (1, 3)
        >>> print(graph_data['species'])  # ['Si']
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


__all__ = ['structure_to_graph_data']

