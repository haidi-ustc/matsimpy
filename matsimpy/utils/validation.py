"""General-purpose numeric validation helpers."""

from __future__ import annotations

from typing import Sequence, Union

import numpy as np


def _reject_bools(name: str, value) -> None:
    """Raise TypeError if *value* is, or contains, a bool (``True`` is not ``1.0``)."""
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be numeric, got bool")
    if isinstance(value, np.ndarray):
        if value.dtype == bool:
            raise TypeError(f"{name} must be numeric, got a boolean array")
        if value.dtype != object:
            return
    if isinstance(value, (list, tuple, np.ndarray)):
        try:
            flat = np.ravel(np.asarray(value, dtype=object))
        except (TypeError, ValueError):
            return
        if any(isinstance(v, (bool, np.bool_)) for v in flat):
            raise TypeError(f"{name} must be numeric, got bool")


def validate_vector3(name: str, value: Union[Sequence[float], np.ndarray]) -> np.ndarray:
    """Validate and return a finite 3-vector."""
    _reject_bools(name, value)
    vector = np.array(value, dtype=np.float64)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite 3-vector")
    return vector


def validate_positive_scalar(name: str, value: float) -> float:
    """Validate and return a finite non-negative scalar."""
    _reject_bools(name, value)
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
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
    _reject_bools(name, value)
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


def validate_matrix3(name: str, value: Union[Sequence[Sequence[float]], np.ndarray]) -> np.ndarray:
    """Validate and return a finite real 3x3 matrix (bools rejected)."""
    _reject_bools(name, value)
    try:
        matrix = np.array(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite 3x3 matrix: {exc}") from None
    if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must be a finite 3x3 matrix, got shape {matrix.shape}")
    return matrix


__all__ = ["validate_matrix3", "validate_vector3", "validate_positive_scalar", "validate_integer_matrix3"]
