"""
Alloy structure builders.

Tools for generating various types of alloy structures:
- random: Random solid solution alloys
- ordered: Ordered intermetallic compounds
- heusler: Heusler alloy structures (full, half, inverse)

Examples:
    >>> from matsimpy import Crystal, Lattice
    >>> from matsimpy.builders.alloy import generate_random_alloy, generate_intermetallic
    >>> from matsimpy.builders.alloy import build_heusler, build_full_heusler
    >>> from matsimpy.builders.bulk import from_prototype
    >>> from matsimpy.transformation.structural import make_supercell
    >>>
    >>> # Generate FCC base
    >>> base = from_prototype('fcc', 'Al', 4.05)
    >>> supercell = make_supercell(base, [4, 4, 4])
    >>>
    >>> # Create random Al-Cu alloy
    >>> alloy = generate_random_alloy(supercell, ['Cu'], 'Al', [0.25])
    >>>
    >>> # Create ordered L1_2 structure
    >>> ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)
    >>>
    >>> # Create full Heusler alloy
    >>> cu2mnal = build_full_heusler('Cu', 'Mn', 'Al', 5.95)
    >>> # Or use generic function
    >>> nimnsb = build_heusler('Ni', 'Mn', 'Sb', 5.93, 'half')
"""

from .random import generate_random_alloy
from .ordered import generate_ordered_alloy, generate_intermetallic
from .heusler import (
    build_heusler,
    build_full_heusler,
    build_half_heusler,
    build_inverse_heusler,
)

__all__ = [
    "generate_random_alloy",
    "generate_ordered_alloy",
    "generate_intermetallic",
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
]
