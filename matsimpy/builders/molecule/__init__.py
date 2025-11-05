"""
Molecule structure builders.

Tools for building molecular structures:
- geometry: Build by geometry (linear, bent, tetrahedral, etc.)
- smiles: Build from SMILES strings

Examples:
    >>> from matsimpy.builders.molecule import build_linear, build_bent, build_tetrahedral
    >>> 
    >>> # Build CO2 (linear)
    >>> co2 = build_linear(['O', 'C', 'O'], [1.16, 1.16])
    >>> 
    >>> # Build H2O (bent)
    >>> h2o = build_bent(['O', 'H', 'H'], [0.96, 0.96], [104.5])
    >>> 
    >>> # Build CH4 (tetrahedral)
    >>> ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
    >>> 
    >>> # Build from SMILES (requires RDKit)
    >>> # from matsimpy.builders.molecule import build_from_smiles
    >>> # benzene = build_from_smiles('c1ccccc1')
"""

from .geometry import build_linear, build_bent, build_trigonal_planar, build_tetrahedral
from .smiles import build_from_smiles

__all__ = [
    'build_linear',
    'build_bent',
    'build_trigonal_planar',
    'build_tetrahedral',
    'build_from_smiles',
]

