"""
Structure builders for MatSimPy — constructors only.

Builders create structures from parameters/prototypes.
For modification of existing structures, see matsimpy.transformation.

Categories:
    bulk/         — from_prototype(), random_crystal()
    surface/      — generate_slab()
    molecule/     — build_linear(), build_bent(), build_tetrahedral(), build_from_smiles()
    nanostructure/ — build_nanotube(), build_carbon_nanotube(), build_twisted_bilayer(), etc.

Usage::

    >>> from matsimpy.builders import from_prototype
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
"""

# Curated top-level API
from .bulk import from_prototype
from .surface import generate_slab
from .molecule import (
    build_linear,
    build_bent,
    build_tetrahedral,
)
from .nanostructure import (
    build_nanotube,
    build_carbon_nanotube,
    build_twisted_bilayer,
    build_magic_angle_twisted,
    build_twisted_multilayer,
)

# Optional dependencies
try:
    from .bulk import random_crystal
except ImportError:
    pass

try:
    from .molecule import build_from_smiles
except ImportError:
    pass

# Registry
from .registry import registry, BuilderSpec, BuilderRegistry

# Auto-register built-in builders
from ._register import register_all as _register_builders
_register_builders()

# Allow access to submodules
from . import bulk
from . import surface
from . import molecule
from . import nanostructure

__all__ = [
    "from_prototype",
    "generate_slab",
    "build_linear",
    "build_bent",
    "build_tetrahedral",
    "build_nanotube",
    "build_carbon_nanotube",
    "build_twisted_bilayer",
    "build_magic_angle_twisted",
    "build_twisted_multilayer",
    "registry",
    "BuilderSpec",
    "BuilderRegistry",
]
