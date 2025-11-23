"""
Lattice scaling and volume operations.
"""

from typing import List, Optional, Union
import numpy as np
from ...core import Crystal, Lattice


def scale_lattice(
    crystal: Crystal,
    scale_factor: Union[float, List[float], np.ndarray],
    inplace: bool = False,
) -> Crystal:
    """
    Scale lattice by a factor.

    Args:
        crystal: Crystal structure to scale
        scale_factor: Uniform scale factor or [a, b, c] for anisotropic scaling
        inplace: If True, modify crystal in-place

    Returns:
        Scaled crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import scale_lattice
        >>> # Uniform 10% expansion
        >>> scaled = scale_lattice(crystal, 1.1)
        >>> # Anisotropic scaling
        >>> scaled = scale_lattice(crystal, [1.1, 1.0, 0.95])
    """
    from ..base import _copy_structure

    if not inplace:
        crystal = _copy_structure(crystal)

    if isinstance(scale_factor, (int, float)):
        scale_matrix = np.eye(3) * scale_factor
    else:
        scale_factor = np.array(scale_factor, dtype=np.float64)
        scale_matrix = np.diag(scale_factor)

    new_lattice_vectors = np.dot(scale_matrix, crystal.lattice.lattice_vectors)
    crystal.lattice = Lattice(new_lattice_vectors)

    # Update Cartesian positions (fractional stay same)
    crystal.cart_positions = crystal._convert_to_cartesian()
    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None

    return crystal


def set_volume(
    crystal: Crystal, target_volume: float, inplace: bool = False
) -> Crystal:
    """
    Scale crystal to target volume.

    Args:
        crystal: Crystal structure
        target_volume: Target volume in Angstrom^3
        inplace: If True, modify crystal in-place

    Returns:
        Scaled crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import set_volume
        >>> # Set to 1000 A^3
        >>> scaled = set_volume(crystal, 1000.0)
    """
    current_volume = crystal.volume
    scale_factor = (target_volume / current_volume) ** (1.0 / 3.0)

    return scale_lattice(crystal, scale_factor, inplace=inplace)


def optimize_lattice(
    crystal: Crystal,
    target_density: Optional[float] = None,
    target_volume: Optional[float] = None,
    preserve_angles: bool = True,
    inplace: bool = False,
) -> Crystal:
    """
    Optimize lattice parameters to match target density or volume.

    Args:
        crystal: Crystal structure
        target_density: Target density in g/cm^3
        target_volume: Target volume in Angstrom^3
        preserve_angles: If True, preserve lattice angles
        inplace: If True, modify crystal in-place

    Returns:
        Optimized crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import optimize_lattice
        >>> # Optimize to match experimental density
        >>> optimized = optimize_lattice(crystal, target_density=2.33)
    """
    if target_density is None and target_volume is None:
        raise ValueError("Must specify either target_density or target_volume")

    if target_density is not None:
        # Calculate required volume from density
        # density = mass / volume
        mass = crystal.composition.mass  # in amu
        # Convert amu to grams and A^3 to cm^3
        amu_to_g = 1.66053906660e-24
        angstrom3_to_cm3 = 1e-24
        mass_g = mass * amu_to_g
        target_volume = mass_g / target_density / angstrom3_to_cm3

    return set_volume(crystal, target_volume, inplace=inplace)


__all__ = ["scale_lattice", "set_volume", "optimize_lattice"]
