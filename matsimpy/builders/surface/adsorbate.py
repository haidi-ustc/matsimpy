"""
Adsorbate placement on surfaces.

Tools for adding adsorbates to slab surfaces.
"""

from matsimpy.utils.tooling import tool
from typing import Tuple, Union
import numpy as np
from ...core import Crystal, Molecule


@tool
def add_adsorbate(
    slab: Crystal,
    adsorbate: Union[str, Crystal, Molecule],
    position: Tuple[float, float],
    height: float,
) -> Crystal:
    """
    Add an adsorbate to a slab surface.

    Args:
        slab: Slab structure
        adsorbate: An element symbol, or a Molecule/Crystal whose Cartesian geometry
            is kept as given (orient it so that it points along the surface normal)
        position: Fractional (a, b) coordinates of the adsorption site
        height: Height in Angstroms of the adsorbate's lowest atom above the
            slab's highest atom, measured along the surface normal (a x b)

    Returns:
        Crystal: Slab with adsorbate

    Examples:
        >>> from matsimpy.builders.surface import generate_slab, add_adsorbate
        >>> from matsimpy.core import Crystal, Lattice, Molecule
        >>> cu = Crystal(['Cu'] * 4, [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        ...              Lattice.cubic(3.61))
        >>> slab = generate_slab(cu, (1, 1, 1), layers=4)
        >>> with_o = add_adsorbate(slab, 'O', (1/3, 1/3), 1.2)
        >>> co = Molecule(['C', 'O'], [[0, 0, 0], [0, 0, 1.13]])
        >>> with_co = add_adsorbate(slab, co, (0, 0), 1.85)
    """
    if not isinstance(slab, Crystal):
        raise TypeError("slab must be a Crystal")
    if len(position) != 2:
        raise ValueError("position must be a 2-tuple of fractional x/y coordinates")
    if not np.isfinite(float(height)):
        raise ValueError(f"height must be finite, got {height}")
    if float(height) < 0:
        raise ValueError(f"height must be non-negative, got {height}")

    slab_cart = slab.cart_positions.copy()
    a_vec, b_vec, c_vec = slab.lattice.matrix
    normal = np.cross(a_vec, b_vec)
    normal = normal / np.linalg.norm(normal)
    if normal @ c_vec < 0:
        normal = -normal
    projections = np.dot(slab_cart, normal)
    surface_proj = float(np.max(projections))
    in_plane = float(position[0]) * a_vec + float(position[1]) * b_vec
    in_plane_proj = np.dot(in_plane, normal)
    anchor = in_plane + normal * (surface_proj + float(height) - in_plane_proj)

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
        # centre the adsorbate over the site within the surface plane
        center = adsorbate_cart.mean(axis=0)
        shift = in_plane - center
        adsorbate_cart += shift - (shift @ normal) * normal
        ads_proj = np.dot(adsorbate_cart, normal)
        ads_min_proj = float(np.min(ads_proj))
        adsorbate_cart += normal * (surface_proj + float(height) - ads_min_proj)
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
