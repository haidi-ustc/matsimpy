"""
CIF (Crystallographic Information File) format support.

This module provides functions to read and write CIF format files following
the CIF 1.1 standard. Our implementation focuses on the essential data items
needed for crystal structure representation.
"""

from pathlib import Path
from typing import Optional, Dict, List
import re
import numpy as np

from ..core import Crystal, Lattice


def _parse_cif_value(value: str) -> float:
    """
    Parse a CIF value, handling uncertainties and parentheses.
    
    Args:
        value: CIF value string (may contain uncertainty like "1.5(2)")
        
    Returns:
        float: Parsed numeric value
    """
    # Remove uncertainty in parentheses like "1.5(2)" -> "1.5"
    value = re.sub(r'\([^)]*\)', '', value)
    # Remove leading/trailing whitespace and quotes
    value = value.strip().strip('"\'')
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Could not parse CIF value as float: {value}")


def _parse_cif_line(line: str) -> tuple:
    """
    Parse a CIF data line.
    
    Args:
        line: CIF line (may be data_item or loop)
        
    Returns:
        tuple: (data_name, value) or None if not a data line
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # Check for data_ block
    if line.startswith('data_'):
        return ('data_block', line[5:].strip())
    
    # Check for loop_ statement
    if line.startswith('loop_'):
        return ('loop_start', None)
    
    # Check for data item (starts with _)
    if line.startswith('_'):
        parts = line.split(None, 1)
        if len(parts) == 2:
            return (parts[0], parts[1].strip().strip('"\''))
        elif len(parts) == 1:
            return (parts[0], None)
    
    return None


def read_CIF(filename: str) -> Crystal:
    """
    Read a CIF (Crystallographic Information File) format file.
    
    This function reads standard CIF files and extracts crystal structure
    information including lattice parameters and atomic positions.
    
    Args:
        filename: Path to the CIF file
        
    Returns:
        Crystal: Crystal structure from the file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid or missing required data
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"CIF file not found: {filename}")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Parse CIF data
    cif_data = {}
    in_loop = False
    loop_items = []
    loop_data_lines = []
    current_line_index = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        parsed = _parse_cif_line(line)
        
        if parsed is None:
            i += 1
            continue
        
        data_name, value = parsed
        
        if data_name == 'loop_start':
            in_loop = True
            loop_items = []
            loop_data_lines = []
            i += 1
            # Collect loop items
            while i < len(lines):
                loop_line = lines[i]
                if not loop_line.strip():
                    i += 1
                    continue
                loop_parsed = _parse_cif_line(loop_line)
                if loop_parsed is None:
                    # Empty line or comment, skip
                    i += 1
                    continue
                loop_name, loop_value = loop_parsed
                if loop_name.startswith('_'):
                    loop_items.append(loop_name)
                    i += 1
                else:
                    # Start of data (not a data item line)
                    break
            # Collect data lines
            while i < len(lines):
                data_line = lines[i]
                if not data_line.strip():
                    break
                # Check if this is a data item or loop start (end of loop)
                if data_line.strip().startswith('_') or data_line.strip().startswith('loop_') or data_line.strip().startswith('data_'):
                    break
                # This is a data line
                loop_data_lines.append(data_line.strip())
                i += 1
            # Process loop data
            for data_line in loop_data_lines:
                if not data_line.strip():
                    continue
                values = data_line.split()
                for j, item in enumerate(loop_items):
                    if item not in cif_data:
                        cif_data[item] = []
                    if j < len(values):
                        cif_data[item].append(values[j])
            in_loop = False
        else:
            if data_name.startswith('_'):
                cif_data[data_name] = value
            i += 1
    
    # Extract lattice parameters
    # Try both standard and alternative CIF data names
    a = _parse_cif_value(cif_data.get('_cell_length_a', cif_data.get('_cell_length_a?', '0')))
    b = _parse_cif_value(cif_data.get('_cell_length_b', cif_data.get('_cell_length_b?', '0')))
    c = _parse_cif_value(cif_data.get('_cell_length_c', cif_data.get('_cell_length_c?', '0')))
    alpha = _parse_cif_value(cif_data.get('_cell_angle_alpha', cif_data.get('_cell_angle_alpha?', '90')))
    beta = _parse_cif_value(cif_data.get('_cell_angle_beta', cif_data.get('_cell_angle_beta?', '90')))
    gamma = _parse_cif_value(cif_data.get('_cell_angle_gamma', cif_data.get('_cell_angle_gamma?', '90')))
    
    if a == 0 or b == 0 or c == 0:
        raise ValueError("Invalid lattice parameters in CIF file")
    
    # Create lattice from parameters
    lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)
    
    # Extract atomic positions
    # Look for atom site loop or individual site data
    atom_species = []
    atom_positions = []
    
    # Try to get from loop data
    if '_atom_site_type_symbol' in cif_data:
        atom_species = cif_data['_atom_site_type_symbol']
    elif '_atom_site_label' in cif_data:
        # Extract element from label (e.g., "Si1" -> "Si")
        labels = cif_data['_atom_site_label']
        atom_species = [re.match(r'([A-Z][a-z]?)', label).group(1) if re.match(r'[A-Z][a-z]?', label) else label 
                       for label in labels]
    
    # Get positions
    frac_x = cif_data.get('_atom_site_fract_x', cif_data.get('_atom_site_fract_x?'))
    frac_y = cif_data.get('_atom_site_fract_y', cif_data.get('_atom_site_fract_y?'))
    frac_z = cif_data.get('_atom_site_fract_z', cif_data.get('_atom_site_fract_z?'))
    
    if not (frac_x and frac_y and frac_z):
        # Try cartesian coordinates
        cart_x = cif_data.get('_atom_site_Cartn_x', cif_data.get('_atom_site_Cartn_x?'))
        cart_y = cif_data.get('_atom_site_Cartn_y', cif_data.get('_atom_site_Cartn_y?'))
        cart_z = cif_data.get('_atom_site_Cartn_z', cif_data.get('_atom_site_Cartn_z?'))
        
        if cart_x and cart_y and cart_z:
            # Convert cartesian to fractional
            positions = []
            for x, y, z in zip(cart_x, cart_y, cart_z):
                cart_pos = np.array([_parse_cif_value(x), _parse_cif_value(y), _parse_cif_value(z)])
                frac_pos = np.dot(cart_pos, np.linalg.inv(lattice.matrix))
                positions.append(frac_pos.tolist())
            
            if not atom_species:
                raise ValueError("Could not find atomic species in CIF file")
            
            return Crystal(atom_species, positions, lattice, coords_are_cartesian=False)
        else:
            raise ValueError("Could not find atomic positions in CIF file")
    
    # Parse fractional positions
    positions = []
    for x, y, z in zip(frac_x, frac_y, frac_z):
        positions.append([
            _parse_cif_value(x),
            _parse_cif_value(y),
            _parse_cif_value(z)
        ])
    
    if not atom_species:
        raise ValueError("Could not find atomic species in CIF file")
    
    if len(atom_species) != len(positions):
        raise ValueError(f"Number of species ({len(atom_species)}) doesn't match positions ({len(positions)})")
    
    return Crystal(atom_species, positions, lattice, coords_are_cartesian=False)


