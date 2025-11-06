"""
Classical potential calculators.

These calculators compute energies and forces using classical/semi-classical
potential functions without requiring external programs or ML models.
"""

from .lennard_jones import LennardJones

__all__ = [
    'LennardJones',
]

