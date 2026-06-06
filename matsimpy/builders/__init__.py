"""
Structure builders for MatSimPy.

Builders create structures from parameters/prototypes or modify existing
structures using transformation operations internally. No code duplication
with matsimpy.transformation.

Categories:
    bulk/         — from_prototype(), random_crystal()
    surface/      — generate_slab(), add_adsorbate()
    alloy/        — generate_random_alloy(), build_heusler(), etc.
    molecule/     — build_linear(), build_bent(), build_tetrahedral(), build_from_smiles()
    defects/      — create_vacancy(), create_interstitial(), etc.
    interface/    — create_simple_interface()
    nanostructure/ — build_nanotube(), build_carbon_nanotube(), build_twisted_bilayer(), etc.

Usage::

    >>> from matsimpy.builders import from_prototype, create_vacancy
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    >>> vac = create_vacancy(fcc_cu, 0)
"""

# Curated top-level API — constructors
from .bulk import from_prototype
from .surface import generate_slab, add_adsorbate
from .alloy import (
    generate_random_alloy,
    generate_ordered_alloy,
    generate_intermetallic,
    build_heusler,
    build_full_heusler,
    build_half_heusler,
    build_inverse_heusler,
)
from .molecule import (
    build_linear,
    build_bent,
    build_tetrahedral,
)
from .defects import (
    create_vacancy,
    create_interstitial,
    create_substitution,
    create_frenkel,
    create_schottky,
    create_antisite,
)
from .interface import create_simple_interface
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
from . import alloy
from . import molecule
from . import defects
from . import interface
from . import nanostructure

__all__ = [
    "from_prototype",
    "generate_slab",
    "add_adsorbate",
    "generate_random_alloy",
    "generate_ordered_alloy",
    "generate_intermetallic",
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
    "build_linear",
    "build_bent",
    "build_tetrahedral",
    "create_vacancy",
    "create_interstitial",
    "create_substitution",
    "create_frenkel",
    "create_schottky",
    "create_antisite",
    "create_simple_interface",
    "build_nanotube",
    "build_carbon_nanotube",
    "build_twisted_bilayer",
    "build_magic_angle_twisted",
    "build_twisted_multilayer",
    "registry",
    "BuilderSpec",
    "BuilderRegistry",
]
