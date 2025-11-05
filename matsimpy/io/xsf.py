"""
XSF (XCrySDen) format support.

XSF format is used by XCrySDen visualization software. This module provides
basic support for reading and writing XSF files for crystal structures.
"""

from pathlib import Path
from typing import Optional
import numpy as np

from ..core import Crystal, Lattice


def read_XSF(filename: str) -> Crystal:
    """
    Read an XSF format file.
    
    XSF format supports both crystal and molecule structures. This function
    focuses on crystal structures with periodic boundary conditions.
    
    Args:
        filename: Path to the XSF file
        
    Returns:
        Crystal: Crystal structure from the file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"XSF file not found: {filename}")
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
    
    # Find CRYSTAL block
    crystal_start = None
    for i, line in enumerate(lines):
        if line.upper().startswith('CRYSTAL'):
            crystal_start = i
            break
    
    if crystal_start is None:
        raise ValueError("XSF file does not contain CRYSTAL block")
    
    # Read lattice vectors (3 lines after CRYSTAL)
    lattice_vectors = []
    for i in range(crystal_start + 1, crystal_start + 4):
        if i >= len(lines):
            raise ValueError("Not enough lines for lattice vectors")
        try:
            vec = [float(x) for x in lines[i].split()[:3]]
            if len(vec) != 3:
                raise ValueError(f"Invalid lattice vector at line {i+1}")
            lattice_vectors.append(vec)
        except ValueError as e:
            raise ValueError(f"Invalid lattice vector format at line {i+1}: {e}")
    
    lattice = Lattice(lattice_vectors)
    
    # Find PRIMVEC or CONVVEC (usually PRIMVEC)
    # For now, we'll use the vectors we already read
    
    # Find atomic positions (after PRIMCOORD)
    primcoord_start = None
    for i, line in enumerate(lines):
        if line.upper().startswith('PRIMCOORD'):
            primcoord_start = i
            break
    
    if primcoord_start is None:
        raise ValueError("XSF file does not contain PRIMCOORD block")
    
    # Read number of atoms (line after PRIMCOORD)
    if primcoord_start + 1 >= len(lines):
        raise ValueError("Missing atom count in PRIMCOORD")
    
    try:
        n_atoms = int(lines[primcoord_start + 1].split()[0])
    except (ValueError, IndexError):
        raise ValueError(f"Invalid atom count in PRIMCOORD: {lines[primcoord_start + 1]}")
    
    # Read atomic positions (coordinate type is usually 1 = fractional)
    species = []
    positions = []
    
    for i in range(primcoord_start + 2, primcoord_start + 2 + n_atoms):
        if i >= len(lines):
            raise ValueError(f"Not enough coordinate lines: expected {n_atoms}")
        parts = lines[i].split()
        if len(parts) < 4:
            raise ValueError(f"Invalid coordinate line {i+1}")
        
        try:
            specie = parts[0]
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            species.append(specie)
            positions.append([x, y, z])
        except ValueError as e:
            raise ValueError(f"Invalid coordinate format at line {i+1}: {e}")
    
    # XSF fractional coordinates are typically in crystal coordinates
    return Crystal(species, positions, lattice, coords_are_cartesian=False)


def write_XSF(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to an XSF format file.
    
    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional comment/title (not used in XSF, but kept for API consistency)
        
    Raises:
        ValueError: If crystal is not a valid Crystal object
    """
    if not isinstance(crystal, Crystal):
        raise ValueError("write_XSF requires a Crystal object")
    
    filepath = Path(filename)
    
    with open(filepath, 'w') as f:
        # Write header
        f.write("# XSF file written by MatSimPy\n")
        f.write("CRYSTAL\n")
        
        # Write lattice vectors (PRIMVEC)
        f.write("PRIMVEC\n")
        for vec in crystal.lattice.lattice_vectors:
            f.write(f"{vec[0]:20.12f} {vec[1]:20.12f} {vec[2]:20.12f}\n")
        
        # Write atomic coordinates (PRIMCOORD)
        f.write("PRIMCOORD\n")
        f.write(f"{len(crystal)} 1\n")  # 1 = fractional coordinates
        
        # Write atom positions
        for specie, pos in zip(crystal.species, crystal.frac_positions):
            f.write(f"{specie:4s} {pos[0]:20.12f} {pos[1]:20.12f} {pos[2]:20.12f}\n")


__all__ = ['read_XSF', 'write_XSF']
