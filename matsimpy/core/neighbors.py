"""Neighbor-search helpers for MatSimPy.

This module centralizes fixed-radius periodic neighbor lookup so runtime code
does not depend directly on third-party neighbor modules.
"""

import math
from typing import Tuple

import numpy as np


def validate_cutoff(cutoff, *, allow_zero=True):
    """Validate a neighbor-list cutoff radius.

    Args:
        cutoff: The cutoff value to validate.
        allow_zero: Whether zero-radius queries are permitted.

    Returns:
        float: The validated cutoff.

    Raises:
        ValueError: If cutoff is negative, NaN, or infinite.
        TypeError: If cutoff is not numeric.
    """
    if not isinstance(cutoff, (int, float, np.integer, np.floating)):
        raise TypeError(f"cutoff must be a number, got {type(cutoff).__name__}")
    value = float(cutoff)
    if math.isnan(value):
        raise ValueError("cutoff must not be NaN")
    if math.isinf(value):
        raise ValueError("cutoff must be finite")
    if value < 0:
        raise ValueError(f"cutoff must be non-negative, got {value}")
    if value == 0 and not allow_zero:
        raise ValueError("cutoff must be positive, got 0")
    return value


def find_points_in_spheres(
    center_coords: np.ndarray,
    all_coords: np.ndarray,
    r: float,
    pbc: np.ndarray,
    lattice: np.ndarray,
    tol: float = 1e-8,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Find all points within fixed-radius spheres.

    This returns the same tuple shape used by MatterSim/PyMatGen neighbor
    utilities: center indices, neighbor indices, integer image offsets, and
    distances. When PyMatGen is available, MatSimPy delegates to its optimized
    implementation to preserve MatterSim graph ordering. A pure NumPy fallback
    keeps the API usable without PyMatGen.
    """
    try:
        from pymatgen.optimization.neighbors import (
            find_points_in_spheres as _pymatgen_find_points_in_spheres,
        )
    except ImportError:
        return _find_points_in_spheres_numpy(
            center_coords=center_coords,
            all_coords=all_coords,
            r=r,
            pbc=pbc,
            lattice=lattice,
            tol=tol,
        )

    return _pymatgen_find_points_in_spheres(
        np.ascontiguousarray(center_coords, dtype=float),
        np.ascontiguousarray(all_coords, dtype=float),
        r=float(r),
        pbc=np.array(pbc, dtype=np.int64),
        lattice=np.ascontiguousarray(lattice, dtype=float),
        tol=tol,
    )


def _find_points_in_spheres_numpy(
    center_coords: np.ndarray,
    all_coords: np.ndarray,
    r: float,
    pbc: np.ndarray,
    lattice: np.ndarray,
    tol: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    center_coords = np.ascontiguousarray(center_coords, dtype=float)
    all_coords = np.ascontiguousarray(all_coords, dtype=float)
    pbc = np.array(pbc, dtype=bool)
    lattice = np.ascontiguousarray(lattice, dtype=float)

    image_ranges = _periodic_image_ranges(lattice, pbc, r)
    center_indices = []
    neighbor_indices = []
    images = []
    distances = []

    for image in image_ranges:
        shift = np.dot(image, lattice)
        for center_index, center in enumerate(center_coords):
            deltas = all_coords + shift - center
            dists = np.linalg.norm(deltas, axis=1)
            matches = np.where(dists <= r + tol)[0]
            for neighbor_index in matches:
                center_indices.append(center_index)
                neighbor_indices.append(int(neighbor_index))
                images.append(image.copy())
                distances.append(float(dists[neighbor_index]))

    return (
        np.array(center_indices, dtype=np.int64),
        np.array(neighbor_indices, dtype=np.int64),
        np.array(images, dtype=np.int64).reshape(-1, 3),
        np.array(distances, dtype=float),
    )


def _periodic_image_ranges(
    lattice: np.ndarray, pbc: np.ndarray, cutoff: float
) -> np.ndarray:
    inv_matrix = np.linalg.inv(lattice)
    ranges = []
    for axis, periodic in enumerate(pbc):
        if not periodic:
            ranges.append(np.array([0], dtype=np.int64))
            continue
        plane_spacing = 1.0 / np.linalg.norm(inv_matrix[:, axis])
        n_images = int(np.ceil(cutoff / plane_spacing)) + 1
        ranges.append(np.arange(-n_images, n_images + 1, dtype=np.int64))

    return np.array(
        [[i, j, k] for i in ranges[0] for j in ranges[1] for k in ranges[2]],
        dtype=np.int64,
    )


__all__ = ["find_points_in_spheres", "validate_cutoff"]
