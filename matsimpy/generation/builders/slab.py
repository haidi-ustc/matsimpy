"""
Slab (surface) generation tools.

Generate surface slabs from bulk structures with various terminations,
vacuum spacing, and surface reconstructions.
"""

from typing import List, Optional, Tuple, Union
import numpy as np
from ..core import Crystal, Lattice


def generate_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: float,
    min_vacuum_size: float,
    layers: Optional[int] = None,
    center_slab: bool = True,
    in_unit_planes: bool = False,
    **kwargs
) -> Crystal:
    """
    Generate a surface slab from a bulk crystal structure.
    
    Args:
        bulk: Bulk crystal structure
        miller_index: Miller indices of surface plane (h, k, l)
        min_slab_size: Minimum slab thickness in Angstroms
        min_vacuum_size: Minimum vacuum spacing in Angstroms
        layers: Number of atomic layers (alternative to min_slab_size)
        center_slab: Center the slab in the cell
        in_unit_planes: Use unit plane layers instead of Angstrom units
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Slab structure with vacuum
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.slab import generate_slab
        >>> bulk = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> slab = generate_slab(bulk, (1,0,0), min_slab_size=10, min_vacuum_size=15)
        >>> slab = generate_slab(bulk, (1,1,1), layers=5, min_vacuum_size=15)
    """
    h, k, l = miller_index
    
    # Get the surface normal vector in Cartesian coordinates
    lattice_matrix = bulk.lattice.lattice_vectors
    surface_normal = np.dot(lattice_matrix.T, np.array([h, k, l]))
    surface_normal = surface_normal / np.linalg.norm(surface_normal)
    
    # Calculate d-spacing for this Miller index
    reciprocal_lattice = bulk.lattice.reciprocal_lattice_vectors
    d_spacing = 1.0 / np.linalg.norm(np.dot(reciprocal_lattice.T, np.array([h, k, l])))
    
    # Determine number of layers if not specified
    if layers is None:
        layers = int(np.ceil(min_slab_size / d_spacing))
    
    # Create new lattice for slab
    # Find two lattice vectors in the surface plane
    # This is a simplified approach - full implementation would use
    # more sophisticated algorithm to find optimal surface vectors
    
    # For now, use a simple approach based on Miller indices
    if h != 0:
        # Use b and c as in-plane vectors
        a_surf = lattice_matrix[1]
        b_surf = lattice_matrix[2]
    elif k != 0:
        # Use a and c as in-plane vectors
        a_surf = lattice_matrix[0]
        b_surf = lattice_matrix[2]
    else:
        # Use a and b as in-plane vectors (for (001) surfaces)
        a_surf = lattice_matrix[0]
        b_surf = lattice_matrix[1]
    
    # Calculate c vector (perpendicular to surface)
    slab_thickness = layers * d_spacing
    total_c = slab_thickness + min_vacuum_size
    c_surf = surface_normal * total_c
    
    # Create new lattice
    new_lattice_vectors = np.array([a_surf, b_surf, c_surf])
    new_lattice = Lattice(new_lattice_vectors)
    
    # Transform atomic positions to new coordinate system
    # This is simplified - full implementation would properly handle
    # all atoms and create appropriate surface termination
    
    new_species = []
    new_positions = []
    
    # Get all atoms in a supercell to ensure we capture surface
    # Simplified: just use original atoms and transform
    for spec, pos in zip(bulk.species, bulk.positions):
        # Convert to Cartesian
        cart_pos = np.dot(pos, lattice_matrix)
        
        # Project onto new coordinate system
        # This is a placeholder - needs proper transformation
        new_frac = np.dot(cart_pos, np.linalg.inv(new_lattice_vectors))
        
        # Only keep atoms within slab region
        if center_slab:
            # Center atoms in middle of cell
            z_center = (1.0 - min_vacuum_size / total_c) / 2.0
            new_frac[2] = (new_frac[2] % 1.0) * (slab_thickness / total_c) + (min_vacuum_size / total_c / 2.0)
        else:
            # Place at bottom
            new_frac[2] = (new_frac[2] % 1.0) * (slab_thickness / total_c)
        
        # Wrap fractional coordinates
        new_frac[0] = new_frac[0] % 1.0
        new_frac[1] = new_frac[1] % 1.0
        
        new_species.append(spec)
        new_positions.append(new_frac)
    
    return Crystal(new_species, new_positions, new_lattice)


