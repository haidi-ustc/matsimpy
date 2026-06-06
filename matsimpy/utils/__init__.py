"""
General-purpose utility functions for MatSimPy.

This module provides:
- validation: numeric vector/matrix/scalar validation
- dict_utils: nested dictionary access and property copying
- path_utils: filesystem path expansion
"""

from .validation import (
    validate_vector3,
    validate_positive_scalar,
    validate_integer_matrix3,
)
from .dict_utils import (
    get_nested_value,
    set_nested_value,
    copy_properties,
)
from .path_utils import expand_path

__all__ = [
    "validate_vector3",
    "validate_positive_scalar",
    "validate_integer_matrix3",
    "get_nested_value",
    "set_nested_value",
    "copy_properties",
    "expand_path",
]
