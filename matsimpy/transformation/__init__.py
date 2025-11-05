"""
Structure transformation tools.

This module provides comprehensive transformations for Crystal and Molecule objects
organized into categories:

**Geometric** (Translation, Rotation):
- Works for both Crystal and Molecule
- translate, translate_to_origin
- rotate, rotate_around_axis

**Lattice** (Strain, Scale, Transform):
- Crystal-specific lattice operations
- apply_strain, apply_deformation
- scale_lattice, set_volume, optimize_lattice
- rotate_lattice, transform_lattice, standardize_cell

**Atomic** (Manipulation, Organization):
- Works for both Crystal and Molecule
- move_atoms, swap_atoms, merge_atoms, split_atom
- sort_atoms, center_structure, perturb_positions

**Chemical** (Substitution):
- Works for both Crystal and Molecule
- substitute, substitute_all

**Structural** (Supercell, Molecular):
- make_supercell (Crystal)
- fragment_molecule, align_molecules, merge_molecules (Molecule)

Usage:
    # Functional style (returns new object)
    >>> from matsimpy.transformation import translate, rotate, apply_strain
    >>> new_molecule = translate(molecule, [1, 1, 1])
    >>> rotated = rotate(new_molecule, 90, [0, 0, 1])
    >>> strained = apply_strain(crystal, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
    
    # In-place (modifies existing)
    >>> translate(molecule, [1, 1, 1], inplace=True)
    
    # Lattice operations
    >>> from matsimpy.transformation.lattice import scale_lattice
    >>> scaled = scale_lattice(crystal, 1.1)
    
    # Atom operations
    >>> from matsimpy.transformation.atomic import move_atoms, sort_atoms
    >>> moved = move_atoms(crystal, [0, 1], [0.1, 0, 0])
    >>> sorted_struct = sort_atoms(crystal, key='species')
    
    # Molecular operations
    >>> from matsimpy.transformation.structural import align_molecules
    >>> aligned = align_molecules(mol1, mol2, [0,1,2], [0,1,2])
"""

# Import from geometric
from .geometric import *
from .geometric import __all__ as _geometric_all

# Import from lattice
from .lattice import *
from .lattice import __all__ as _lattice_all

# Import from atomic
from .atomic import *
from .atomic import __all__ as _atomic_all

# Import from chemical
from .chemical import *
from .chemical import __all__ as _chemical_all

# Import from structural
from .structural import *
from .structural import __all__ as _structural_all

# Import composite operations
from .composite import chain, apply_transformations

# Combine all exports
__all__ = (
    _geometric_all + 
    _lattice_all + 
    _atomic_all + 
    _chemical_all + 
    _structural_all +
    ['chain', 'apply_transformations']
)

# Allow direct access to submodules
from . import geometric
from . import lattice
from . import atomic
from . import chemical
from . import structural
from . import base
from . import composite
