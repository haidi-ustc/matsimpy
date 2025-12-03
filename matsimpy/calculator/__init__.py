"""
Calculator module for MatSimPy.

Provides calculators for computing energies, forces, and other properties
of crystal and molecular structures.

Organized by calculator type:
- classical: Classical potential calculators (Lennard-Jones, etc.)
- ml: Machine learning potential calculators (Mattersim, MACE, etc.)
- dft: DFT calculators (VASP, Quantum Espresso, etc.)

Usage:
    # Direct import (backward compatible)
    >>> from matsimpy.calculator import LennardJones, Mattersim

    # Category import (recommended)
    >>> from matsimpy.calculator.classical import LennardJones
    >>> from matsimpy.calculator.ml import Mattersim

    # Category module import
    >>> from matsimpy.calculator import classical, ml
    >>> calc1 = classical.LennardJones(...)
    >>> calc2 = ml.Mattersim(...)
"""

# Base class
from .base import Calculator

# Classical calculators
from .classical import LennardJones

# ML calculators - use try/except to handle missing torch dependencies
try:
    from .ml import Mattersim, BaseML

    _ml_available = True
except (ImportError, ModuleNotFoundError):
    # If torch or other ML dependencies are not available, set to None
    Mattersim = None
    BaseML = None
    _ml_available = False

# DFT calculators
from .dft import BaseDFT

# Category modules (for category-level imports)
from . import classical

# ML module import - use try/except to handle missing torch dependencies
try:
    from . import ml
except (ImportError, ModuleNotFoundError):
    # If torch or other ML dependencies are not available, create a dummy module
    import types

    ml = types.ModuleType("ml")
    ml.__all__ = []
from . import dft

__all__ = [
    # Base
    "Calculator",
    # Classical
    "LennardJones",
    # ML (may be None if dependencies not available)
    "Mattersim",
    "BaseML",
    # DFT
    "BaseDFT",
    # Categories
    "classical",
    "ml",
    "dft",
]
