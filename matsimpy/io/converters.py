"""
Converters for interoperability with pymatgen and ASE.

This module provides functions to convert MatSimPy structures to and from
pymatgen and ASE format objects, enabling interoperability with these popular
libraries.
"""

from typing import Optional, Union
import numpy as np

from ..core import Crystal, Molecule, Lattice


def to_pymatgen(structure: Union[Crystal, Molecule]):
    """
    Convert MatSimPy structure to pymatgen Structure or Molecule.
    
    Args:
        structure: MatSimPy Crystal or Molecule object
        
    Returns:
        pymatgen.core.Structure or pymatgen.core.structure.Molecule
        
    Raises:
        ImportError: If pymatgen is not installed
        ValueError: If structure type is not supported
    """
    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError:
        raise ImportError(
            "pymatgen is required for conversion. Install with: pip install pymatgen"
        )
    
    if isinstance(structure, Crystal):
        # Convert Crystal to pymatgen Structure
        species = list(structure.species)
        positions = structure.cart_positions.tolist()
        
        # Get lattice matrix
        lattice_matrix = structure.lattice.matrix
        
        # Create pymatgen Structure
        pymatgen_structure = PymatgenStructure(
            lattice_matrix,
            species,
            positions,
            coords_are_cartesian=True
        )
        
        return pymatgen_structure
    
    elif isinstance(structure, Molecule):
        # Convert Molecule to pymatgen Molecule
        species = list(structure.species)
        positions = structure.positions.tolist()
        
        # Create pymatgen Molecule
        pymatgen_molecule = PymatgenMolecule(species, positions)
        
        return pymatgen_molecule
    
    else:
        raise ValueError(f"Unsupported structure type: {type(structure)}")


def from_pymatgen(pymatgen_obj):
    """
    Convert pymatgen Structure or Molecule to MatSimPy structure.
    
    Args:
        pymatgen_obj: pymatgen.core.Structure or pymatgen.core.structure.Molecule
        
    Returns:
        Crystal or Molecule: MatSimPy structure object
        
    Raises:
        ImportError: If pymatgen is not installed
        ValueError: If object type is not supported
    """
    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError:
        raise ImportError(
            "pymatgen is required for conversion. Install with: pip install pymatgen"
        )
    
    if isinstance(pymatgen_obj, PymatgenStructure):
        # Convert pymatgen Structure to Crystal
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        
        # Get cartesian positions
        positions = pymatgen_obj.cart_coords.tolist()
        
        # Get lattice
        lattice_matrix = pymatgen_obj.lattice.matrix
        lattice = Lattice(lattice_matrix)
        
        # Create Crystal
        crystal = Crystal(
            species,
            positions,
            lattice,
            coords_are_cartesian=True
        )
        
        return crystal
    
    elif isinstance(pymatgen_obj, PymatgenMolecule):
        # Convert pymatgen Molecule to MatSimPy Molecule
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        positions = pymatgen_obj.cart_coords.tolist()
        
        # Create Molecule
        molecule = Molecule(species, positions)
        
        return molecule
    
    else:
        raise ValueError(
            f"Unsupported pymatgen object type: {type(pymatgen_obj)}. "
            "Expected Structure or Molecule."
        )


def to_ase(structure: Union[Crystal, Molecule]):
    """
    Convert MatSimPy structure to ASE Atoms object.
    
    Args:
        structure: MatSimPy Crystal or Molecule object
        
    Returns:
        ase.Atoms: ASE Atoms object
        
    Raises:
        ImportError: If ASE is not installed
        ValueError: If structure type is not supported
    """
    try:
        from ase import Atoms
    except ImportError:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install ase"
        )
    
    # Get species and positions
    symbols = list(structure.species)
    
    # For crystals, use cartesian positions; for molecules use positions directly
    if isinstance(structure, Crystal):
        positions = structure.cart_positions.tolist()
    else:
        positions = structure.positions.tolist()
    
    # Create ASE Atoms
    if isinstance(structure, Crystal):
        # For crystals, include cell information
        cell = structure.lattice.matrix
        pbc = structure.pbc
        
        ase_atoms = Atoms(
            symbols=symbols,
            positions=positions,
            cell=cell,
            pbc=pbc
        )
    else:
        # For molecules, no cell
        ase_atoms = Atoms(
            symbols=symbols,
            positions=positions
        )
    
    return ase_atoms


def from_ase(ase_atoms):
    """
    Convert ASE Atoms object to MatSimPy structure.
    
    Args:
        ase_atoms: ase.Atoms object
        
    Returns:
        Crystal or Molecule: MatSimPy structure object
        
    Raises:
        ImportError: If ASE is not installed
        ValueError: If object type is not supported
    """
    try:
        from ase import Atoms
    except ImportError:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install ase"
        )
    
    if not isinstance(ase_atoms, Atoms):
        raise ValueError(f"Expected ASE Atoms object, got {type(ase_atoms)}")
    
    # Get species and positions
    symbols = [symbol for symbol in ase_atoms.get_chemical_symbols()]
    positions = ase_atoms.get_positions().tolist()
    
    # Check if it's a crystal (has cell and PBC)
    cell = ase_atoms.get_cell()
    pbc = ase_atoms.get_pbc()
    
    if cell is not None and cell.any() and any(pbc):
        # Convert to Crystal
        lattice_matrix = cell.array
        lattice = Lattice(lattice_matrix)
        
        crystal = Crystal(
            symbols,
            positions,
            lattice,
            coords_are_cartesian=True,
            pbc=list(pbc)
        )
        
        return crystal
    else:
        # Convert to Molecule
        molecule = Molecule(symbols, positions)
        
        return molecule


__all__ = [
    'to_pymatgen',
    'from_pymatgen',
    'to_ase',
    'from_ase',
]

