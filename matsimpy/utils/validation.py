"""General-purpose numeric validation helpers."""

from __future__ import annotations

from typing import Sequence, Union

import numpy as np


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


__all__ = ["validate_vector3", "validate_positive_scalar", "validate_integer_matrix3"]
