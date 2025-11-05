"""
Lattice transformation and standardization operations.
"""

from typing import List, Union
import numpy as np
from ...core import Crystal, Lattice


def rotate_lattice(
    crystal: Crystal,
    rotation_matrix: Union[List[List[float]], np.ndarray],
    rotate_atoms: bool = True,
    inplace: bool = False
) -> Crystal:
    """
    Rotate lattice (and optionally atoms).
    
    Args:
        crystal: Crystal structure
        rotation_matrix: 3x3 rotation matrix
        rotate_atoms: If True, also rotate atomic positions
        inplace: If True, modify crystal in-place
    
    Returns:
        Rotated crystal structure
        
    Examples:
        >>> from matsimpy.transformation.lattice import rotate_lattice
        >>> import numpy as np
        >>> # 45 degree rotation around z-axis
        >>> angle = np.pi / 4
        >>> R = [[np.cos(angle), -np.sin(angle), 0],
        ...      [np.sin(angle), np.cos(angle), 0],
        ...      [0, 0, 1]]
        >>> rotated = rotate_lattice(crystal, R)
    """
    from ..base import _copy_structure
    
    if not inplace:
        crystal = _copy_structure(crystal)
    
    rotation_matrix = np.array(rotation_matrix, dtype=np.float64)
    
    # Rotate lattice vectors
    new_lattice_vectors = np.dot(rotation_matrix, crystal.lattice.lattice_vectors)
    crystal.lattice = Lattice(new_lattice_vectors)
    
    if rotate_atoms:
        # Rotate Cartesian positions
        new_cart_positions = np.dot(crystal.cart_positions, rotation_matrix.T)
        crystal.cart_positions = new_cart_positions
        # Update fractional positions
        crystal.positions = np.dot(new_cart_positions, np.linalg.inv(new_lattice_vectors))
        crystal.frac_positions = crystal.positions
    else:
        # Keep fractional positions, update Cartesian
        crystal.cart_positions = crystal._convert_to_cartesian()
    
    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None
    crystal._sites = crystal._initialize_sites()
    
    return crystal


def transform_lattice(
    crystal: Crystal,
    transformation_matrix: Union[List[List[float]], np.ndarray],
    transform_positions: bool = False,
    inplace: bool = False
) -> Crystal:
    """
    Apply general linear transformation to lattice.
    
    Args:
        crystal: Crystal structure
        transformation_matrix: 3x3 transformation matrix
        transform_positions: If True, transform atomic positions by same matrix
        inplace: If True, modify crystal in-place
    
    Returns:
        Transformed crystal structure
        
    Examples:
        >>> from matsimpy.transformation.lattice import transform_lattice
        >>> # Convert to primitive cell (for FCC to simple cubic, etc.)
        >>> T = [[0.5, 0.5, 0], [0, 0.5, 0.5], [0.5, 0, 0.5]]
        >>> primitive = transform_lattice(crystal, T)
    """
    from .strain import apply_deformation
    return apply_deformation(crystal, transformation_matrix, transform_positions, inplace)


def get_niggli_reduced(
    crystal: Crystal,
    inplace: bool = False
) -> Crystal:
    """
    Get Niggli-reduced cell.
    
    Args:
        crystal: Crystal structure
        inplace: If True, modify crystal in-place
    
    Returns:
        Niggli-reduced crystal structure
        
    Examples:
        >>> from matsimpy.transformation.lattice import get_niggli_reduced
        >>> reduced = get_niggli_reduced(crystal)
    
    Note:
        Requires spglib for full implementation.
    """
    from ..base import _copy_structure
    
    if not inplace:
        crystal = _copy_structure(crystal)
    
    # Placeholder - full implementation would use spglib
    return crystal


def standardize_cell(
    crystal: Crystal,
    to_primitive: bool = False,
    inplace: bool = False
) -> Crystal:
    """
    Standardize crystal cell using spglib conventions.
    
    Args:
        crystal: Crystal structure
        to_primitive: If True, convert to primitive cell
        inplace: If True, modify crystal in-place
    
    Returns:
        Standardized crystal structure
        
    Examples:
        >>> from matsimpy.transformation.lattice import standardize_cell
        >>> standardized = standardize_cell(crystal)
        >>> primitive = standardize_cell(crystal, to_primitive=True)
    """
    from ..base import _copy_structure
    
    if not inplace:
        crystal = _copy_structure(crystal)
    
    # Placeholder - full implementation would use spglib
    try:
        import spglib
        
        cell = (
            crystal.lattice.lattice_vectors,
            crystal.positions,
            [crystal.species.index(s) + 1 for s in crystal.species]
        )
        
        if to_primitive:
            prim_cell = spglib.find_primitive(cell)
            if prim_cell is not None:
                lattice, positions, numbers = prim_cell
                species = [crystal.species[n - 1] for n in numbers]
                crystal.lattice = Lattice(lattice)
                crystal.positions = positions
                crystal.species = tuple(species)
        else:
            std_cell = spglib.standardize_cell(cell)
            if std_cell is not None:
                lattice, positions, numbers = std_cell
                species = [crystal.species[n - 1] for n in numbers]
                crystal.lattice = Lattice(lattice)
                crystal.positions = positions
                crystal.species = tuple(species)
        
        # Update derived properties
        crystal.frac_positions = crystal.positions
        crystal.cart_positions = crystal._convert_to_cartesian()
        crystal._neighbor_tree = None
        crystal._neighbor_tree_positions = None
        crystal._sites = crystal._initialize_sites()
        
    except ImportError:
        import warnings
        warnings.warn("spglib not available, returning unchanged crystal")
    
    return crystal


__all__ = ['rotate_lattice', 'transform_lattice', 'get_niggli_reduced', 'standardize_cell']

