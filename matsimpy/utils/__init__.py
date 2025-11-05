"""
Utility functions and constants.

This module provides:
- Math utilities
- Physical constants
- Type hints and utilities
- Atom selection utilities
"""

# Utilities will be imported here as they are implemented
# from .math import *
# from .constants import *
# from .typing import *
from .selection import (
    select_by_species,
    select_by_indices,
    select_by_position,
    select_by_box,
    select_by_property,
    select_by_custom,
    combine_selections,
    select_all,
    select_none,
    AtomSelection,
)

__all__ = [
    # Selection utilities
    'select_by_species',
    'select_by_indices',
    'select_by_position',
    'select_by_box',
    'select_by_property',
    'select_by_custom',
    'combine_selections',
    'select_all',
    'select_none',
    'AtomSelection',
]

