"""
Type hints and typing utilities.

Common type aliases for the package.
"""

from typing import List, Tuple, Union, Optional, Dict
import numpy as np
from numpy.typing import NDArray

# Type aliases
Vector3D = Union[List[float], Tuple[float, float, float], NDArray[np.float64]]
Matrix3x3 = Union[List[List[float]], NDArray[np.float64]]
Species = Union[str, int, List[str], List[int]]

__all__ = ['Vector3D', 'Matrix3x3', 'Species']

