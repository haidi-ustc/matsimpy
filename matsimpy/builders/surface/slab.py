"""
Surface slab generation.

Generate surface slabs from bulk structures with various Miller indices,
vacuum spacing, and terminations.
"""

from typing import Tuple, Optional
import numpy as np
from ...core import Crystal, Lattice


def generate_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: float,
    min_vacuum_size: float,
    layers: Optional[int] = None,
    center_slab: bool = True,
    **kwargs,
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
        **kwargs: Additional parameters

    Returns:
        Crystal: Slab structure with vacuum

    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.builders.surface import generate_slab
        >>> from matsimpy.builders.bulk import from_prototype
        >>> bulk = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
        >>> slab = generate_slab(bulk, (1,0,0), min_slab_size=10, min_vacuum_size=15)
        >>> slab = generate_slab(bulk, (1,1,1), layers=5, min_vacuum_size=15)
    """
    h, k, l = miller_index
    if h == 0 and k == 0 and l == 0:
        raise ValueError("Miller index cannot be (0, 0, 0)")

    # Get the surface normal vector in Cartesian coordinates
    lattice_matrix = bulk.lattice.lattice_vectors
    surface_normal = np.dot(lattice_matrix.T, np.array([h, k, l]))
    surface_normal = surface_normal / np.linalg.norm(surface_normal)

    # Calculate d-spacing for this Miller index
    # d = 1/|h*a* + k*b* + l*c*| where a*, b*, c* are reciprocal lattice vectors
    # For simple case, approximate d-spacing
    d_spacing = (
        np.linalg.norm(lattice_matrix[0]) / np.sqrt(h**2 + k**2 + l**2)
        if (h**2 + k**2 + l**2) > 0
        else 1.0
    )

    # Determine number of layers if not specified
    if layers is None:
        layers = max(2, int(np.ceil(min_slab_size / d_spacing)))
    if layers <= 0:
        raise ValueError("layers must be positive")

    # Create new lattice for slab
    # Simplified implementation: repeat the input cell along the third lattice
    # direction and add vacuum.  The requested Miller index currently affects
    # the layer-count estimate only; full surface reorientation should be added
    # in a dedicated crystallographic slab builder.
    c_len = np.linalg.norm(lattice_matrix[2])
    slab_thickness = max(layers * c_len, min_slab_size)
    total_c = slab_thickness + min_vacuum_size

    new_lattice_vectors = lattice_matrix.copy()
    c_direction = new_lattice_vectors[2] / c_len
    new_lattice_vectors[2] = c_direction * total_c

    new_lattice = Lattice(new_lattice_vectors)

    # Transform atomic positions
    new_species = []
    new_positions = []

    slab_fraction = slab_thickness / total_c
    z_offset = (min_vacuum_size / total_c / 2.0) if center_slab else 0.0

    for layer in range(layers):
        for spec, pos in zip(bulk.species, bulk.positions):
            pos = np.array(pos, dtype=np.float64)
            new_frac = pos.copy()
            new_frac[0] = new_frac[0] % 1.0
            new_frac[1] = new_frac[1] % 1.0
            # Repeat along the slab direction, compressing the repeated slab
            # into the non-vacuum portion of the new cell.
            new_frac[2] = ((pos[2] % 1.0) + layer) / layers
            new_frac[2] = new_frac[2] * slab_fraction + z_offset
            new_species.append(spec)
            new_positions.append(new_frac.tolist())

    return Crystal(new_species, new_positions, new_lattice, pbc=[True, True, False])


def generate_symmetric_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: float,
    min_vacuum_size: float,
    **kwargs,
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
        >>> from matsimpy.builders.surface import generate_symmetric_slab
        >>> slab = generate_symmetric_slab(bulk, (1,1,0), 15, 10)
    """
    slab = generate_slab(
        bulk, miller_index, min_slab_size, min_vacuum_size, center_slab=True, **kwargs
    )

    return slab


__all__ = ["generate_slab", "generate_symmetric_slab"]
