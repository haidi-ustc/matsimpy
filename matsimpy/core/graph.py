"""
Graph conversion utilities for Crystal and Molecule structures.

Provides functions to convert MatSimPy structures to graph representations
compatible with ML frameworks like MatterSim, without external dependencies.
"""

import numpy as np
from typing import Optional, Union, Dict, Any
from .crystal import Crystal
from .molecule import Molecule


def structure_to_graph_data(
    structure: Union[Crystal, Molecule],
    cutoff: float = 5.0,
    threebody_cutoff: float = 4.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Convert MatSimPy structure to graph data format.
    
    Extracts all necessary structure information (positions, species, cell, pbc)
    directly from Crystal or Molecule objects for use with ML frameworks.
    
    Args:
        structure: Crystal or Molecule object
        cutoff: Cutoff radius for graph construction (Å)
        threebody_cutoff: Cutoff for three-body interactions (Å)
        **kwargs: Additional parameters
        
    Returns:
        Dictionary containing:
            - positions: Atomic positions (N, 3) in Cartesian coordinates
            - species: List of atomic species (N,)
            - cell: Lattice vectors (3, 3) for crystals, None for molecules
            - pbc: Periodic boundary conditions (3,) for crystals, [False,False,False] for molecules
            - num_atoms: Number of atoms
            - is_crystal: Whether structure is a crystal
            
    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.core.graph import structure_to_graph_data
        >>> 
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> graph_data = structure_to_graph_data(crystal)
        >>> print(graph_data['positions'].shape)  # (1, 3)
        >>> print(graph_data['species'])  # ['Si']
    """
    # Extract positions (already in Cartesian)
    if isinstance(structure, Crystal):
        positions = np.array(structure.cart_positions, dtype=np.float64)
        cell = np.array(structure.lattice.lattice_vectors, dtype=np.float64)
        pbc = np.array(structure.pbc, dtype=bool)
        is_crystal = True
    else:  # Molecule
        positions = np.array(structure.positions, dtype=np.float64)
        cell = None
        pbc = np.array([False, False, False], dtype=bool)
        is_crystal = False
    
    # Extract species
    species = list(structure.species)
    
    return {
        'positions': positions,
        'species': species,
        'cell': cell,
        'pbc': pbc,
        'num_atoms': len(structure),
        'is_crystal': is_crystal,
        'cutoff': cutoff,
        'threebody_cutoff': threebody_cutoff,
    }


def structure_to_mattersim_input(
    structure: Union[Crystal, Molecule]
) -> Any:
    """
    Convert MatSimPy structure to input format for MatterSim's GraphConvertor.
    
    Creates a minimal object with only the attributes MatterSim needs:
    - symbols (or get_chemical_symbols method)
    - positions
    - cell (for crystals)
    - pbc
    - copy() method
    
    All data extracted directly from Crystal/Molecule, no ASE or pymatgen dependency.
    
    Args:
        structure: Crystal or Molecule object
        
    Returns:
        Object compatible with MatterSim's GraphConvertor
        
    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.core.graph import structure_to_mattersim_input
        >>> 
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> atoms_input = structure_to_mattersim_input(crystal)
    """
    # Extract data directly from structure
    if isinstance(structure, Crystal):
        positions = np.array(structure.cart_positions, dtype=np.float64)
        cell = np.array(structure.lattice.lattice_vectors, dtype=np.float64)
        pbc = np.array(structure.pbc, dtype=bool)
    else:  # Molecule
        positions = np.array(structure.positions, dtype=np.float64)
        cell = None
        pbc = np.array([False, False, False], dtype=bool)
    
    species = list(structure.species)
    
    # Create minimal object with required attributes
    class MatterSimInput:
        """Minimal interface for MatterSim GraphConvertor."""
        def __init__(self, symbols, positions, cell, pbc):
            self.symbols = symbols
            self.positions = positions
            self.cell = cell
            self.pbc = pbc
            
            # MatterSim may access these
            self.numbers = self._get_atomic_numbers()
            
        def _get_atomic_numbers(self):
            """Get atomic numbers from symbols."""
            from .periodic_table import Element
            numbers = []
            for symbol in self.symbols:
                elem = Element(symbol)
                numbers.append(elem.atomic_no)
            return np.array(numbers, dtype=int)
        
        def get_chemical_symbols(self):
            """Return chemical symbols (MatterSim may call this)."""
            return self.symbols
        
        def get_scaled_positions(self, wrap=True):
            """Get fractional positions (MatterSim calls this)."""
            if self.cell is None:
                # For molecules, return positions as-is (no scaling)
                return self.positions.copy()
            # Convert Cartesian to fractional
            cell_inv = np.linalg.inv(self.cell)
            frac_pos = np.dot(self.positions, cell_inv)
            if wrap:
                # Wrap to [0, 1)
                frac_pos = frac_pos % 1.0
            return frac_pos
        
        def set_scaled_positions(self, scaled_positions):
            """Set fractional positions (MatterSim calls this)."""
            if self.cell is None:
                # For molecules, set positions directly
                self.positions = np.array(scaled_positions, dtype=np.float64)
            else:
                # Convert fractional to Cartesian
                self.positions = np.dot(scaled_positions, self.cell)
        
        def get_positions(self):
            """Get Cartesian positions (MatterSim calls this)."""
            return self.positions.copy()
        
        def get_atomic_numbers(self):
            """Get atomic numbers (MatterSim calls this)."""
            return self.numbers
        
        def copy(self):
            """Create a copy."""
            return MatterSimInput(
                self.symbols.copy(),
                self.positions.copy(),
                self.cell.copy() if self.cell is not None else None,
                self.pbc.copy()
            )
        
        def set_cell(self, cell):
            """Set cell (MatterSim may call this)."""
            self.cell = np.array(cell, dtype=np.float64)
        
        def set_pbc(self, pbc):
            """Set PBC (MatterSim may call this)."""
            self.pbc = np.array(pbc, dtype=bool)
        
        def __len__(self):
            """Return number of atoms (MatterSim calls len(atoms))."""
            return len(self.symbols)
    
    # Create instance
    atoms_input = MatterSimInput(species, positions, cell, pbc)
    
    return atoms_input


__all__ = ['structure_to_graph_data', 'structure_to_mattersim_input']

