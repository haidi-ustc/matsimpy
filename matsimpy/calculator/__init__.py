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

# ML calculators
from .ml import Mattersim, BaseML

# DFT calculators
from .dft import BaseDFT

# Category modules (for category-level imports)
from . import classical
from . import ml
from . import dft

__all__ = [
    # Base
    'Calculator',
    
    # Classical
    'LennardJones',
    
    # ML
    'Mattersim',
    'BaseML',
    
    # DFT
    'BaseDFT',
    
    # Categories
    'classical',
    'ml',
    'dft',
]
