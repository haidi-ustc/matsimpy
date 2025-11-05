"""
Input/output formatting utilities for AI operations.

Provides functions for formatting structures and results for AI interfaces.
"""

from typing import Dict, Any, List, Union
import numpy as np
from ...core import Crystal, Molecule, Lattice


def format_structure_for_ai(structure: Union[Crystal, Molecule]) -> Dict[str, Any]:
    """
    Format structure for AI input.
    
    Converts Crystal or Molecule to dictionary format suitable for AI interfaces.
    
    Args:
        structure: Crystal or Molecule structure
    
    Returns:
        Dictionary representation with:
        - species: List of species
        - positions: List of positions
        - lattice: Lattice vectors (for Crystal only)
        - formula: Chemical formula
        - composition: Composition dictionary
    
    Examples:
        >>> from matsimpy.ai.utils.formatting import format_structure_for_ai
        >>> data = format_structure_for_ai(crystal)
        >>> # {'species': ['Ti', 'O', 'O'], 'positions': [...], 'lattice': [...]}
    """
    # Convert positions to list if numpy array
    positions = structure.positions
    if hasattr(positions, 'tolist'):
        positions = positions.tolist()
    else:
        positions = [list(pos) for pos in positions]
    
    data = {
        "species": list(structure.species),
        "positions": positions,
        "formula": str(structure.formula),
    }
    
    # Add composition info
    if hasattr(structure, 'composition'):
        comp = structure.composition
        # Composition has a .composition attribute that is a Counter
        if hasattr(comp, 'composition'):
            data["composition"] = {
                str(k): float(v) for k, v in comp.composition.items()
            }
        else:
            # Fallback: try to get from formula
            data["composition"] = {"formula": str(comp.formula) if hasattr(comp, 'formula') else str(comp)}
    
    # Add lattice for Crystal
    if isinstance(structure, Crystal):
        lattice = structure.lattice
        if hasattr(lattice.lattice_vectors, 'tolist'):
            data["lattice"] = lattice.lattice_vectors.tolist()
        else:
            data["lattice"] = [list(v) for v in lattice.lattice_vectors]
        
        data["lattice_params"] = {
            "a": float(lattice.a),
            "b": float(lattice.b),
            "c": float(lattice.c),
            "alpha": float(lattice.alpha),
            "beta": float(lattice.beta),
            "gamma": float(lattice.gamma),
        }
        
        data["volume"] = float(structure.volume)
    
    return data


def parse_structure_from_ai(result: Dict[str, Any]) -> Union[Crystal, Molecule]:
    """
    Parse AI result into Crystal or Molecule object.
    
    Args:
        result: AI operation result dictionary with:
               - species: List of species
               - positions: List of positions
               - lattice: Lattice vectors (optional, for Crystal)
    
    Returns:
        Crystal or Molecule object
    """
    species = result.get("species", [])
    positions = result.get("positions", [])
    
    if not species or not positions:
        raise ValueError("Invalid structure result: missing species or positions")
    
    if len(species) != len(positions):
        raise ValueError("Species and positions must have same length")
    
    # Check if it's a crystal (has lattice) or molecule
    lattice_data = result.get("lattice")
    
    if lattice_data:
        # Create Crystal
        lattice = Lattice(lattice_data)
        return Crystal(species, positions, lattice)
    else:
        # Create Molecule
        return Molecule(species, positions)


def format_properties_for_ai(properties: Dict[str, Any]) -> str:
    """
    Format property dictionary for AI prompt.
    
    Args:
        properties: Dictionary of property names to values
    
    Returns:
        Formatted string representation
    """
    lines = []
    for prop, value in properties.items():
        if isinstance(value, (int, float)):
            lines.append(f"{prop}: {value}")
        else:
            lines.append(f"{prop}: {str(value)}")
    
    return "\n".join(lines)


def format_constraints_for_ai(constraints: Dict[str, Any]) -> str:
    """
    Format constraints dictionary for AI prompt.
    
    Args:
        constraints: Dictionary of constraints
    
    Returns:
        Formatted string representation
    """
    lines = []
    for key, value in constraints.items():
        lines.append(f"{key}: {value}")
    
    return ", ".join(lines)


__all__ = [
    'format_structure_for_ai',
    'parse_structure_from_ai',
    'format_properties_for_ai',
    'format_constraints_for_ai',
]

