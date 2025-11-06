"""
Supercell generation tools.

Create supercells from unit cells by repeating the unit cell.
"""

from typing import List, Union
import numpy as np
from ...core import Crystal, Lattice
from ..base import _validate_structure


def make_supercell(crystal: Crystal,
                   scaling_matrix: Union[List[int], List[List[int]], np.ndarray],
                   inplace: bool = False) -> Crystal:
    """
    Create supercell from unit cell.
    
    This function replicates the unit cell according to the scaling matrix.
    The scaling_matrix can be:
    - Simple: [a, b, c] - repeats a times in a, b times in b, c times in c
    - Matrix: [[a1, a2, a3], [b1, b2, b3], [c1, c2, c3]] - general transformation
    
    Args:
        crystal: Unit cell to expand
        scaling_matrix: Scaling matrix for supercell generation
        inplace: If True, modify crystal in-place (default: False)
                Note: Supercell creation always creates new atoms, so this
                option mainly affects whether the original lattice is modified.
    
    Returns:
        Supercell Crystal structure
        
    Raises:
        TypeError: If crystal is not a Crystal object
        ValueError: If scaling_matrix is invalid
        
    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.transformation import make_supercell
        >>> from matsimpy.builders.bulk import from_prototype
        >>> unit_cell = from_prototype('diamond', 'Si', 5.0)  # Proper diamond structure
        >>> # Simple 2x2x2 supercell
        >>> supercell = make_supercell(unit_cell, [2, 2, 2])
        >>> # General transformation
        >>> supercell = make_supercell(unit_cell, [[2,0,0], [0,2,0], [0,0,2]])
    """
    if not isinstance(crystal, Crystal):
        raise TypeError("make_supercell requires a Crystal object")
    
    scaling_matrix = np.array(scaling_matrix, dtype=np.int32)
    
    # Handle simple [a, b, c] format
    if scaling_matrix.ndim == 1:
        if len(scaling_matrix) != 3:
            raise ValueError("Scaling matrix must have 3 elements for [a, b, c] format")
        scaling_matrix = np.diag(scaling_matrix)
    
    # Validate matrix format
    if scaling_matrix.shape != (3, 3):
        raise ValueError("Scaling matrix must be 3x3 or [a, b, c] format")
    
    # Calculate new lattice vectors
    new_lattice_vectors = np.dot(scaling_matrix, crystal.lattice.lattice_vectors)
    new_lattice = Lattice(new_lattice_vectors)
    
    # Generate all atoms in supercell
    new_species = []
    new_positions = []
    new_site_properties = [] if crystal.site_properties else None
    
    # Iterate over all unit cell replications
    for i in range(scaling_matrix[0, 0] * scaling_matrix[1, 1] * scaling_matrix[2, 2]):
        # Calculate replication indices
        # This is a simplified approach - for general matrices, need more complex logic
        # For now, handle simple diagonal case
        if np.allclose(scaling_matrix, np.diag(np.diag(scaling_matrix))):
            # Simple diagonal case
            diag = np.diag(scaling_matrix)
            na, nb, nc = diag
            
            # Calculate i, j, k from linear index
            k = i // (na * nb)
            j = (i // na) % nb
            ii = i % na
            
            # Add offset to fractional positions
            offset = np.array([ii, j, k], dtype=np.float64)
            
            for atom_idx, (spec, pos) in enumerate(zip(crystal.species, crystal.positions)):
                new_pos = pos + offset
                # Wrap to [0, 1) for fractional coordinates
                new_pos = new_pos % 1.0
                new_species.append(spec)
                new_positions.append(new_pos.tolist())
                
                if new_site_properties is not None and crystal.site_properties:
                    new_site_properties.append(crystal.site_properties[atom_idx].copy())
        else:
            # General matrix case - more complex
            # For now, raise NotImplementedError for non-diagonal matrices
            raise NotImplementedError(
                "General (non-diagonal) scaling matrices not yet implemented. "
                "Use simple [a, b, c] format or diagonal matrix."
            )
    
    # Create new crystal
    if inplace:
        # Update crystal in-place (replace all data)
        crystal.species = tuple(new_species)
        crystal.positions = np.array(new_positions, dtype=np.float64)
        crystal.frac_positions = crystal.positions
        crystal.cart_positions = crystal._convert_to_cartesian()
        crystal.lattice = new_lattice
        if new_site_properties is not None:
            crystal.site_properties = new_site_properties
        crystal._neighbor_tree = None
        crystal._neighbor_tree_positions = None
        crystal._sites = crystal._initialize_sites()
        crystal._formula_dirty = True
        crystal._cached_composition = None
        return crystal
    else:
        # Create new crystal
        return Crystal(
            new_species,
            new_positions,
            new_lattice,
            site_properties=new_site_properties,
            coords_are_cartesian=False
        )


__all__ = ['make_supercell']