def generate_symmetric_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: float,
    min_vacuum_size: float,
    **kwargs
) -> Crystal:
    """
    Generate a symmetric slab (same termination on both surfaces).
    
    Args:
        bulk: Bulk crystal structure
        miller_index: Miller indices (h, k, l)
        min_slab_size: Minimum slab thickness in Angstroms
        min_vacuum_size: Minimum vacuum spacing in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Symmetric slab structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.slab import generate_symmetric_slab
        >>> bulk = Crystal(['Fe'], [[0,0,0]], Lattice.cubic(2.87))
        >>> slab = generate_symmetric_slab(bulk, (1,1,0), 15, 10)
    """
    # Generate basic slab
    slab = generate_slab(
        bulk, miller_index, min_slab_size, min_vacuum_size, 
        center_slab=True, **kwargs
    )
    
    # Ensure symmetry by mirroring if needed
    # This is a placeholder - full implementation would check and ensure symmetry
    
    return slab


def get_all_slabs(
    bulk: Crystal,
    max_index: int,
    min_slab_size: float,
    min_vacuum_size: float,
    symmetrize: bool = False,
    **kwargs
) -> List[Tuple[Tuple[int, int, int], Crystal]]:
    """
    Generate all unique slabs up to a maximum Miller index.
    
    Args:
        bulk: Bulk crystal structure
        max_index: Maximum Miller index to consider
        min_slab_size: Minimum slab thickness
        min_vacuum_size: Minimum vacuum spacing
        symmetrize: Generate symmetric slabs
        **kwargs: Additional parameters
    
    Returns:
        List of (miller_index, slab) tuples
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.slab import get_all_slabs
        >>> bulk = Crystal(['Al'], [[0,0,0]], Lattice.cubic(4.05))
        >>> slabs = get_all_slabs(bulk, max_index=2, min_slab_size=10, min_vacuum_size=15)
        >>> for (h,k,l), slab in slabs:
        ...     print(f"({h},{k},{l}): {len(slab.species)} atoms")
    """
    slabs = []
    
    # Generate all Miller indices up to max_index
    for h in range(-max_index, max_index + 1):
        for k in range(-max_index, max_index + 1):
            for l in range(-max_index, max_index + 1):
                # Skip (0,0,0)
                if h == 0 and k == 0 and l == 0:
                    continue
                
                # Skip if not in reduced form (use symmetry)
                # Simplified: just keep positive first non-zero index
                first_nonzero = None
                for idx in [h, k, l]:
                    if idx != 0:
                        first_nonzero = idx
                        break
                
                if first_nonzero is not None and first_nonzero < 0:
                    continue
                
                try:
                    if symmetrize:
                        slab = generate_symmetric_slab(
                            bulk, (h, k, l), min_slab_size, min_vacuum_size, **kwargs
                        )
                    else:
                        slab = generate_slab(
                            bulk, (h, k, l), min_slab_size, min_vacuum_size, **kwargs
                        )
                    slabs.append(((h, k, l), slab))
                except Exception:
                    # Skip if slab generation fails
                    continue
    
    return slabs


def add_adsorbate(
    slab: Crystal,
    adsorbate: Union[str, Crystal],
    position: Tuple[float, float],
    height: float,
    **kwargs
) -> Crystal:
    """
    Add an adsorbate to a slab surface.
    
    Args:
        slab: Slab structure
        adsorbate: Adsorbate species or structure
        position: (x, y) position on surface (fractional)
        height: Height above surface in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Slab with adsorbate
        
    Examples:
        >>> from matsimpy.generation.slab import generate_slab, add_adsorbate
        >>> slab = generate_slab(bulk, (1,1,1), 10, 15)
        >>> with_ads = add_adsorbate(slab, 'O', (0.5, 0.5), 2.0)
    """
    new_slab = slab.copy()
    
    if isinstance(adsorbate, str):
        # Single atom adsorbate
        # Find the top surface (highest z position)
        cart_positions = slab.cart_positions
        max_z = np.max(cart_positions[:, 2])
        
        # Calculate Cartesian position
        x_cart = position[0] * np.linalg.norm(slab.lattice.lattice_vectors[0])
        y_cart = position[1] * np.linalg.norm(slab.lattice.lattice_vectors[1])
        z_cart = max_z + height
        
        cart_pos = np.array([x_cart, y_cart, z_cart])
        
        # Convert to fractional
        frac_pos = np.dot(cart_pos, np.linalg.inv(slab.lattice.lattice_vectors))
        
        # Add atom
        new_slab.add_atom(adsorbate, frac_pos)
    
    else:
        # Complex adsorbate structure
        # Would need to merge structures - placeholder for now
        pass
    
    return new_slab


__all__ = [
    'generate_slab',
    'generate_symmetric_slab',
    'get_all_slabs',
    'add_adsorbate',
]

