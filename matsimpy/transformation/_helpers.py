"""Internal helpers shared by transformation functions."""

from __future__ import annotations

import copy
from typing import Iterable, Optional, Sequence, Union

import numpy as np

from ..core import Crystal, Molecule


Structure = Union[Crystal, Molecule]


def copy_site_properties(structure: Structure) -> Optional[list[dict]]:
    """Return deep-copied site properties, or ``None`` when absent."""
    props = getattr(structure, "site_properties", ())
    if not props:
        return None
    return [copy.deepcopy(prop) for prop in props]


def site_properties_for_indices(
    structure: Structure, indices: Iterable[int]
) -> Optional[list[dict]]:
    """Return deep-copied site properties reindexed by ``indices``."""
    props = getattr(structure, "site_properties", ())
    if not props:
        return None
    return [copy.deepcopy(props[int(index)]) for index in indices]


def repeated_site_properties_for_index(
    structure: Structure, index: int, count: int
) -> Optional[list[dict]]:
    """Return ``count`` copies of one site's properties, or ``None`` when absent."""
    props = getattr(structure, "site_properties", ())
    if not props:
        return None
    return [copy.deepcopy(props[index]) for _ in range(count)]


def rebuild_structure(
    source: Structure,
    species: Sequence[str],
    positions: Sequence[Sequence[float]],
    *,
    lattice=None,
    coords_are_cartesian: bool = False,
    pbc: Optional[Sequence[bool]] = None,
    site_properties: Optional[Sequence[dict]] = None,
) -> Structure:
    """Rebuild a structure while preserving source-level invariants by default."""
    if isinstance(source, Crystal):
        return Crystal(
            list(species),
            positions,
            lattice=lattice if lattice is not None else source.lattice,
            coords_are_cartesian=coords_are_cartesian,
            pbc=list(pbc if pbc is not None else source.pbc),
            site_properties=site_properties,
        )

    return Molecule(
        list(species),
        positions,
        site_properties=site_properties,
    )


def validate_vector3(name: str, value: Union[Sequence[float], np.ndarray]) -> np.ndarray:
    """Validate and return a finite 3-vector."""
    vector = np.array(value, dtype=np.float64)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite 3-vector")
    return vector


def validate_positive_scalar(name: str, value: float) -> float:
    """Validate and return a finite non-negative scalar."""
    scalar = float(value)
    if not np.isfinite(scalar) or scalar < 0:
        raise ValueError(f"{name} must be a finite non-negative scalar")
    return scalar


def validate_integer_matrix3(
    name: str,
    value: Union[Sequence[Sequence[int]], np.ndarray],
    *,
    positive_determinant: bool = False,
) -> np.ndarray:
    """Validate and return a 3x3 integer matrix."""
    matrix = np.array(value, dtype=np.float64)
    if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must be a finite 3x3 matrix")
    rounded = np.rint(matrix)
    if not np.allclose(matrix, rounded):
        raise ValueError(f"{name} must contain integer values")
    matrix = rounded.astype(np.int64)
    if positive_determinant and round(np.linalg.det(matrix)) <= 0:
        raise ValueError(f"{name} must have positive determinant")
    return matrix
