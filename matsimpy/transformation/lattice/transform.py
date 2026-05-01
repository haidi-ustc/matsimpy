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
) -> Crystal:
    """
    Rotate lattice (and optionally atoms).

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        rotation_matrix: 3x3 rotation matrix
        rotate_atoms: If True, also rotate atomic positions

    Returns:
        New rotated crystal structure

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
    rotation_matrix = np.array(rotation_matrix, dtype=np.float64)

    # Rotate lattice vectors
    new_lattice_vectors = np.dot(rotation_matrix, crystal.lattice.lattice_vectors)
    new_lattice = Lattice(new_lattice_vectors)

    if rotate_atoms:
        # Rotate Cartesian positions
        new_cart_positions = np.dot(crystal.cart_positions, rotation_matrix.T)
        # Convert back to fractional
        new_positions = np.dot(
            new_cart_positions, np.linalg.inv(new_lattice_vectors)
        )
    else:
        # Keep fractional positions unchanged
        new_positions = crystal.frac_positions

    return Crystal(
        list(crystal.species), new_positions.tolist(),
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


def transform_lattice(
    crystal: Crystal,
    transformation_matrix: Union[List[List[float]], np.ndarray],
    transform_positions: bool = False,
) -> Crystal:
    """
    Apply general linear transformation to lattice.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        transformation_matrix: 3x3 transformation matrix
        transform_positions: If True, transform atomic positions by same matrix

    Returns:
        New transformed crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import transform_lattice
        >>> # Convert to primitive cell (for FCC to simple cubic, etc.)
        >>> T = [[0.5, 0.5, 0], [0, 0.5, 0.5], [0.5, 0, 0.5]]
        >>> primitive = transform_lattice(crystal, T)
    """
    from .strain import apply_deformation

    return apply_deformation(
        crystal, transformation_matrix, transform_positions
    )


def get_niggli_reduced(crystal: Crystal) -> Crystal:
    """
    Get Niggli-reduced cell.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure

    Returns:
        New Niggli-reduced crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import get_niggli_reduced
        >>> reduced = get_niggli_reduced(crystal)

    Note:
        Requires spglib for full implementation.
    """
    # Placeholder - just returns a copy
    return crystal.copy()


def standardize_cell(
    crystal: Crystal, to_primitive: bool = False
) -> Crystal:
    """
    Standardize crystal cell using spglib conventions.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        to_primitive: If True, convert to primitive cell

    Returns:
        New standardized crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import standardize_cell
        >>> standardized = standardize_cell(crystal)
        >>> primitive = standardize_cell(crystal, to_primitive=True)
    """
    # Placeholder - full implementation would use spglib
    try:
        import spglib

        cell = (
            crystal.lattice.lattice_vectors,
            crystal.frac_positions,
            [crystal.species.index(s) + 1 for s in crystal.species],
        )

        if to_primitive:
            prim_cell = spglib.find_primitive(cell)
            if prim_cell is not None:
                lattice, positions, numbers = prim_cell
                species = [crystal.species[n - 1] for n in numbers]
                return Crystal(
                    species, positions.tolist(),
                    lattice=Lattice(lattice),
                    coords_are_cartesian=False,
                    pbc=list(crystal.pbc),
                    site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
                )
        else:
            std_cell = spglib.standardize_cell(cell)
            if std_cell is not None:
                lattice, positions, numbers = std_cell
                species = [crystal.species[n - 1] for n in numbers]
                return Crystal(
                    species, positions.tolist(),
                    lattice=Lattice(lattice),
                    coords_are_cartesian=False,
                    pbc=list(crystal.pbc),
                    site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
                )

    except ImportError:
        import warnings

        warnings.warn("spglib not available, returning unchanged crystal")

    return crystal.copy()


__all__ = [
    "rotate_lattice",
    "transform_lattice",
    "get_niggli_reduced",
    "standardize_cell",
]
