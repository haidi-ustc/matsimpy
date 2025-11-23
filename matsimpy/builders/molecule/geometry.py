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

    axis = np.array(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)

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
    if len(species) != 3:
        raise NotImplementedError("Currently only supports triatomic bent molecules")

    # Central atom at origin
    positions = [np.array([0.0, 0.0, 0.0])]

    # First bond along x-axis
    positions.append(np.array([bond_lengths[0], 0.0, 0.0]))

    # Second bond at angle
    angle_rad = np.radians(angles[0])
    x = bond_lengths[1] * np.cos(angle_rad)
    y = bond_lengths[1] * np.sin(angle_rad)
    positions.append(np.array([x, y, 0.0]))

    return Molecule(species, positions)


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
