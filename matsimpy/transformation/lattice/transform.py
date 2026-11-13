"""
Lattice transformation and standardization operations.
"""

from matsimpy.utils.tooling import tool
import copy
from typing import Dict, List, Optional, Union
import numpy as np
from ...core import Crystal, Lattice
from ...utils.validation import validate_matrix3


@tool
def rotate_lattice(
    crystal: Crystal,
    rotation_matrix: Union[List[List[float]], np.ndarray],
    rotate_atoms: bool = True,
) -> Crystal:
    """
    Rigidly rotate the lattice (and by default the atoms) in Cartesian space.

    Cartesian vectors map as ``x' = R x``, so the lattice rows become ``A @ R.T``.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        rotation_matrix: 3x3 proper rotation matrix R (orthogonal, det +1)
        rotate_atoms: If True (default), the atoms rotate with the lattice
            (fractional coordinates unchanged).  If False, the atoms keep their
            Cartesian positions and only the cell is rotated.

    Returns:
        New rotated crystal structure

    Raises:
        ValueError: If R is not a finite 3x3 proper rotation matrix.

    Examples:
        >>> from matsimpy.transformation.lattice import rotate_lattice
        >>> from matsimpy.builders.bulk import from_prototype
        >>> import numpy as np
        >>> crystal = from_prototype('sc', 'Po', 3.0)
        >>> # 90 degree rotation around z: a -> +y
        >>> R = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
        >>> rotate_lattice(crystal, R).lattice.matrix[0].round(6) + 0.0
        array([0., 3., 0.])
    """
    if not isinstance(rotate_atoms, (bool, np.bool_)):
        raise TypeError("rotate_atoms must be a bool")
    rotation = validate_matrix3("rotation_matrix", rotation_matrix)
    if not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-6):
        raise ValueError("rotation_matrix must be orthogonal (R @ R.T = I)")
    if np.linalg.det(rotation) <= 0:
        raise ValueError(
            "rotation_matrix must be a proper rotation (det +1); "
            "a reflection would make the cell left-handed"
        )

    new_lattice = Lattice(crystal.lattice.matrix @ rotation.T)
    if rotate_atoms:
        new_positions = crystal.frac_positions
    else:
        new_positions = crystal.cart_positions @ new_lattice.inv_matrix

    return Crystal(
        list(crystal.species), new_positions,
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


@tool
def transform_lattice(
    crystal: Crystal,
    transformation_matrix: Union[List[List[float]], np.ndarray],
    transform_positions: bool = True,
) -> Crystal:
    """
    Apply a general linear map (deformation gradient) to the lattice.

    Same as :func:`apply_deformation`: Cartesian vectors map as ``x' = T x`` and
    the lattice rows become ``A @ T.T``.  This is *not* a change of basis; to
    build a supercell or a different cell of the same crystal use
    ``make_supercell`` or ``standardize_cell(..., to_primitive=True)``.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        transformation_matrix: 3x3 matrix T with positive determinant
        transform_positions: If True (default), the atoms move with the
            lattice; if False they keep their Cartesian positions.

    Returns:
        New transformed crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import transform_lattice
        >>> from matsimpy.builders.bulk import from_prototype
        >>> crystal = from_prototype('sc', 'Po', 3.0)
        >>> # stretch z by 10%
        >>> round(float(transform_lattice(crystal, [[1, 0, 0], [0, 1, 0], [0, 0, 1.1]]).lattice.c), 3)
        3.3
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
        crystal.lattice.matrix,
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
    new_cart = np.asarray(frac_positions, dtype=np.float64) @ lattice.matrix
    inv_lattice = np.linalg.inv(lattice.matrix)
    pbc = np.asarray(crystal.pbc, dtype=bool)
    used = set()
    mapping = []

    def periodic_distance(position1: np.ndarray, position2: np.ndarray) -> float:
        delta_frac = (position1 - position2) @ inv_lattice
        delta_frac[pbc] -= np.rint(delta_frac[pbc])
        return float(np.linalg.norm(delta_frac @ lattice.matrix))

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

    site_props = crystal.site_properties  # deep copy once, not once per site
    return [copy.deepcopy(site_props[index]) for index in mapping]


@tool
def standardize_cell(
    crystal: Crystal, to_primitive: bool = False
) -> Crystal:
    """
    Standardize crystal cell using spglib conventions.

    ``to_primitive=False`` returns spglib's standardized conventional cell;
    ``to_primitive=True`` returns the primitive cell found by spglib.

    Always returns a new crystal structure.

    Args:
        crystal: Fully periodic crystal structure
        to_primitive: If True, convert to primitive cell

    Returns:
        New standardized crystal structure

    Raises:
        ImportError: If spglib is not installed.
        ValueError: If the crystal is not periodic along all three axes, if
            spglib cannot standardize it, or if the crystal has site
            properties and the new cell is not just a reordering of its atoms
            (properties cannot be carried over reliably).

    Examples:
        >>> from matsimpy.transformation.lattice import standardize_cell
        >>> standardized = standardize_cell(crystal)
        >>> primitive = standardize_cell(crystal, to_primitive=True)
    """
    try:
        import spglib
    except ImportError as e:
        raise ImportError(
            "spglib is required for standardize_cell. "
            "Install with: pip install spglib or pip install MatSimPy[analysis]"
        ) from e

    if not all(crystal.pbc):
        raise ValueError(
            f"standardize_cell needs a crystal periodic along all axes, got pbc={tuple(crystal.pbc)}; "
            "spglib may reorder the axes, which would make the pbc flags meaningless"
        )

    species_to_number, number_to_species = _spglib_number_maps(list(crystal.species))
    cell = (
        crystal.lattice.matrix,
        crystal.frac_positions,
        [species_to_number[s] for s in crystal.species],
    )

    result = spglib.find_primitive(cell) if to_primitive else spglib.standardize_cell(cell)
    if result is None:
        raise ValueError("spglib failed to standardize the cell (symmetry search failed)")

    lattice, positions, numbers = result
    new_lattice = Lattice(lattice)
    species = [number_to_species[int(n)] for n in numbers]
    site_properties = _map_site_properties(crystal, species, positions, new_lattice)
    if crystal.site_properties and site_properties is None:
        raise ValueError(
            "standardize_cell changed the atoms of a crystal with site properties; "
            "the properties cannot be carried over. Remove them first "
            "(crystal.with_site_properties(None)) and reassign them afterwards."
        )
    return Crystal(
        species, positions,
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=[True, True, True],
        site_properties=site_properties,
    )


__all__ = [
    "rotate_lattice",
    "transform_lattice",
    "get_niggli_reduced",
    "standardize_cell",
]
