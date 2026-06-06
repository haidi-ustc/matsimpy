"""
Adsorbate placement on surfaces.

Tools for adding adsorbates to slab surfaces.
"""

from typing import Tuple, Union
import numpy as np
from ...core import Crystal, Molecule


def add_adsorbate(
    slab: Crystal,
    adsorbate: Union[str, Crystal, Molecule],
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
    if not isinstance(slab, Crystal):
        raise TypeError("slab must be a Crystal")
    if len(position) != 2:
        raise ValueError("position must be a 2-tuple of fractional x/y coordinates")

    slab_cart = slab.cart_positions.copy()
    surface_z = float(np.max(slab_cart[:, 2]))
    anchor = (
        float(position[0]) * slab.lattice.lattice_vectors[0]
        + float(position[1]) * slab.lattice.lattice_vectors[1]
    )
    anchor[2] = surface_z + float(height)

    if isinstance(adsorbate, str):
        adsorbate_species = [adsorbate]
        adsorbate_cart = np.array([anchor], dtype=np.float64)
        adsorbate_site_properties = None
    elif isinstance(adsorbate, (Crystal, Molecule)):
        adsorbate_species = list(adsorbate.species)
        adsorbate_cart = (
            adsorbate.cart_positions.copy()
            if isinstance(adsorbate, Crystal)
            else adsorbate.positions.copy()
        )
        adsorbate_xy_center = np.mean(adsorbate_cart[:, :2], axis=0)
        adsorbate_min_z = float(np.min(adsorbate_cart[:, 2]))
        adsorbate_cart[:, 0] += anchor[0] - adsorbate_xy_center[0]
        adsorbate_cart[:, 1] += anchor[1] - adsorbate_xy_center[1]
        adsorbate_cart[:, 2] += anchor[2] - adsorbate_min_z
        adsorbate_site_properties = (
            list(adsorbate.site_properties) if adsorbate.site_properties else None
        )
    else:
        raise TypeError("adsorbate must be an element symbol, Crystal, or Molecule")

    combined_species = list(slab.species) + adsorbate_species
    combined_cart = np.vstack([slab_cart, adsorbate_cart])

    site_properties = None
    if slab.site_properties or adsorbate_site_properties:
        slab_props = (
            list(slab.site_properties)
            if slab.site_properties
            else [{} for _ in slab.species]
        )
        ads_props = (
            adsorbate_site_properties
            if adsorbate_site_properties
            else [{} for _ in adsorbate_species]
        )
        site_properties = slab_props + ads_props

    return Crystal(
        combined_species,
        combined_cart.tolist(),
        slab.lattice,
        coords_are_cartesian=True,
        pbc=list(slab.pbc),
        site_properties=site_properties,
    )


__all__ = ["add_adsorbate"]