def write_CIF(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to a CIF format file.
    
    This function writes the structure following CIF 1.1 standard conventions.
    
    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional title/data block name (default: uses formula)
        
    Raises:
        ValueError: If crystal is not a valid Crystal object
    """
    if not isinstance(crystal, Crystal):
        raise ValueError("write_CIF requires a Crystal object")
    
    if title is None:
        # Create valid CIF data block name (alphanumeric and underscores only)
        title = re.sub(r'[^a-zA-Z0-9_]', '_', crystal.formula)
        if not title[0].isalpha():
            title = 'structure_' + title
    
    filepath = Path(filename)
    
    with open(filepath, 'w') as f:
        # Write data block header
        f.write(f"data_{title}\n\n")
        
        # Write cell parameters
        f.write("_cell_length_a    {:.6f}\n".format(crystal.lattice.a))
        f.write("_cell_length_b    {:.6f}\n".format(crystal.lattice.b))
        f.write("_cell_length_c    {:.6f}\n".format(crystal.lattice.c))
        f.write("_cell_angle_alpha {:.6f}\n".format(crystal.lattice.alpha))
        f.write("_cell_angle_beta  {:.6f}\n".format(crystal.lattice.beta))
        f.write("_cell_angle_gamma {:.6f}\n\n".format(crystal.lattice.gamma))
        
        # Write space group (if available, otherwise use P1)
        f.write("_space_group_name_H-M_alt     'P 1'\n")
        f.write("_space_group_IT_number       1\n\n")
        
        # Write loop for atomic positions
        f.write("loop_\n")
        f.write("_atom_site_type_symbol\n")
        f.write("_atom_site_label\n")
        f.write("_atom_site_fract_x\n")
        f.write("_atom_site_fract_y\n")
        f.write("_atom_site_fract_z\n")
        f.write("_atom_site_occupancy\n")
        
        # Write atomic positions
        for i, (specie, pos) in enumerate(zip(crystal.species, crystal.frac_positions)):
            label = f"{specie}{i+1}"
            f.write(f"{specie:4s} {label:8s} {pos[0]:12.8f} {pos[1]:12.8f} {pos[2]:12.8f} 1.0\n")


__all__ = ['read_CIF', 'write_CIF']
