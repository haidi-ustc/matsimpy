"""
Interface generation tools.

Generate interfaces between different materials, including
heterostructures, grain boundaries, and multilayers.
"""

from typing import List, Optional, Union, Tuple
import numpy as np
from ..core import Crystal, Lattice


def generate_interface(
    structure1: Crystal,
    structure2: Crystal,
    miller1: Tuple[int, int, int],
    miller2: Tuple[int, int, int],
    vacuum: float = 0.0,
    strain_tolerance: float = 0.05,
    **kwargs
) -> Crystal:
    """
    Generate interface between two crystal structures.
    
    Args:
        structure1: First crystal structure (substrate)
        structure2: Second crystal structure (film)
        miller1: Miller indices for structure1 surface
        miller2: Miller indices for structure2 surface
        vacuum: Vacuum spacing between structures (Angstroms)
        strain_tolerance: Maximum allowed strain for lattice matching
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Interface structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.interfaces import generate_interface
        >>> si = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> ge = Crystal(['Ge'], [[0,0,0]], Lattice.cubic(5.65))
        >>> interface = generate_interface(si, ge, (0,0,1), (0,0,1), vacuum=5.0)
    """
    from ..generation.slab import generate_slab
    
    # Generate slabs for both structures
    slab1 = generate_slab(structure1, miller1, min_slab_size=10, min_vacuum_size=0)
    slab2 = generate_slab(structure2, miller2, min_slab_size=10, min_vacuum_size=0)
    
    # Calculate lattice mismatch
    a1 = np.linalg.norm(slab1.lattice.lattice_vectors[0])
    a2 = np.linalg.norm(slab2.lattice.lattice_vectors[0])
    
    b1 = np.linalg.norm(slab1.lattice.lattice_vectors[1])
    b2 = np.linalg.norm(slab2.lattice.lattice_vectors[1])
    
    strain_a = abs(a1 - a2) / max(a1, a2)
    strain_b = abs(b1 - b2) / max(b1, b2)
    
    if strain_a > strain_tolerance or strain_b > strain_tolerance:
        import warnings
        warnings.warn(
            f"Large lattice mismatch: strain_a={strain_a:.3f}, strain_b={strain_b:.3f}. "
            f"Consider using a supercell or different orientations."
        )
    
    # Combine structures
    # Use lattice from structure1 (substrate)
    combined_lattice_vectors = slab1.lattice.lattice_vectors.copy()
    
    # Calculate total height
    height1 = np.linalg.norm(slab1.lattice.lattice_vectors[2])
    height2 = np.linalg.norm(slab2.lattice.lattice_vectors[2])
    total_height = height1 + height2 + vacuum
    
    # Update c vector
    c_direction = slab1.lattice.lattice_vectors[2] / np.linalg.norm(slab1.lattice.lattice_vectors[2])
    combined_lattice_vectors[2] = c_direction * total_height
    
    combined_lattice = Lattice(combined_lattice_vectors)
    
    # Combine species and positions
    combined_species = []
    combined_positions = []
    
    # Add structure1 atoms (bottom)
    for spec, pos in zip(slab1.species, slab1.positions):
        combined_species.append(spec)
        # Scale z position to new cell
        new_pos = pos.copy()
        new_pos[2] = pos[2] * (height1 / total_height)
        combined_positions.append(new_pos)
    
    # Add structure2 atoms (top)
    for spec, pos in zip(slab2.species, slab2.positions):
        combined_species.append(spec)
        # Shift and scale z position
        new_pos = pos.copy()
        new_pos[2] = (height1 + vacuum) / total_height + pos[2] * (height2 / total_height)
        combined_positions.append(new_pos)
    
    return Crystal(combined_species, combined_positions, combined_lattice)


