"""
Strain and deformation operations for crystal lattices.
"""

from typing import List, Union
import numpy as np
from ...core import Crystal, Lattice


def apply_strain(
    crystal: Crystal,
    strain_matrix: Union[List[List[float]], np.ndarray],
    inplace: bool = False
) -> Crystal:
    """
    Apply strain to crystal structure.
    
    Args:
        crystal: Crystal structure to strain
        strain_matrix: 3x3 strain tensor
        inplace: If True, modify crystal in-place
    
    Returns:
        Strained crystal structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.transformation.lattice import apply_strain
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> # Apply 1% tensile strain in x direction
        >>> strain = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
        >>> strained = apply_strain(crystal, strain)
    """
    from ..base import _copy_structure
    
    if not inplace:
        crystal = _copy_structure(crystal)
    
    strain_matrix = np.array(strain_matrix, dtype=np.float64)
    
    # Apply strain: new_lattice = (I + strain) * old_lattice
    deformation = np.eye(3) + strain_matrix
    new_lattice_vectors = np.dot(deformation, crystal.lattice.lattice_vectors)
    
    crystal.lattice = Lattice(new_lattice_vectors)
    
    # Update Cartesian positions (fractional positions stay the same in strain)
    crystal.cart_positions = crystal._convert_to_cartesian()
    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None
    
    return crystal


def apply_deformation(
    crystal: Crystal,
    deformation_matrix: Union[List[List[float]], np.ndarray],
    deform_positions: bool = True,
    inplace: bool = False
) -> Crystal:
    """
    Apply general deformation to crystal structure.
    
    Args:
        crystal: Crystal structure to deform
        deformation_matrix: 3x3 deformation gradient tensor
        deform_positions: If True, also deform atomic positions
        inplace: If True, modify crystal in-place
    
    Returns:
        Deformed crystal structure
        
    Examples:
        >>> from matsimpy.transformation.lattice import apply_deformation
        >>> import numpy as np
        >>> # Apply shear deformation
        >>> shear = [[1, 0.1, 0], [0, 1, 0], [0, 0, 1]]
        >>> deformed = apply_deformation(crystal, shear)
    """
    from ..base import _copy_structure
    
    if not inplace:
        crystal = _copy_structure(crystal)
    
    deformation_matrix = np.array(deformation_matrix, dtype=np.float64)
    
    # Apply deformation to lattice
    new_lattice_vectors = np.dot(deformation_matrix, crystal.lattice.lattice_vectors)
    crystal.lattice = Lattice(new_lattice_vectors)
    
    if deform_positions:
        # Also deform atomic positions (Cartesian)
        new_cart_positions = np.dot(crystal.cart_positions, deformation_matrix.T)
        # Convert back to fractional
        crystal.positions = np.dot(new_cart_positions, np.linalg.inv(new_lattice_vectors))
        crystal.frac_positions = crystal.positions
        crystal.cart_positions = new_cart_positions
    else:
        # Keep fractional positions, update Cartesian
        crystal.cart_positions = crystal._convert_to_cartesian()
    
    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None
    crystal._sites = crystal._initialize_sites()
    
    return crystal


__all__ = ['apply_strain', 'apply_deformation']

