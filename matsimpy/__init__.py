"""
MatSimPy - Materials Simulation in Python

A comprehensive package for materials simulation and analysis.
"""

# Core modules
from .core import (
    Structure,
    Crystal,
    Molecule,
    Lattice,
    Composition,
    Site,
    CrystalSite,
    Element,
)

# Constants
from .constants import POSITION_TOL, LATTICE_TOL

# Version
__version__ = "0.3.0"

__all__ = [
    # Core classes
    "Structure",
    "Crystal",
    "Molecule",
    "Lattice",
    "Composition",
    "Site",
    "CrystalSite",
    "Element",
    # Constants
    "POSITION_TOL",
    "LATTICE_TOL",
    # Version
    "__version__",
]
