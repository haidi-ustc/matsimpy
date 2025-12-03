"""
Adsorbate placement on surfaces.

Tools for adding adsorbates to slab surfaces.
"""

from typing import Tuple, Union
import numpy as np
from copy import deepcopy
from ...core import Crystal


def add_adsorbate(
    slab: Crystal,
    adsorbate: Union[str, Crystal],
    position: Tuple[float, float],
    height: float,
    **kwargs,
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
        >>> from matsimpy.builders.surface import generate_slab, add_adsorbate
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.builders.bulk import from_prototype
        >>> bulk = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
        >>> slab = generate_slab(bulk, (1,1,1), 10, 15)
        >>> with_ads = add_adsorbate(slab, 'O', (0.5, 0.5), 2.0)
    """
    new_slab = deepcopy(slab)

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
        # Complex adsorbate structure - would need to merge structures
        raise NotImplementedError("Complex adsorbate structures not yet implemented")

    return new_slab


__all__ = ["add_adsorbate"]
