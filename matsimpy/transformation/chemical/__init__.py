"""
Chemical transformations (substitution).

Works for both Crystal and Molecule structures.
"""

from .substitution import substitute, substitute_all
from .alloy_random import generate_random_alloy
from .alloy_ordered import generate_ordered_alloy, generate_intermetallic
from .alloy_heusler import (
    build_heusler,
    build_full_heusler,
    build_half_heusler,
    build_inverse_heusler,
)

__all__ = [
    "substitute",
    "substitute_all",
    "generate_random_alloy",
    "generate_ordered_alloy",
    "generate_intermetallic",
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
]
