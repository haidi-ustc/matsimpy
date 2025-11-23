"""
Rotation transformations for structures.

Provides both functional (immutable-style) and in-place rotation operations.
"""

from typing import List, Optional, Union
import numpy as np
from ...core import Crystal, Molecule
from ..base import _copy_structure, _validate_structure


def rotate(
    structure: Union[Crystal, Molecule],
    angle: float,
    axis: List[float],
    center: Optional[List[float]] = None,
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Rotate structure around an axis.

    This function provides a functional interface to rotation. For molecules,
    you can also use the in-place method: molecule.rotate(angle, axis).

    Args:
        structure: Crystal or Molecule to rotate
        angle: Rotation angle in degrees
        axis: Rotation axis [x, y, z] (will be normalized)
        center: Rotation center in Cartesian coordinates.
                If None, uses origin for crystals or COM for molecules (default: None)
        inplace: If True, modify structure in-place and return same object.
                If False, return a new structure (default: False)

    Returns:
        Rotated structure. If inplace=True, returns the same object.
        If inplace=False, returns a new structure.

    Raises:
        TypeError: If structure is not Crystal or Molecule
        ValueError: If axis is not 3D

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.transformation import rotate
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> # Functional (returns new)
        >>> mol2 = rotate(mol, angle=90, axis=[0, 0, 1])
        >>> # In-place
        >>> rotate(mol, angle=90, axis=[0, 0, 1], inplace=True)
    """
    _validate_structure(structure)

    axis = np.array(axis, dtype=np.float64)
    if axis.ndim != 1 or len(axis) != 3:
        raise ValueError("Rotation axis must be 3D [x, y, z]")

    # Normalize axis
    axis_norm = np.linalg.norm(axis)
    if axis_norm == 0:
        raise ValueError("Rotation axis cannot be zero vector")
    axis = axis / axis_norm

    # Determine rotation center
    if center is None:
        if isinstance(structure, Molecule):
            center = structure.get_center_of_mass()
        else:
            center = [0.0, 0.0, 0.0]
    center = np.array(center, dtype=np.float64)

    if inplace:
        # Use in-place method if available (for molecules)
        if isinstance(structure, Molecule):
            # Translate to origin, rotate, translate back
            structure.translate((-center).tolist())
            structure.rotate(angle, axis.tolist())
            structure.translate(center.tolist())
            return structure
        else:
            # For crystals, rotate Cartesian positions
            from scipy.spatial.transform import Rotation

            rotation = Rotation.from_rotvec(np.radians(angle) * axis)

            # Translate to rotation center, rotate, translate back
            translated_positions = structure.cart_positions - center
            rotated_positions = rotation.apply(translated_positions)
            structure.cart_positions = rotated_positions + center

            # Update fractional positions
            structure.frac_positions = structure._convert_to_fractional()
            # Invalidate caches
            structure._neighbor_tree = None
            structure._neighbor_tree_positions = None
            if hasattr(structure, "_sites"):
                structure._sites = structure._initialize_sites()
            return structure
    else:
        # Create copy and rotate
        new_structure = _copy_structure(structure)
        return rotate(new_structure, angle, axis, center, inplace=True)


def rotate_around_axis(
    structure: Union[Crystal, Molecule],
    angle: float,
    axis: List[float],
    point: Optional[List[float]] = None,
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Rotate structure around an axis passing through a point.

    Alias for rotate() with center parameter for clarity.

    Args:
        structure: Crystal or Molecule to rotate
        angle: Rotation angle in degrees
        axis: Rotation axis [x, y, z]
        point: Point on the rotation axis (default: COM for molecules, origin for crystals)
        inplace: If True, modify structure in-place (default: False)

    Returns:
        Rotated structure
    """
    return rotate(structure, angle, axis, center=point, inplace=inplace)


__all__ = ["rotate", "rotate_around_axis"]
