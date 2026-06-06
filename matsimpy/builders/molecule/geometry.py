"""
Molecular geometry builders.

Build molecules with specific geometries (linear, bent, trigonal, etc.).
"""

from typing import List
import numpy as np
from ...core import Molecule


def build_linear(
    species: List[str], bond_lengths: List[float], axis: List[float] = [1, 0, 0]
) -> Molecule:
    """
    Build linear molecule along an axis.

    Args:
        species: List of atomic species
        bond_lengths: List of bond lengths (n-1 for n atoms)
        axis: Direction vector for molecule axis

    Returns:
        Linear molecule

    Examples:
        >>> from matsimpy.builders.molecule import build_linear
        >>> # Build CO2: O=C=O
        >>> co2 = build_linear(['O', 'C', 'O'], [1.16, 1.16])
    """
    if len(bond_lengths) != len(species) - 1:
        raise ValueError(f"Need {len(species)-1} bond lengths for {len(species)} atoms")
    if any(not np.isfinite(b) or b <= 0 for b in bond_lengths):
        raise ValueError("bond_lengths must be positive and finite")

    axis = np.array(axis, dtype=np.float64)
    if axis.shape != (3,):
        raise ValueError(f"axis must be a 3-element vector, got shape {axis.shape}")
    if not np.all(np.isfinite(axis)):
        raise ValueError("axis must be finite")
    axis_norm = np.linalg.norm(axis)
    if axis_norm == 0:
        raise ValueError("axis must be non-zero")
    axis = axis / axis_norm

    positions = []
    current_pos = np.array([0.0, 0.0, 0.0])
    positions.append(current_pos.copy())

    for length in bond_lengths:
        current_pos += axis * length
        positions.append(current_pos.copy())

    return Molecule(species, positions)


def build_bent(
    species: List[str],
    bond_lengths: List[float],
    angles: List[float],
    plane_normal: List[float] = [0, 0, 1],
) -> Molecule:
    """
    Build bent molecule (e.g., H2O, bent triatomic).

    Args:
        species: List of atomic species
        bond_lengths: List of bond lengths
        angles: List of bond angles in degrees
        plane_normal: Normal vector to molecular plane

    Returns:
        Bent molecule

    Examples:
        >>> from matsimpy.builders.molecule import build_bent
        >>> # Build H2O with HOH angle of 104.5°
        >>> h2o = build_bent(['O', 'H', 'H'], [0.96, 0.96], [104.5])
    """
    if len(species) < 3:
        raise ValueError("Bent molecule requires at least 3 atoms")
    if len(bond_lengths) != len(species) - 1:
        raise ValueError(f"Need {len(species)-1} bond lengths for {len(species)} atoms")
    if len(angles) != len(species) - 2:
        raise ValueError(f"Need {len(species)-2} bond angles for {len(species)} atoms")
    if any(length <= 0 for length in bond_lengths):
        raise ValueError("bond lengths must be positive")
    if any(angle <= 0 or angle >= 180 for angle in angles):
        raise ValueError("bond angles must be between 0 and 180 degrees")

    plane_normal_array = np.array(plane_normal, dtype=np.float64)
    if plane_normal_array.shape != (3,) or not np.all(np.isfinite(plane_normal_array)):
        raise ValueError("plane_normal must be a finite 3D vector")
    normal_norm = np.linalg.norm(plane_normal_array)
    if normal_norm == 0:
        raise ValueError("plane_normal cannot be zero")
    plane_normal_array = plane_normal_array / normal_norm

    if len(species) == 3:
        # Backward-compatible central-atom model for bent triatomic molecules:
        # species[0] is central, species[1:3] are bonded to it.
        positions = [np.array([0.0, 0.0, 0.0])]
        positions.append(np.array([bond_lengths[0], 0.0, 0.0]))

        angle_rad = np.radians(angles[0])
        x = bond_lengths[1] * np.cos(angle_rad)
        y = bond_lengths[1] * np.sin(angle_rad)
        positions.append(np.array([x, y, 0.0]))
    else:
        # Chain-like bent molecule using internal coordinates:
        # bond_lengths[i] is the distance i -> i+1 and angles[i] is the
        # angle at atom i+1 between atoms i, i+1, and i+2.
        positions = [np.array([0.0, 0.0, 0.0])]
        positions.append(np.array([bond_lengths[0], 0.0, 0.0]))

        direction = np.array([1.0, 0.0])
        for length, angle in zip(bond_lengths[1:], angles):
            turn = np.pi - np.radians(angle)
            rotation = np.array(
                [
                    [np.cos(turn), -np.sin(turn)],
                    [np.sin(turn), np.cos(turn)],
                ]
            )
            direction = rotation @ direction
            direction = direction / np.linalg.norm(direction)
            next_xy = positions[-1][:2] + direction * length
            positions.append(np.array([next_xy[0], next_xy[1], 0.0]))

    positions = np.array(positions, dtype=np.float64)
    positions = _orient_plane(positions, plane_normal_array)
    return Molecule(species, positions)


