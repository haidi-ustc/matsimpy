"""
Lattice scaling and volume operations.
"""

from typing import List, Optional, Union
import numpy as np
from ...core import Crystal, Lattice


def _validate_positive_finite_scalar(value: float, name: str) -> float:
    """Return value as float after validating positivity and finiteness."""
    scalar = float(value)
    if not np.isfinite(scalar) or scalar <= 0:
        raise ValueError(f"{name} must be a finite positive value")
    return scalar


def _validate_scale_factor(
    scale_factor: Union[float, List[float], np.ndarray],
) -> np.ndarray:
    """Return a 3x3 scale matrix from a validated scale factor."""
    if np.isscalar(scale_factor):
        scalar = _validate_positive_finite_scalar(scale_factor, "scale_factor")
        return np.eye(3) * scalar

    factors = np.asarray(scale_factor, dtype=np.float64)
    if factors.shape != (3,):
        raise ValueError(
            "scale_factor must be a finite positive scalar or exactly three "
            "finite positive factors"
        )
    if not np.all(np.isfinite(factors)) or np.any(factors <= 0):
        raise ValueError("scale_factor factors must be finite and positive")
    return np.diag(factors)


def scale_lattice(
    crystal: Crystal,
    scale_factor: Union[float, List[float], np.ndarray],
) -> Crystal:
    """
    Scale lattice by a factor.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure to scale
        scale_factor: Uniform scale factor or [a, b, c] for anisotropic scaling

    Returns:
        New scaled crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import scale_lattice
        >>> # Uniform 10% expansion
        >>> scaled = scale_lattice(crystal, 1.1)
        >>> # Anisotropic scaling
        >>> scaled = scale_lattice(crystal, [1.1, 1.0, 0.95])
    """
    scale_matrix = _validate_scale_factor(scale_factor)

    new_lattice_vectors = np.dot(scale_matrix, crystal.lattice.lattice_vectors)
    new_lattice = Lattice(new_lattice_vectors)

    # Fractional positions are invariant under uniform lattice scaling;
    # the new Crystal constructor recomputes Cartesian positions automatically.
    return Crystal(
        list(crystal.species),
        crystal.frac_positions.tolist(),
        new_lattice,
        pbc=list(crystal.pbc),
        coords_are_cartesian=False,
        site_properties=(
            list(crystal.site_properties) if crystal.site_properties else None
        ),
    )


def set_volume(
    crystal: Crystal, target_volume: float
) -> Crystal:
    """
    Scale crystal to target volume.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        target_volume: Target volume in Angstrom^3

    Returns:
        New scaled crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import set_volume
        >>> # Set to 1000 A^3
        >>> scaled = set_volume(crystal, 1000.0)
    """
    target_volume = _validate_positive_finite_scalar(
        target_volume, "target_volume"
    )
    current_volume = crystal.volume
    scale_factor = (target_volume / current_volume) ** (1.0 / 3.0)

    return scale_lattice(crystal, scale_factor)


def optimize_lattice(
    crystal: Crystal,
    target_density: Optional[float] = None,
    target_volume: Optional[float] = None,
    preserve_angles: bool = True,
) -> Crystal:
    """
    Optimize lattice parameters to match target density or volume.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure
        target_density: Target density in g/cm^3
        target_volume: Target volume in Angstrom^3
        preserve_angles: If True, preserve lattice angles

    Returns:
        New optimized crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import optimize_lattice
        >>> # Optimize to match experimental density
        >>> optimized = optimize_lattice(crystal, target_density=2.33)
    """
    if target_density is None and target_volume is None:
        raise ValueError("Must specify either target_density or target_volume")

    if target_density is not None:
        target_density = _validate_positive_finite_scalar(
            target_density, "target_density"
        )
        # Calculate required volume from density
        # density = mass / volume
        mass = crystal.composition.mass  # in amu
        # Convert amu to grams and A^3 to cm^3
        amu_to_g = 1.66053906660e-24
        angstrom3_to_cm3 = 1e-24
        mass_g = mass * amu_to_g
        target_volume = mass_g / target_density / angstrom3_to_cm3
    else:
        target_volume = _validate_positive_finite_scalar(
            target_volume, "target_volume"
        )

    return set_volume(crystal, target_volume)


__all__ = ["scale_lattice", "set_volume", "optimize_lattice"]
