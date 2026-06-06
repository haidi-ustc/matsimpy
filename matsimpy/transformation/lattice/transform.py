"""
Lattice transformation and standardization operations.
"""

import copy
from typing import Dict, List, Optional, Union
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


def get_niggli_reduced(crystal: Crystal, eps: float = 1e-5) -> Crystal:
    """
    Get Niggli-reduced cell.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        eps: Numerical tolerance passed to spglib

    Returns:
        New Niggli-reduced crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import get_niggli_reduced
        >>> reduced = get_niggli_reduced(crystal)

    Note:
        Requires spglib.
    """
    try:
        import spglib
    except ImportError as e:
        raise ImportError(
            "spglib is required for Niggli reduction. "
            "Install with: pip install spglib or pip install MatSimPy[analysis]"
        ) from e

    if eps <= 0:
        raise ValueError("eps must be positive")

    reduced_lattice_vectors = spglib.niggli_reduce(
        crystal.lattice.lattice_vectors,
        eps=eps,
    )
    if reduced_lattice_vectors is None:
        raise ValueError("spglib failed to Niggli-reduce the lattice")

    reduced_lattice = Lattice(reduced_lattice_vectors)
    reduced_frac_positions = np.dot(
        crystal.cart_positions,
        np.linalg.inv(reduced_lattice_vectors),
    )

    return Crystal(
        list(crystal.species),
        reduced_frac_positions.tolist(),
        lattice=reduced_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(
            list(crystal.site_properties) if crystal.site_properties else None
        ),
    )


def _spglib_number_maps(species: List[str]) -> tuple[Dict[str, int], Dict[int, str]]:
    """Build stable species-number maps for spglib cells."""
    unique_species = []
    for symbol in species:
        if symbol not in unique_species:
            unique_species.append(symbol)
    species_to_number = {
        symbol: index + 1 for index, symbol in enumerate(unique_species)
    }
    number_to_species = {
        index + 1: symbol for index, symbol in enumerate(unique_species)
    }
    return species_to_number, number_to_species


def _map_site_properties(
    crystal: Crystal,
    species: List[str],
    frac_positions: np.ndarray,
    lattice: Lattice,
    tol: float = 1e-5,
) -> Optional[List[dict]]:
    """Map site properties when a standardized cell is only reordered."""
    if not crystal.site_properties:
        return None
    if len(species) != len(crystal):
        return None

    old_cart = crystal.cart_positions
    new_cart = np.asarray(frac_positions, dtype=np.float64) @ lattice.lattice_vectors
    inv_lattice = np.linalg.inv(lattice.lattice_vectors)
    pbc = np.asarray(crystal.pbc, dtype=bool)
    used = set()
    mapping = []

    def periodic_distance(position1: np.ndarray, position2: np.ndarray) -> float:
        delta_frac = (position1 - position2) @ inv_lattice
        delta_frac[pbc] -= np.rint(delta_frac[pbc])
        return float(np.linalg.norm(delta_frac @ lattice.lattice_vectors))

    for new_symbol, new_position in zip(species, new_cart):
        candidates = [
            (
                index,
                periodic_distance(new_position, old_position),
            )
            for index, (old_symbol, old_position) in enumerate(
                zip(crystal.species, old_cart)
            )
            if index not in used and old_symbol == new_symbol
        ]
        if not candidates:
            return None

        old_index, distance = min(candidates, key=lambda item: item[1])
        if distance > tol:
            return None
        used.add(old_index)
        mapping.append(old_index)

    return [copy.deepcopy(crystal.site_properties[index]) for index in mapping]


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
    try:
        import spglib

        species_to_number, number_to_species = _spglib_number_maps(
            list(crystal.species)
        )
        cell = (
            crystal.lattice.lattice_vectors,
            crystal.frac_positions,
            [species_to_number[s] for s in crystal.species],
        )

        if to_primitive:
            prim_cell = spglib.find_primitive(cell)
            if prim_cell is not None:
                lattice, positions, numbers = prim_cell
                new_lattice = Lattice(lattice)
                species = [number_to_species[int(n)] for n in numbers]
                site_properties = _map_site_properties(
                    crystal, species, positions, new_lattice
                )
                return Crystal(
                    species, positions.tolist(),
                    lattice=new_lattice,
                    coords_are_cartesian=False,
                    pbc=list(crystal.pbc),
                    site_properties=site_properties,
                )
        else:
            std_cell = spglib.standardize_cell(cell)
            if std_cell is not None:
                lattice, positions, numbers = std_cell
                new_lattice = Lattice(lattice)
                species = [number_to_species[int(n)] for n in numbers]
                site_properties = _map_site_properties(
                    crystal, species, positions, new_lattice
                )
                return Crystal(
                    species, positions.tolist(),
                    lattice=new_lattice,
                    coords_are_cartesian=False,
                    pbc=list(crystal.pbc),
                    site_properties=site_properties,
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
