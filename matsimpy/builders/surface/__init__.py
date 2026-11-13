"""
Surface structure builders.

Tools for generating surface slabs and adding adsorbates.

Examples:
    >>> from matsimpy.builders.surface import generate_slab, add_adsorbate
    >>> from matsimpy.core import Crystal, Lattice
    >>>
    >>> # Miller indices refer to the bulk cell given: use the conventional cell
    >>> si = Crystal(['Si'] * 8, [[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0],
    ...                           [0.25, 0.25, 0.25], [0.25, 0.75, 0.75], [0.75, 0.25, 0.75],
    ...                           [0.75, 0.75, 0.25]], Lattice.cubic(5.43))
    >>> slab = generate_slab(si, (1, 1, 1), min_slab_size=10, min_vacuum_size=15)
    >>> with_h = add_adsorbate(slab, 'H', (0, 0), height=1.5)
"""

from .slab import generate_slab, generate_symmetric_slab
from .adsorbate import add_adsorbate

__all__ = ["generate_slab", "generate_symmetric_slab", "add_adsorbate"]
