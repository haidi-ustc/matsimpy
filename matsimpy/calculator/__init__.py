"""
Calculator module for MatSimPy.

Provides calculators for computing energies, forces, and other properties.
- lj: Lennard-Jones classical potential
- mattersim: MatterSim ML potential (requires torch)
- vasp: VASP DFT calculator (adapted from pymatgen)
- gaussian: Gaussian calculator (adapted from pymatgen)
- lammps: LAMMPS calculator (adapted from pymatgen)
"""

from .base import Calculator
from .lj import LennardJones

# Lazy import for MatterSim (torch optional)
try:
    from .mattersim import Mattersim
    _has_mattersim = True
except ImportError:
    Mattersim = None
    _has_mattersim = False

# VASP, Gaussian, LAMMPS — always available (IO-only, no external binary required)
from .vasp import VaspCalculator
from .gaussian import GaussianCalculator
from .lammps import LammpsCalculator

__all__ = [
    "Calculator",
    "LennardJones",
    "Mattersim",
    "VaspCalculator",
    "GaussianCalculator",
    "LammpsCalculator",
]
