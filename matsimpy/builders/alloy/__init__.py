"""
Alloy structure builders.

Tools for generating various types of alloy structures:
- random: Random solid solution alloys
- ordered: Ordered intermetallic compounds

Examples:
    >>> from matsimpy import Crystal, Lattice
    >>> from matsimpy.builders.alloy import generate_random_alloy, generate_intermetallic
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
"""

from .random import generate_random_alloy
from .ordered import generate_ordered_alloy, generate_intermetallic

__all__ = [
    'generate_random_alloy',
    'generate_ordered_alloy',
    'generate_intermetallic',
]

