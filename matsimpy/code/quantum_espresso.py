"""
Quantum Espresso DFT code interface.

This module provides functions for generating Quantum Espresso input files
from crystal structures.
"""

from typing import Optional
import numpy as np

from ..core import Crystal


def to_quantum_espresso(crystal: Crystal, filename: Optional[str] = None) -> Optional[str]:
    """
    Convert a Crystal structure to Quantum Espresso input format.
    
    Args:
        crystal: Crystal structure to convert
        filename: Optional filename to write to. If None, returns string.
        
    Returns:
        str or None: Quantum Espresso input string if filename is None, otherwise None
        
    Raises:
        ValueError: If crystal is not a valid Crystal object
    """
    if not isinstance(crystal, Crystal):
        raise ValueError("to_quantum_espresso requires a Crystal object")
    
    # Prepare the Quantum Espresso formatted string
    qe_str = "&system\n"
    qe_str += f"  ibrav = 0,\n"
    qe_str += f"  nat = {len(crystal)},\n"
    qe_str += f"  ntyp = {len(np.unique(crystal.species))},\n"
    qe_str += "/\n\n"
    
    qe_str += "ATOMIC_SPECIES\n"
    unique_species, _ = np.unique(crystal.species, return_counts=True)
    for s in unique_species:
        qe_str += f"{s} 1.0 {s}.UPF\n"
    
    qe_str += "\nCELL_PARAMETERS (angstrom)\n"
    for vector in crystal.lattice.lattice_vectors:
        qe_str += f"{vector[0]:.8f} {vector[1]:.8f} {vector[2]:.8f}\n"
    
    qe_str += "\nATOMIC_POSITIONS (angstrom)\n"
    for s, position in zip(crystal.species, crystal.cart_positions):
        qe_str += f"{s} {position[0]:.8f} {position[1]:.8f} {position[2]:.8f}\n"
    
    if filename:
        with open(filename, 'w') as file:
            file.write(qe_str)
        return None
    else:
        return qe_str


__all__ = ['to_quantum_espresso']
