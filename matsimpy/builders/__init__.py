"""
Structure builders for MatSimPy.

This module provides comprehensive tools for building crystal and molecular structures
organized by structure type:

**bulk/**        - Bulk crystal structures
  - from_prototype(): FCC, BCC, diamond, rocksalt, etc. (9 prototypes)
  - random_crystal(): Random crystal with symmetry (PyXtal)

**surface/**     - Surface structures
  - generate_slab(): Create surface slabs with vacuum
  - add_adsorbate(): Add adsorbates to surfaces

**alloy/**       - Alloy structures
  - generate_random_alloy(): Random solid solutions
  - generate_ordered_alloy(): Ordered substitution patterns
  - generate_intermetallic(): L1_2, B2 compounds

**molecule/**    - Molecular structures
  - build_linear(): Linear molecules (CO2, etc.)
  - build_bent(): Bent molecules (H2O, etc.)
  - build_tetrahedral(): CH4-like structures
  - build_from_smiles(): From SMILES strings (RDKit)

**interface/**   - Interface structures (placeholder)

Quick Start:
    >>> from matsimpy.builders import *
    >>> 
    >>> # Build bulk structures
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    >>> si = random_crystal(3, 227, ['Si'], [8])
    >>> 
    >>> # Build surface
    >>> slab = generate_slab(fcc_cu, (1,1,1), 10, 15)
    >>> with_ads = add_adsorbate(slab, 'O', (0.5, 0.5), 2.0)
    >>> 
    >>> # Build alloy
    >>> from matsimpy.transformation.structural import make_supercell
    >>> supercell = make_supercell(fcc_cu, [4, 4, 4])
    >>> alloy = generate_random_alloy(supercell, ['Ni'], 'Cu', [0.25])
    >>> 
    >>> # Build molecules
    >>> co2 = build_linear(['O', 'C', 'O'], [1.16, 1.16])
    >>> h2o = build_bent(['O', 'H', 'H'], [0.96, 0.96], [104.5])
    >>> ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
"""

# Import all from submodules
from .bulk import *
from .surface import *
from .alloy import *
from .molecule import *

# Import submodule __all__ lists
from .bulk import __all__ as _bulk_all
from .surface import __all__ as _surface_all
from .alloy import __all__ as _alloy_all
from .molecule import __all__ as _molecule_all

# Combine all exports
__all__ = _bulk_all + _surface_all + _alloy_all + _molecule_all

# Allow access to submodules
from . import bulk
from . import surface
from . import alloy
from . import molecule
from . import interface

