"""
Defect structure builders.

This module provides tools for creating defect structures:
- Point defects: Vacancies, interstitials, substitutions
- Frenkel defects: Atom displaced from site to interstitial
- Schottky defects: Pair of vacancies
- Antisite defects: Atomic swaps
"""

from .point import (
    create_vacancy,
    create_interstitial,
    create_substitution,
    create_frenkel,
    create_schottky,
    create_antisite,
)

__all__ = [
    "create_vacancy",
    "create_interstitial",
    "create_substitution",
    "create_frenkel",
    "create_schottky",
    "create_antisite",
]
