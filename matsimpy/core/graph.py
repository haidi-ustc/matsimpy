"""
Graph conversion utilities for Crystal and Molecule structures.

Provides functions to convert MatSimPy structures to graph representations
compatible with ML frameworks like MatterSim.
"""

import numpy as np
from typing import Optional, Union, Dict, Any, Tuple
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
    from Crystal or Molecule objects for use with ML frameworks.
    
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


def structure_to_ase_atoms(
    structure: Union[Crystal, Molecule],
    require_ase: bool = True
) -> Any:
    """
    Convert MatSimPy structure to ASE Atoms object.
    
    This function extracts structure data and creates an ASE Atoms object.
    ASE is only imported when needed (optional dependency).
    
    Args:
        structure: Crystal or Molecule object
        require_ase: If True, raises ImportError if ASE not available.
                    If False, returns None when ASE unavailable.
        
    Returns:
        ase.Atoms: ASE Atoms object, or None if ASE unavailable and require_ase=False
        
    Raises:
        ImportError: If ASE not available and require_ase=True
        
    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.core.graph import structure_to_ase_atoms
        >>> 
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> atoms = structure_to_ase_atoms(crystal)
    """
    # Get graph data
    graph_data = structure_to_graph_data(structure)
    
    # Import ASE conditionally
    try:
        from ase import Atoms
    except ImportError:
        if require_ase:
            raise ImportError(
                "ASE is required for this operation. Install with: pip install ase"
            )
        return None
    
    # Create ASE Atoms object
    if graph_data['is_crystal']:
        atoms = Atoms(
            symbols=graph_data['species'],
            positions=graph_data['positions'],
            cell=graph_data['cell'],
            pbc=graph_data['pbc']
        )
    else:
        atoms = Atoms(
            symbols=graph_data['species'],
            positions=graph_data['positions']
        )
    
    return atoms


__all__ = ['structure_to_graph_data', 'structure_to_ase_atoms']

