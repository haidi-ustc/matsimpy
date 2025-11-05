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
    Element
)

# Version
__version__ = "0.1.0"

__all__ = [
    # Core classes
    'Structure',
    'Crystal',
    'Molecule',
    'Lattice',
    'Composition',
    'Site',
    'CrystalSite',
    'Element',
    # Version
    '__version__',
]

