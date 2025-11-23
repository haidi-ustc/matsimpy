"""
Surface structure builders.

Tools for generating surface slabs and adding adsorbates.

Examples:
    >>> from matsimpy import Crystal, Lattice
    >>> from matsimpy.builders.surface import generate_slab, add_adsorbate
    >>>
    >>> # Generate bulk
    >>> from matsimpy.builders.bulk import from_prototype
    >>> bulk = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
    >>>
    >>> # Generate (111) slab
    >>> slab = generate_slab(bulk, (1,1,1), min_slab_size=10, min_vacuum_size=15)
    >>>
    >>> # Add adsorbate
    >>> with_ads = add_adsorbate(slab, 'O', (0.5, 0.5), height=2.0)
"""

from .slab import generate_slab, generate_symmetric_slab
from .adsorbate import add_adsorbate

__all__ = ["generate_slab", "generate_symmetric_slab", "add_adsorbate"]
