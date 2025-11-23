"""
Utility functions for MatSimPy.

This module provides atom selection utilities for flexible atom selection
in Crystal and Molecule structures.
"""

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
    "select_by_species",
    "select_by_indices",
    "select_by_position",
    "select_by_box",
    "select_by_property",
    "select_by_custom",
    "combine_selections",
    "select_all",
    "select_none",
    "AtomSelection",
]