def generate_grain_boundary(
    structure: Crystal,
    rotation_axis: Tuple[int, int, int],
    rotation_angle: float,
    boundary_plane: Tuple[int, int, int],
    vacuum: float = 0.0,
    **kwargs
) -> Crystal:
    """
    Generate grain boundary structure.
    
    Args:
        structure: Base crystal structure
        rotation_axis: Rotation axis (Miller indices)
        rotation_angle: Rotation angle in degrees
        boundary_plane: Grain boundary plane (Miller indices)
        vacuum: Vacuum spacing at boundary
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Grain boundary structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.interfaces import generate_grain_boundary
        >>> cu = Crystal(['Cu'], [[0,0,0]], Lattice.cubic(3.61))
        >>> # Sigma 5 (001) twist grain boundary
        >>> gb = generate_grain_boundary(cu, (0,0,1), 36.87, (0,0,1))
    """
    from ..transformation import rotate
    from ..generation.slab import generate_slab
    
    # Generate slab with boundary plane
    slab1 = generate_slab(structure, boundary_plane, min_slab_size=15, min_vacuum_size=0)
    
    # Create rotated version
    slab2 = rotate(slab1, rotation_angle, rotation_axis)
    
    # Combine to create grain boundary
    # This is simplified - full implementation would handle CSL,
    # periodic boundaries, and optimization
    
    gb = generate_interface(
        slab1, slab2, 
        boundary_plane, boundary_plane,
        vacuum=vacuum,
        **kwargs
    )
    
    return gb


def generate_multilayer(
    structures: List[Crystal],
    miller_indices: List[Tuple[int, int, int]],
    layer_thicknesses: List[float],
    vacuum_spacings: Optional[List[float]] = None,
    **kwargs
) -> Crystal:
    """
    Generate multilayer (superlattice) structure.
    
    Args:
        structures: List of crystal structures for each layer
        miller_indices: Miller indices for each layer surface
        layer_thicknesses: Thickness of each layer (Angstroms)
        vacuum_spacings: Vacuum spacing between layers (default: 0 for all)
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Multilayer structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.interfaces import generate_multilayer
        >>> si = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> ge = Crystal(['Ge'], [[0,0,0]], Lattice.cubic(5.65))
        >>> # Si/Ge/Si superlattice
        >>> multilayer = generate_multilayer([si, ge, si], [(0,0,1)]*3, [20, 10, 20])
    """
    if vacuum_spacings is None:
        vacuum_spacings = [0.0] * (len(structures) - 1)
    
    # Generate first layer
    from ..generation.slab import generate_slab
    
    result = generate_slab(
        structures[0], 
        miller_indices[0],
        min_slab_size=layer_thicknesses[0],
        min_vacuum_size=0
    )
    
    # Add subsequent layers
    for i in range(1, len(structures)):
        next_slab = generate_slab(
            structures[i],
            miller_indices[i],
            min_slab_size=layer_thicknesses[i],
            min_vacuum_size=0
        )
        
        vacuum = vacuum_spacings[i - 1] if i - 1 < len(vacuum_spacings) else 0.0
        
        result = generate_interface(
            result, next_slab,
            (0, 0, 1), (0, 0, 1),  # Use c-direction
            vacuum=vacuum
        )
    
    return result


def find_coincident_sites(
    lattice1: Lattice,
    lattice2: Lattice,
    max_index: int = 3,
    tolerance: float = 0.1
) -> List[Tuple[np.ndarray, float]]:
    """
    Find coincident site lattices (CSL) for two lattices.
    
    Args:
        lattice1: First lattice
        lattice2: Second lattice
        max_index: Maximum CSL index to search
        tolerance: Tolerance for site matching (Angstroms)
    
    Returns:
        List of (transformation_matrix, sigma) tuples
        
    Examples:
        >>> from matsimpy import Lattice
        >>> from matsimpy.generation.interfaces import find_coincident_sites
        >>> lat = Lattice.cubic(3.61)
        >>> csls = find_coincident_sites(lat, lat, max_index=5)
    """
    # Placeholder for CSL finding algorithm
    # Full implementation would use CSL theory
    
    csls = []
    
    # Simple example: identity (Sigma=1)
    csls.append((np.eye(3), 1.0))
    
    return csls


__all__ = [
    'generate_interface',
    'generate_grain_boundary',
    'generate_multilayer',
    'find_coincident_sites',
]

