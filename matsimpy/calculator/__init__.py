"""
Calculator module for MatSimPy.

Provides calculators for computing energies, forces, and other properties.
- lj: Lennard-Jones classical potential
- vasp: VASP DFT calculator (adapted from pymatgen)
- gaussian: Gaussian calculator (adapted from pymatgen)
- lammps: LAMMPS calculator (adapted from pymatgen)
"""

from .base import Calculator
from .lj import LennardJones

__all__ = ["Calculator", "LennardJones"]
