"""
Rotation transformations for structures.

Provides both functional (immutable-style) and in-place rotation operations.
"""

from typing import List, Optional, Union
import numpy as np
from ...core import Crystal, Molecule
from ..base import _validate_structure


def rotate(
    structure: Union[Crystal, Molecule],
    angle: float,
    axis: List[float],
    center: Optional[List[float]] = None,
) -> Union[Crystal, Molecule]:
    """
    Rotate structure around an axis.

    Always returns a new structure. For in-place modification, use the
    structure's rotate method directly.

    Args:
        structure: Crystal or Molecule to rotate
        angle: Rotation angle in degrees
        axis: Rotation axis [x, y, z] (will be normalized)
        center: Rotation center in Cartesian coordinates.
                If None, uses origin for crystals or COM for molecules (default: None)

    Returns:
        New rotated structure.

    Raises:
        TypeError: If structure is not Crystal or Molecule
        ValueError: If axis is not 3D

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.transformation import rotate
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> # Always returns new structure
        >>> mol2 = rotate(mol, angle=90, axis=[0, 0, 1])
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

    # Always create a new structure
    new_structure = structure.copy()
    
    # Use structure's rotate method if available (for molecules)
    if isinstance(new_structure, Molecule):
        # Translate to origin, rotate, translate back
        new_structure = new_structure.translate((-center).tolist(), inplace=False)
        new_structure = new_structure.rotate(angle, axis.tolist(), inplace=False)
        return new_structure.translate(center.tolist(), inplace=False)
    else:
        # For crystals, rotate Cartesian positions
        from scipy.spatial.transform import Rotation

        rotation = Rotation.from_rotvec(np.radians(angle) * axis)

        # Translate to rotation center, rotate, translate back
        translated_positions = new_structure.cart_positions - center
        rotated_positions = rotation.apply(translated_positions)
        new_structure.cart_positions = rotated_positions + center

        # Update fractional positions
        new_structure.frac_positions = new_structure._convert_to_fractional()
        # Invalidate caches
        new_structure._neighbor_tree = None
        new_structure._neighbor_tree_positions = None
        if hasattr(new_structure, "_sites"):
            new_structure._sites = new_structure._initialize_sites()
        return new_structure


def rotate_around_axis(
    structure: Union[Crystal, Molecule],
    angle: float,
    axis: List[float],
    point: Optional[List[float]] = None,
) -> Union[Crystal, Molecule]:
    """
    Rotate structure around an axis passing through a point.

    Alias for rotate() with center parameter for clarity.
    Always returns a new structure.

    Args:
        structure: Crystal or Molecule to rotate
        angle: Rotation angle in degrees
        axis: Rotation axis [x, y, z]
        point: Point on the rotation axis (default: COM for molecules, origin for crystals)

    Returns:
        New rotated structure
    """
    return rotate(structure, angle, axis, center=point)


__all__ = ["rotate", "rotate_around_axis"]
