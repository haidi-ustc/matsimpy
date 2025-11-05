"""
MOL (MDL Molfile) format support.

This module provides functions to read and write MOL format files, which are
commonly used in cheminformatics and molecular modeling. MOL format includes
connectivity information as well as atomic coordinates.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np

from ..core import Molecule


def read_MOL(filename: str) -> Molecule:
    """
    Read a MOL format file.
    
    MOL format structure:
    - Header: 3 lines (title, program info, comments)
    - Counts line: "nnn nnn ..." (atom count, bond count, etc.)
    - Atom block: atom lines with coordinates
    - Bond block: bond connectivity information
    - Properties block (optional)
    
    We primarily extract atomic coordinates and species.
    
    Args:
        filename: Path to the MOL file
        
    Returns:
        Molecule: Molecule object from the file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"MOL file not found: {filename}")
    
    with open(filepath, 'r') as f:
        lines = [line.rstrip() for line in f.readlines()]
    
    if len(lines) < 5:
        raise ValueError("MOL file must have at least 5 lines (header + counts)")
    
    # Read header (lines 0-2)
    title = lines[0].strip()
    program_info = lines[1].strip() if len(lines) > 1 else ""
    comments = lines[2].strip() if len(lines) > 2 else ""
    
    # Read counts line (line 3)
    if len(lines) < 4:
        raise ValueError("MOL file missing counts line")
    
    counts_line = lines[3]
    # MOL counts line can have various formats
    # Try to extract first two numbers (atoms and bonds)
    counts = counts_line.split()
    
    if len(counts) < 1:
        raise ValueError("Invalid counts line in MOL file")
    
    try:
        # Try to get atom count from first number
        n_atoms = int(counts[0])
        # Bond count is optional, default to 0
        n_bonds = int(counts[1]) if len(counts) > 1 else 0
    except ValueError:
        # Try parsing from fixed-width format
        try:
            if len(counts_line) >= 6:
                n_atoms = int(counts_line[0:3].strip())
                n_bonds = int(counts_line[3:6].strip()) if len(counts_line) >= 6 else 0
            else:
                raise ValueError(f"Invalid atom/bond counts in MOL file: {counts_line}")
        except ValueError:
            raise ValueError(f"Invalid atom/bond counts in MOL file: {counts_line}")
    
    if n_atoms <= 0:
        raise ValueError(f"Invalid number of atoms: {n_atoms}")
    
    # Read atom block (lines 4 to 4+n_atoms)
    if len(lines) < 4 + n_atoms:
        raise ValueError(f"Not enough lines for {n_atoms} atoms")
    
    species = []
    positions = []
    
    for i in range(4, 4 + n_atoms):
        if i >= len(lines):
            break
        
        line = lines[i]
        if len(line) < 30:  # Minimum line length for atom data
            continue
        
        try:
            # MOL atom line format (fixed width):
            # xxxxx.xxxx yyyyy.yyyy zzzzz.zzzz EEE MM 0 0 0 0 0 0 0 0 0 0 0 0
            # Positions: 0-9, 10-19, 20-29
            x = float(line[0:10].strip())
            y = float(line[10:20].strip())
            z = float(line[20:30].strip())
            
            # Element symbol might be at position 31-33 (after coordinates)
            # Or we might need to infer from atom type
            if len(line) > 31:
                element = line[31:34].strip()
                if not element or element == '0':
                    # Try to get from later positions or use default
                    element = 'C'  # Default to carbon
            else:
                element = 'C'  # Default
            
            # Some MOL files have element in different position
            # Try alternative parsing
            parts = line.split()
            if len(parts) >= 4:
                try:
                    # If 4th element is numeric, element might be later
                    float(parts[3])
                    if len(parts) >= 5:
                        element = parts[4]
                except ValueError:
                    # 4th element might be the element symbol
                    element = parts[3]
            
            # Clean element symbol
            element = element.strip()
            if not element or element.isdigit():
                element = 'C'  # Default fallback
            
            species.append(element)
            positions.append([x, y, z])
        except (ValueError, IndexError) as e:
            # Skip invalid lines
            continue
    
    if not species:
        raise ValueError("No valid atoms found in MOL file")
    
    return Molecule(species, positions)


def write_MOL(molecule: Molecule, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Molecule to MOL format file.
    
    Args:
        molecule: Molecule object to write
        filename: Output filename
        title: Optional title (default: molecule formula)
        
    Raises:
        ValueError: If molecule is not a valid Molecule object
    """
    if not isinstance(molecule, Molecule):
        raise ValueError("write_MOL requires a Molecule object")
    
    if title is None:
        title = molecule.formula if hasattr(molecule, 'formula') else "MatSimPy Molecule"
    
    filepath = Path(filename)
    
    with open(filepath, 'w') as f:
        # Write header
        f.write(f"{title}\n")
        f.write("  MatSimPy\n")
        f.write("\n")
        
        # Write counts line
        # Format: "nnn nnn ..." (atoms, bonds, ...)
        n_atoms = len(molecule)
        n_bonds = 0  # We don't calculate bonds, set to 0
        f.write(f"{n_atoms:3d}{n_bonds:3d}  0  0  0  0  0  0  0  0  1 V2000\n")
        
        # Write atom block
        for specie, pos in zip(molecule.species, molecule.positions):
            # Format: xxxxx.xxxx yyyyy.yyyy zzzzz.zzzz EEE MM 0 0 0 0 0 0 0 0 0 0 0 0
            f.write(f"{pos[0]:10.4f}{pos[1]:10.4f}{pos[2]:10.4f} {specie:>3s}  0  0  0  0  0  0  0  0  0  0  0  0\n")
        
        # Write bond block (empty since we don't have bond info)
        # Still write M  END
        f.write("M  END\n")


__all__ = ['read_MOL', 'write_MOL']

