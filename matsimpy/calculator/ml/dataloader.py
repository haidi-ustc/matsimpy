"""
DataLoader utilities for MatterSim ML calculator.

Provides functions to build dataloaders from MatSimPy structures (Crystal/Molecule)
without requiring ASE Atoms dependency.
"""

import numpy as np
import torch
from typing import List, Optional, Union, Any
from torch_geometric.loader import DataLoader as DataLoader_pyg
from mattersim.datasets.utils.convertor import GraphConvertor
from ...core import Crystal, Molecule, Element


def _create_atoms_like_object(structure: Union[Crystal, Molecule]) -> Any:
    """
    Create a minimal object compatible with MatterSim's GraphConvertor.
    
    This creates a duck-typed object that mimics ASE Atoms interface
    without requiring ASE dependency.
    
    Args:
        structure: Crystal or Molecule object
        
    Returns:
        Object compatible with GraphConvertor
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
    
    # Create minimal object with required attributes and methods
    class AtomsLike:
        """Minimal interface for MatterSim GraphConvertor."""
        def __init__(self, symbols, positions, cell, pbc):
            self.symbols = symbols
            self.positions = positions
            self.cell = cell
            self.pbc = pbc
            self.numbers = self._get_atomic_numbers()
        
        def _get_atomic_numbers(self):
            """Get atomic numbers from symbols."""
            return np.array([Element(s).atomic_no for s in self.symbols], dtype=int)
        
        def get_chemical_symbols(self):
            return self.symbols
        
        def get_scaled_positions(self, wrap=True):
            """Get fractional positions."""
            if self.cell is None:
                return self.positions.copy()
            cell_inv = np.linalg.inv(self.cell)
            frac_pos = np.dot(self.positions, cell_inv)
            if wrap:
                frac_pos = frac_pos % 1.0
            return frac_pos
        
        def set_scaled_positions(self, scaled_positions):
            """Set fractional positions."""
            if self.cell is None:
                self.positions = np.array(scaled_positions, dtype=np.float64)
            else:
                self.positions = np.dot(scaled_positions, self.cell)
        
        def get_positions(self):
            return self.positions.copy()
        
        def get_atomic_numbers(self):
            return self.numbers
        
        def copy(self):
            return AtomsLike(
                self.symbols.copy(),
                self.positions.copy(),
                self.cell.copy() if self.cell is not None else None,
                self.pbc.copy()
            )
        
        def set_cell(self, cell):
            self.cell = np.array(cell, dtype=np.float64) if cell is not None else None
        
        def set_pbc(self, pbc):
            self.pbc = np.array(pbc, dtype=bool)
        
        def __len__(self):
            return len(self.symbols)
    
    return AtomsLike(species, positions, cell, pbc)


def _patch_isinstance_for_matsimpy():
    """
    Patch isinstance check in MatterSim's convertor module to accept MatSimPy objects.
    
    MatterSim's GraphConvertor checks isinstance(atoms, Atoms) which requires ASE.
    We patch this to accept our AtomsLike objects based on duck typing.
    """
    import mattersim.datasets.utils.convertor as convertor_module
    import builtins
    
    # Store original isinstance if not already stored
    if not hasattr(convertor_module, '_original_isinstance'):
        convertor_module._original_isinstance = builtins.isinstance
    
    # Patch isinstance in convertor module
    def patched_isinstance(obj, cls):
        # Accept our AtomsLike objects as Atoms (duck typing)
        if hasattr(cls, '__name__') and cls.__name__ == 'Atoms':
            if (hasattr(obj, 'symbols') and 
                hasattr(obj, 'positions') and 
                hasattr(obj, 'get_scaled_positions') and
                hasattr(obj, 'copy')):
                return True
        # Check for ASE Atoms module
        if hasattr(cls, '__module__') and 'ase' in str(cls.__module__):
            if (hasattr(obj, 'symbols') and hasattr(obj, 'positions')):
                return True
        # Fall back to original isinstance
        return convertor_module._original_isinstance(obj, cls)
    
    convertor_module.isinstance = patched_isinstance


def build_dataloader(
    structures: List[Union[Crystal, Molecule]],
    energies: Optional[List[float]] = None,
    forces: Optional[List[np.ndarray]] = None,
    stresses: Optional[List[np.ndarray]] = None,
    cutoff: float = 5.0,
    threebody_cutoff: float = 4.0,
    batch_size: int = 1,
    model_type: str = "m3gnet",
    shuffle: bool = False,
    only_inference: bool = True,
    num_workers: int = 0,
    pin_memory: bool = False,
    **kwargs,
):
    """
    Build a dataloader from MatSimPy structures (Crystal/Molecule).
    
    This function adapts MatterSim's build_dataloader to work directly with
    MatSimPy structures without requiring ASE Atoms.
    
    Args:
        structures: List of Crystal or Molecule objects
        energies: Optional list of energies (eV) for training
        forces: Optional list of force arrays (N, 3) in eV/Å for training
        stresses: Optional list of stress arrays (3, 3) in GPa for training
        cutoff: Cutoff radius for graph construction (Å)
        threebody_cutoff: Cutoff for three-body interactions (Å)
        batch_size: Batch size for dataloader
        model_type: Model type (default: "m3gnet")
        shuffle: Whether to shuffle data
        only_inference: If True, energies/forces/stresses are ignored
        num_workers: Number of workers for dataloader
        pin_memory: Whether to pin memory
        **kwargs: Additional arguments
        
    Returns:
        DataLoader: PyTorch Geometric DataLoader
        
    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.calculator.ml.dataloader import build_dataloader
        >>> 
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> dataloader = build_dataloader([crystal], only_inference=True)
    """
    # Patch isinstance to accept MatSimPy objects
    _patch_isinstance_for_matsimpy()
    
    # Convert MatSimPy structures to atoms-like objects
    atoms = [_create_atoms_like_object(struct) for struct in structures]
    
    # Create convertor
    convertor = GraphConvertor(model_type, cutoff, True, threebody_cutoff)
    
    # Prepare data
    if not only_inference:
        assert energies is not None, "energies must be provided if only_inference is False"
    
    if stresses is not None:
        assert np.array(stresses[0]).shape == (3, 3), "stresses must be a list of 3x3 matrices"
    
    length = len(atoms)
    if energies is None:
        energies = [None] * length
    if forces is None:
        forces = [None] * length
    if stresses is None:
        stresses = [None] * length
    
    # Convert to graph format
    preprocessed_data = []
    for atom, energy, force, stress in zip(atoms, energies, forces, stresses):
        graph = convertor.convert(atom.copy(), energy, force, stress, **kwargs)
        if graph is not None:
            preprocessed_data.append(graph)
    
    # Create and return DataLoader
    return DataLoader_pyg(
        preprocessed_data,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )


__all__ = ['build_dataloader']

