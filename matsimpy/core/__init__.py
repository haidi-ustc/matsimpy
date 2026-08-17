"""Core domain model for MatSimPy.

This module provides the fundamental data classes:
- Lattice, Composition, Site — supporting value objects
- Structure — abstract base class
- Crystal — periodic structures with lattice
- Molecule — non-periodic structures
- Element — periodic table element data
"""

from .lattice import Lattice
from .composition import Composition
from .structure import Structure
from .molecule import Molecule
from .crystal import Crystal
from .site import Site, CrystalSite
from .periodic_table import Element
from .symmop import SymmOp
from .units import unitized

__all__ = [
    "Lattice",
    "Composition",
    "Site",
    "CrystalSite",
    "Structure",
    "Crystal",
    "Molecule",
    "Element",
    "SymmOp",
    "unitized",
]
