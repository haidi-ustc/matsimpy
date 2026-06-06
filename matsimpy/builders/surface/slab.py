"""
Surface slab generation.

Generate surface slabs from bulk structures with various Miller indices,
vacuum spacing, and terminations.
"""

from typing import Tuple, Optional
import numpy as np
from ...core import Crystal, Lattice


def generate_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: float,
    min_vacuum_size: float,
    layers: Optional[int] = None,
    center_slab: bool = True,
    **kwargs,
) -> Crystal:
    """
    Generate a surface slab from a bulk crystal structure.

    Args:
        bulk: Bulk crystal structure
        miller_index: Miller indices of surface plane (h, k, l)
        min_slab_size: Minimum slab thickness in Angstroms
        min_vacuum_size: Minimum vacuum spacing in Angstroms
        layers: Number of atomic layers (alternative to min_slab_size)
        center_slab: Center the slab in the cell
        **kwargs: Additional parameters

    Returns:
        Crystal: Slab structure with vacuum

    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.builders.surface import generate_slab
        >>> from matsimpy.builders.bulk import from_prototype
        >>> bulk = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
        >>> slab = generate_slab(bulk, (1,0,0), min_slab_size=10, min_vacuum_size=15)
        >>> slab = generate_slab(bulk, (1,1,1), layers=5, min_vacuum_size=15)
    """
    if not isinstance(bulk, Crystal):
        raise TypeError("bulk must be a Crystal")
    h, k, l = miller_index
    if h == 0 and k == 0 and l == 0:
        raise ValueError("Miller index cannot be (0, 0, 0)")
    if min_slab_size <= 0:
        raise ValueError("min_slab_size must be positive")
    if min_vacuum_size < 0:
        raise ValueError("min_vacuum_size must be non-negative")
    if layers is not None and layers <= 0:
        raise ValueError("layers must be positive")

    lattice_matrix = bulk.lattice.lattice_vectors
    hkl = np.array([h, k, l], dtype=int)
    normal = np.linalg.solve(lattice_matrix, hkl.astype(np.float64))
    normal = normal / np.linalg.norm(normal)

    d_spacing = 1.0 / np.linalg.norm(np.linalg.solve(lattice_matrix, hkl.astype(np.float64)))
    if layers is None:
        layers = max(2, int(np.ceil(min_slab_size / d_spacing)))
    slab_thickness = max(layers * d_spacing, min_slab_size)
    total_normal_length = slab_thickness + min_vacuum_size

    u, v = _miller_plane_basis(hkl)
    a_vec = u @ lattice_matrix
    b_vec = v @ lattice_matrix
    slab_lattice_vectors = np.array(
        [a_vec, b_vec, normal * total_normal_length],
        dtype=np.float64,
    )
    selection_lattice_vectors = np.array(
        [a_vec, b_vec, normal * slab_thickness],
        dtype=np.float64,
    )

    new_lattice = Lattice(slab_lattice_vectors)
    inv_selection_lattice = np.linalg.inv(selection_lattice_vectors)

    new_species = []
    new_positions = []
    slab_fraction = slab_thickness / total_normal_length
    z_offset = (min_vacuum_size / total_normal_length / 2.0) if center_slab else 0.0

    search_radius = int(max(np.max(np.abs(u)), np.max(np.abs(v)), np.max(np.abs(hkl)), layers) + 3)
    seen = set()
    tol = 1e-8
    for i in range(-search_radius, search_radius + 1):
        for j in range(-search_radius, search_radius + 1):
            for k_shift in range(-search_radius, search_radius + 1):
                shift = np.array([i, j, k_shift], dtype=np.float64)
                for spec, frac_pos in zip(bulk.species, bulk.frac_positions):
                    cart = (frac_pos + shift) @ lattice_matrix
                    slab_frac = cart @ inv_selection_lattice
                    if (
                        -tol <= slab_frac[0] < 1.0 - tol
                        and -tol <= slab_frac[1] < 1.0 - tol
                        and -tol <= slab_frac[2] < 1.0 - tol
                    ):
                        final_frac = slab_frac.copy()
                        final_frac[0] = final_frac[0] % 1.0
                        final_frac[1] = final_frac[1] % 1.0
                        final_frac[2] = final_frac[2] * slab_fraction + z_offset
                        key = tuple(np.round(final_frac, 8)) + (spec,)
                        if key in seen:
                            continue
                        seen.add(key)
                        new_species.append(spec)
                        new_positions.append(final_frac.tolist())

    if not new_positions:
        raise ValueError(f"Failed to generate slab for Miller index {miller_index}")

    slab_crystal = Crystal(new_species, new_positions, new_lattice, pbc=[True, True, False])

    c_vec = new_lattice.lattice_vectors[2]
    c_norm = np.linalg.norm(c_vec)
    normal = c_vec / c_norm
    cart_positions = slab_crystal.cart_positions
    projections = np.dot(cart_positions, normal)
    projected_thickness = float(np.max(projections) - np.min(projections))
    vacuum_thickness = c_norm - projected_thickness
    if vacuum_thickness < min_vacuum_size - 1e-6:
        raise ValueError(
            f"Slab vacuum thickness {vacuum_thickness:.3f} is less than "
            f"requested minimum {min_vacuum_size:.3f}"
        )

    return slab_crystal


def _miller_plane_basis(hkl: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return two reduced integer vectors lying in the Miller plane."""
    h, k, l = [int(value) for value in hkl]
    if h == 0 and k == 0:
        u = np.array([1, 0, 0], dtype=int)
    else:
        u = np.array([k, -h, 0], dtype=int)
    v = np.cross(hkl, u).astype(int)
    return _reduce_integer_vector(u), _reduce_integer_vector(v)


def _reduce_integer_vector(vector: np.ndarray) -> np.ndarray:
    values = [abs(int(value)) for value in vector if int(value) != 0]
    if not values:
        return vector
    divisor = values[0]
    for value in values[1:]:
        divisor = int(np.gcd(divisor, value))
    if divisor > 1:
        vector = vector // divisor
    first_nonzero = next((int(value) for value in vector if int(value) != 0), 1)
    if first_nonzero < 0:
        vector = -vector
    return vector


def generate_symmetric_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: float,
    min_vacuum_size: float,
    **kwargs,
) -> Crystal:
    """
    Generate a symmetric slab (same termination on both surfaces).

    Args:
        bulk: Bulk crystal structure
        miller_index: Miller indices (h, k, l)
        min_slab_size: Minimum slab thickness in Angstroms
        min_vacuum_size: Minimum vacuum spacing in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Symmetric slab structure

    Examples:
        >>> from matsimpy.builders.surface import generate_symmetric_slab
        >>> slab = generate_symmetric_slab(bulk, (1,1,0), 15, 10)
    """
    slab = generate_slab(
        bulk, miller_index, min_slab_size, min_vacuum_size, center_slab=True, **kwargs
    )

    return slab


__all__ = ["generate_slab", "generate_symmetric_slab"]
