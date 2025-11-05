"""
Mathematical utilities.
"""

import numpy as np
from typing import List, Tuple

def norm(vector: np.ndarray) -> float:
    """Calculate vector norm."""
    return np.linalg.norm(vector)

def angle(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate angle between two vectors in degrees."""
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Handle numerical errors
    return np.degrees(np.arccos(cos_angle))

def distance(p1: np.ndarray, p2: np.ndarray) -> float:
    """Calculate distance between two points."""
    return np.linalg.norm(p2 - p1)

__all__ = ['norm', 'angle', 'distance']