def _orient_plane(positions: np.ndarray, plane_normal: np.ndarray) -> np.ndarray:
    """Rotate xy-plane positions so their normal matches ``plane_normal``."""
    default_normal = np.array([0.0, 0.0, 1.0])
    dot = float(np.clip(np.dot(default_normal, plane_normal), -1.0, 1.0))
    if np.isclose(dot, 1.0):
        return positions
    if np.isclose(dot, -1.0):
        rotation = np.diag([1.0, -1.0, -1.0])
        return positions @ rotation.T

    axis = np.cross(default_normal, plane_normal)
    axis = axis / np.linalg.norm(axis)
    angle = np.arccos(dot)
    skew = np.array(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ]
    )
    rotation = (
        np.eye(3)
        + np.sin(angle) * skew
        + (1.0 - np.cos(angle)) * (skew @ skew)
    )
    return positions @ rotation.T


def build_trigonal_planar(
    central_atom: str, peripheral_atoms: List[str], bond_length: float
) -> Molecule:
    """
    Build trigonal planar molecule (e.g., BF3, 120° angles).

    Args:
        central_atom: Central atom species
        peripheral_atoms: List of 3 peripheral atom species
        bond_length: Bond length from center to periphery

    Returns:
        Trigonal planar molecule

    Examples:
        >>> from matsimpy.builders.molecule import build_trigonal_planar
        >>> bf3 = build_trigonal_planar('B', ['F', 'F', 'F'], 1.31)
    """
    if len(peripheral_atoms) != 3:
        raise ValueError("Trigonal planar requires exactly 3 peripheral atoms")

    species = [central_atom] + peripheral_atoms
    positions = [np.array([0.0, 0.0, 0.0])]  # Central atom

    # Three atoms at 120° angles
    for i in range(3):
        angle = i * 2 * np.pi / 3
        x = bond_length * np.cos(angle)
        y = bond_length * np.sin(angle)
        positions.append(np.array([x, y, 0.0]))

    return Molecule(species, positions)


def build_tetrahedral(
    central_atom: str, peripheral_atoms: List[str], bond_length: float
) -> Molecule:
    """
    Build tetrahedral molecule (e.g., CH4, NH4+).

    Args:
        central_atom: Central atom species
        peripheral_atoms: List of 4 peripheral atom species
        bond_length: Bond length from center to periphery

    Returns:
        Tetrahedral molecule

    Examples:
        >>> from matsimpy.builders.molecule import build_tetrahedral
        >>> ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
    """
    if len(peripheral_atoms) != 4:
        raise ValueError("Tetrahedral requires exactly 4 peripheral atoms")

    species = [central_atom] + peripheral_atoms
    positions = [np.array([0.0, 0.0, 0.0])]  # Central atom

    # Tetrahedral vertices
    tet_vertices = np.array(
        [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=np.float64
    )

    # Normalize and scale
    tet_vertices = tet_vertices / np.linalg.norm(tet_vertices[0]) * bond_length

    for vertex in tet_vertices:
        positions.append(vertex)

    return Molecule(species, positions)


__all__ = ["build_linear", "build_bent", "build_trigonal_planar", "build_tetrahedral"]
