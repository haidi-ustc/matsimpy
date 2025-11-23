"""
Lattice operations (strain, scale, transform).

Crystal-specific operations for lattice manipulation.
"""

from .strain import apply_strain, apply_deformation
from .scale import scale_lattice, set_volume, optimize_lattice
from .transform import (
    rotate_lattice,
    transform_lattice,
    get_niggli_reduced,
    standardize_cell,
)

__all__ = [
    # Strain
    "apply_strain",
    "apply_deformation",
    # Scale
    "scale_lattice",
    "set_volume",
    "optimize_lattice",
    # Transform
    "rotate_lattice",
    "transform_lattice",
    "get_niggli_reduced",
    "standardize_cell",
]
