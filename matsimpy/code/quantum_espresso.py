"""
Quantum Espresso DFT code interface.

This module provides functions for generating Quantum Espresso input files
from crystal structures.
"""

from typing import Optional, Union
import numpy as np

from ..core import Crystal, Molecule


def write_input(structure: Union[Crystal, Molecule], filename: str, **kwargs) -> None:
    """
    Write Quantum Espresso input file from Crystal or Molecule structure.
    
    Args:
        structure: Crystal or Molecule structure to convert
        filename: Output filename
        **kwargs: Additional parameters for Quantum Espresso input
                 (e.g., calculation type, k-points, etc.)
        
    Raises:
        ValueError: If structure is not a valid Crystal or Molecule object
    """
    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError("write_input requires a Crystal or Molecule object")
    
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
    
    with open(filename, 'w') as file:
        file.write(qe_str)


def read_output(filename: str) -> dict:
    """
    Read Quantum Espresso output file.
    
    Args:
        filename: Path to Quantum Espresso output file
        
    Returns:
        dict: Dictionary containing parsed output data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        NotImplementedError: Not yet implemented
    """
    # TODO: Implement Quantum Espresso output parsing
    raise NotImplementedError("Quantum Espresso output parsing not yet implemented")


# Keep legacy function for backward compatibility (deprecated)
def to_quantum_espresso(structure: Union[Crystal, Molecule], filename: Optional[str] = None) -> Optional[str]:
    """
    Convert a Crystal or Molecule structure to Quantum Espresso input format.
    
    DEPRECATED: Use write_input() instead.
    
    Args:
        structure: Crystal or Molecule structure to convert
        filename: Optional filename to write to. If None, returns string.
        
    Returns:
        str or None: Quantum Espresso input string if filename is None, otherwise None
        
    Raises:
        ValueError: If structure is not a valid Crystal or Molecule object
    """
    if filename:
        write_input(structure, filename)
        return None
    else:
        # Return string representation
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            temp_file = f.name
        try:
            write_input(structure, temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
            return content
        finally:
            os.unlink(temp_file)


__all__ = ['write_input', 'read_output', 'to_quantum_espresso']
