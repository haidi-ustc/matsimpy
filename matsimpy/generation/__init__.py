"""
Structure generation tools.

This module provides comprehensive structure generation capabilities organized into:

**Methods** (Generation Strategies):
- random: Random crystal generation with symmetry constraints
- symmetry: Space group and point group based generation
- template: Prototype-based generation (FCC, BCC, perovskite, etc.)
- ai: Machine learning based generation (VAE, GAN, diffusion models)

**Builders** (Specific Structure Types):
- slab: Surface structures with vacuum
- interface: Heterostructures, grain boundaries, multilayers
- alloy: Random, ordered, and SQS alloys
- molecule: Molecule-specific builders

Example:
    >>> from matsimpy.generation import from_prototype, generate_slab, generate_random_alloy
    >>> 
    >>> # Generate from prototype
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    >>> 
    >>> # Generate surface slab
    >>> slab = generate_slab(bulk, (1,1,1), min_slab_size=10, min_vacuum_size=15)
    >>> 
    >>> # Generate random alloy
    >>> alloy = generate_random_alloy(base, ['Cu'], 'Al', [0.5])
    >>> 
    >>> # Build molecule
    >>> from matsimpy.generation.builders import build_linear_molecule
    >>> co2 = build_linear_molecule(['O', 'C', 'O'], [1.16, 1.16])
"""

# Import from methods
from .methods import *
from .methods import __all__ as _methods_all

# Import from builders
from .builders import *
from .builders import __all__ as _builders_all

# Combine all exports
__all__ = _methods_all + _builders_all

# Allow direct access to submodules
from . import methods
from . import builders
