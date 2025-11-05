"""
XYZ coordinate format support.

This module provides functions to read and write XYZ format files, which are
commonly used for molecular structures. The format is simple: number of atoms,
title line, then atom symbol and xyz coordinates for each atom.
"""

from pathlib import Path
from typing import Optional, List
import numpy as np

from ..core import Molecule


def read_XYZ(filename: str) -> Molecule:
    """
    Read an XYZ format file.
    
    XYZ format consists of:
    - Line 1: Number of atoms
    - Line 2: Title/comment (optional)
    - Lines 3+: Atom symbol and xyz coordinates
    
    Multi-frame XYZ files are supported - only the first frame is read.
    
    Args:
        filename: Path to the XYZ file
        
    Returns:
        Molecule: Molecule object from the file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"XYZ file not found: {filename}")
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if len(lines) < 2:
        raise ValueError("XYZ file must have at least 2 lines (atom count and coordinates)")
    
    # Read number of atoms
    try:
        n_atoms = int(lines[0])
    except ValueError:
        raise ValueError(f"Invalid atom count in XYZ file: {lines[0]}")
    
    if n_atoms <= 0:
        raise ValueError(f"Invalid number of atoms: {n_atoms}")
    
    # Check if we have enough lines
    if len(lines) < 2 + n_atoms:
        raise ValueError(f"Not enough coordinate lines: expected {n_atoms}, got {len(lines) - 2}")
    
    # Read title (line 1, optional)
    title = lines[1] if len(lines) > 1 else ""
    
    # Read atom coordinates (lines 2 onwards)
    species = []
    positions = []
    
    for i in range(2, 2 + n_atoms):
        parts = lines[i].split()
        if len(parts) < 4:
            raise ValueError(f"Invalid coordinate line {i+1}: expected at least 4 values (symbol x y z)")
        
        try:
            specie = parts[0]
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            species.append(specie)
            positions.append([x, y, z])
        except ValueError as e:
            raise ValueError(f"Invalid coordinate format at line {i+1}: {e}")
    
    return Molecule(species, positions)


def write_XYZ(molecule: Molecule, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Molecule to an XYZ format file.
    
    Args:
        molecule: Molecule object to write
        filename: Output filename
        title: Optional title/comment line (default: molecule formula)
        
    Raises:
        ValueError: If molecule is not a valid Molecule object
    """
    if not isinstance(molecule, Molecule):
        raise ValueError("write_XYZ requires a Molecule object")
    
    if title is None:
        title = molecule.formula if hasattr(molecule, 'formula') else "MatSimPy Molecule"
    
    filepath = Path(filename)
    
    with open(filepath, 'w') as f:
        # Write number of atoms
        f.write(f"{len(molecule)}\n")
        
        # Write title
        f.write(f"{title}\n")
        
        # Write atom coordinates
        for specie, pos in zip(molecule.species, molecule.positions):
            f.write(f"{specie:4s} {pos[0]:15.10f} {pos[1]:15.10f} {pos[2]:15.10f}\n")


def read_XYZ_multiframe(filename: str) -> List[Molecule]:
    """
    Read a multi-frame XYZ file.
    
    Some XYZ files contain multiple structures (frames). This function reads
    all frames from the file.
    
    Args:
        filename: Path to the XYZ file
        
    Returns:
        List[Molecule]: List of Molecule objects, one per frame
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"XYZ file not found: {filename}")
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
    
    molecules = []
    i = 0
    
    while i < len(lines):
        if not lines[i]:
            i += 1
            continue
        
        try:
            n_atoms = int(lines[i])
        except ValueError:
            i += 1
            continue
        
        if i + 1 + n_atoms >= len(lines):
            break
        
        # Read frame
        title = lines[i + 1] if i + 1 < len(lines) else ""
        species = []
        positions = []
        
        for j in range(i + 2, i + 2 + n_atoms):
            if j >= len(lines):
                break
            parts = lines[j].split()
            if len(parts) >= 4:
                specie = parts[0]
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                species.append(specie)
                positions.append([x, y, z])
        
        if len(species) == n_atoms:
            molecules.append(Molecule(species, positions))
        
        i += 2 + n_atoms
    
    return molecules


__all__ = ['read_XYZ', 'write_XYZ', 'read_XYZ_multiframe']
