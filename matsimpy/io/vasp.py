"""
VASP file format support.

This module provides functions to read and write VASP POSCAR/CONTCAR format files.
Our implementation focuses on clean, readable code that integrates with MatSimPy's
Crystal class.
"""

from pathlib import Path
from typing import Optional, List
import numpy as np

from ..core import Crystal, Lattice


def read_POSCAR(filename: str) -> Crystal:
    """
    Read a VASP POSCAR or CONTCAR file.
    
    This function reads the standard VASP structure format and creates a Crystal
    object. Supports both fractional (Direct) and cartesian coordinates.
    
    Args:
        filename: Path to the POSCAR/CONTCAR file
        
    Returns:
        Crystal: Crystal structure from the file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"POSCAR file not found: {filename}")
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if len(lines) < 8:
        raise ValueError(f"Invalid POSCAR file: too few lines ({len(lines)})")
    
    # Read title (first line)
    title = lines[0]
    
    # Read scale factor (second line)
    try:
        scale_factor = float(lines[1])
    except ValueError:
        raise ValueError(f"Invalid scale factor in POSCAR: {lines[1]}")
    
    # Read lattice vectors (lines 2-4)
    lattice_vectors = []
    for i in range(2, 5):
        if i >= len(lines):
            raise ValueError("Not enough lines for lattice vectors")
        try:
            vec = [float(x) for x in lines[i].split()]
            if len(vec) != 3:
                raise ValueError(f"Invalid lattice vector at line {i+1}")
            lattice_vectors.append(vec)
        except ValueError as e:
            raise ValueError(f"Invalid lattice vector format at line {i+1}: {e}")
    
    lattice_matrix = np.array(lattice_vectors) * scale_factor
    lattice = Lattice(lattice_matrix)
    
    # Read species (line 5)
    if len(lines) < 6:
        raise ValueError("Missing species line in POSCAR")
    species_line = lines[5].split()
    if not species_line:
        raise ValueError("Empty species line in POSCAR")
    
    # Read species counts (line 6)
    if len(lines) < 7:
        raise ValueError("Missing species counts line in POSCAR")
    try:
        species_counts = [int(x) for x in lines[6].split()]
    except ValueError:
        raise ValueError(f"Invalid species counts: {lines[6]}")
    
    if len(species_line) != len(species_counts):
        raise ValueError("Number of species and counts don't match")
    
    # Build species list
    species_list = []
    for specie, count in zip(species_line, species_counts):
        species_list.extend([specie] * count)
    
    total_atoms = sum(species_counts)
    
    # Read coordinate type (line 7)
    if len(lines) < 8:
        raise ValueError("Missing coordinate type indicator")
    coord_type_line = lines[7].strip().lower()
    coords_are_cartesian = coord_type_line.startswith('c') or coord_type_line.startswith('k')
    
    # Read positions (lines 8 onwards)
    if len(lines) < 8 + total_atoms:
        raise ValueError(f"Not enough position lines: expected {total_atoms}, got {len(lines) - 8}")
    
    positions = []
    for i in range(8, 8 + total_atoms):
        try:
            pos = [float(x) for x in lines[i].split()[:3]]  # Take first 3 values
            if len(pos) != 3:
                raise ValueError(f"Invalid position at line {i+1}")
            positions.append(pos)
        except ValueError as e:
            raise ValueError(f"Invalid position format at line {i+1}: {e}")
    
    return Crystal(
        species_list,
        positions,
        lattice,
        coords_are_cartesian=coords_are_cartesian
    )


def write_POSCAR(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to a VASP POSCAR file.
    
    This function writes the structure in standard VASP format with fractional
    coordinates by default.
    
    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional title for the POSCAR file (default: "MatSimPy Crystal")
        
    Raises:
        ValueError: If crystal is not a valid Crystal object
    """
    if not isinstance(crystal, Crystal):
        raise ValueError("write_POSCAR requires a Crystal object")
    
    if title is None:
        title = f"{crystal.__class__.__name__} - {crystal.formula}"
    
    filepath = Path(filename)
    
    with open(filepath, 'w') as f:
        # Write title
        f.write(f"{title}\n")
        
        # Write scale factor (always 1.0)
        f.write("1.0\n")
        
        # Write lattice vectors
        for vec in crystal.lattice.lattice_vectors:
            f.write(f"{vec[0]:.16f} {vec[1]:.16f} {vec[2]:.16f}\n")
        
        # Write species
        unique_species = []
        species_counts = []
        seen = set()
        for specie in crystal.species:
            if specie not in seen:
                unique_species.append(specie)
                species_counts.append(crystal.species.count(specie))
                seen.add(specie)
        
        f.write(" ".join(unique_species) + "\n")
        f.write(" ".join(map(str, species_counts)) + "\n")
        
        # Write coordinate type (always Direct/fractional)
        f.write("Direct\n")
        
        # Write positions (fractional coordinates)
        for pos in crystal.frac_positions:
            f.write(f"{pos[0]:.16f} {pos[1]:.16f} {pos[2]:.16f}\n")


def read_CONTCAR(filename: str) -> Crystal:
    """
    Read a VASP CONTCAR file (alias for read_POSCAR).
    
    CONTCAR format is identical to POSCAR, so this is just a convenience function.
    
    Args:
        filename: Path to the CONTCAR file
        
    Returns:
        Crystal: Crystal structure from the file
    """
    return read_POSCAR(filename)


def write_CONTCAR(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to a VASP CONTCAR file (alias for write_POSCAR).
    
    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional title for the CONTCAR file
    """
    write_POSCAR(crystal, filename, title)


__all__ = ['read_POSCAR', 'write_POSCAR', 'read_CONTCAR', 'write_CONTCAR']
