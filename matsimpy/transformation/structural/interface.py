"""
Interface structure builders.

Tools for creating interfaces between materials:
- Heterostructures (film on substrate)
- Grain boundaries
- Multilayer structures

The implemented public builder covers conservative z-stacking. More
sophisticated lattice matching, strain minimization, and interface
optimization are intentionally outside this stability-focused builder.

Examples:
    >>> from matsimpy import Crystal, Lattice
    >>> from matsimpy.builders.interface import create_simple_interface
    >>>
    >>> from matsimpy.builders.bulk import from_prototype
    >>> si = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
    >>> ge = Crystal(['Ge'], [[0,0,0]], Lattice.cubic(5.65))
    >>>
    >>> interface = create_simple_interface(si, ge, vacuum=5.0)
"""

import numpy as np

from ...core import Crystal, Lattice


def create_simple_interface(
    substrate: Crystal,
    film: Crystal,
    vacuum: float = 5.0,
    gap: float = 2.0,
    center: bool = True,
) -> Crystal:
    """Create a simple z-stacked interface between two crystals.

    This intentionally implements only the conservative stacking case: the
    substrate in-plane lattice is retained, film Cartesian positions are placed
    above the substrate, and the returned object is a MatSimPy ``Crystal``.
    """
    if not isinstance(substrate, Crystal) or not isinstance(film, Crystal):
        raise TypeError("substrate and film must be Crystal instances")
    if vacuum < 0:
        raise ValueError("vacuum must be non-negative")
    if gap < 0:
        raise ValueError("gap must be non-negative")

    substrate_cart = substrate.cart_positions.copy()
    film_cart = film.cart_positions.copy()

    substrate_min_z = float(np.min(substrate_cart[:, 2]))
    substrate_cart[:, 2] -= substrate_min_z
    substrate_max_z = float(np.max(substrate_cart[:, 2]))

    film_min_z = float(np.min(film_cart[:, 2]))
    film_cart[:, 2] -= film_min_z
    film_cart[:, 2] += substrate_max_z + gap

    combined_cart = np.vstack([substrate_cart, film_cart])
    z_span = float(np.max(combined_cart[:, 2]) - np.min(combined_cart[:, 2]))
    c_length = max(z_span + vacuum, 1e-8)

    lattice_vectors = substrate.lattice.lattice_vectors.copy()
    lattice_vectors[2] = np.array([0.0, 0.0, c_length])
    lattice = Lattice(lattice_vectors)

    if center and vacuum:
        combined_min_z = float(np.min(combined_cart[:, 2]))
        combined_max_z = float(np.max(combined_cart[:, 2]))
        combined_cart[:, 2] += (
            c_length - (combined_max_z - combined_min_z)
        ) / 2 - combined_min_z

    species = list(substrate.species) + list(film.species)
    site_properties = None
    if substrate.site_properties or film.site_properties:
        substrate_props = (
            list(substrate.site_properties)
            if substrate.site_properties
            else [{} for _ in substrate.species]
        )
        film_props = (
            list(film.site_properties)
            if film.site_properties
            else [{} for _ in film.species]
        )
        site_properties = substrate_props + film_props

    return Crystal(
        species,
        combined_cart.tolist(),
        lattice,
        coords_are_cartesian=True,
        pbc=(True, True, False),
        site_properties=site_properties,
    )


__all__ = ["create_simple_interface"]
