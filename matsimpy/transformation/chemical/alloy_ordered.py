"""
Ordered alloy generation.

Generate ordered intermetallic compounds and structured alloys.
"""

from typing import Dict, List
from ...core import Crystal, Lattice
from .substitution import substitute


def generate_ordered_alloy(
    base_structure: Crystal, substitution_pattern: Dict[int, str], **kwargs
) -> Crystal:
    """
    Generate ordered alloy with specific substitution pattern.

    Args:
        base_structure: Base crystal structure
        substitution_pattern: Dictionary mapping site indices to species
        **kwargs: Additional parameters

    Returns:
        Crystal: Ordered alloy structure

    Examples:
        >>> from matsimpy.builders.alloy import generate_ordered_alloy
        >>> # Create L1_0 ordered structure
        >>> pattern = {0: 'Au', 1: 'Au', 2: 'Cu', 3: 'Cu'}
        >>> ordered = generate_ordered_alloy(base, pattern)
    """
    # Extract indices and species from pattern
    indices = list(substitution_pattern.keys())
    species_list = [substitution_pattern[idx] for idx in indices]

    # Validate indices
    for idx in indices:
        if idx < 0 or idx >= len(base_structure.species):
            raise ValueError(f"Site index {idx} out of range")

    # Use transformation function for substitution
    return substitute(base_structure, indices, species_list)


def generate_intermetallic(
    elements: List[str],
    composition: str,
    structure_type: str,
    lattice_constant: float,
    **kwargs,
) -> Crystal:
    """
    Generate intermetallic compound with specific structure type.

    Args:
        elements: List of element symbols
        composition: Composition formula (e.g., 'AB', 'AB2', 'A3B')
        structure_type: Structure type ('L1_0', 'L1_2', 'B2', etc.)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Intermetallic structure

    Examples:
        >>> from matsimpy.builders.alloy import generate_intermetallic
        >>> # Generate L1_0 FePt
        >>> fept = generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)
        >>> # Generate L1_2 Ni3Al
        >>> ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)
    """
    SUPPORTED_TYPES = {
        "L1_2": {"n_elements": 2},
        "B2": {"n_elements": 2},
        "L1_0": {"n_elements": 2},
    }

    if structure_type not in SUPPORTED_TYPES:
        raise NotImplementedError(
            f"Intermetallic type '{structure_type}' is not supported. "
            f"Supported: {list(SUPPORTED_TYPES.keys())}"
        )

    if len(elements) != SUPPORTED_TYPES[structure_type]["n_elements"]:
        raise ValueError(
            f"Structure type '{structure_type}' requires "
            f"{SUPPORTED_TYPES[structure_type]['n_elements']} elements, "
            f"got {len(elements)}"
        )

    if structure_type == "L1_2":
        species = [elements[0], elements[0], elements[0], elements[1]]
        positions = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
        lattice = Lattice.cubic(lattice_constant)
        return Crystal(species, positions, lattice)

    elif structure_type == "B2":
        species = [elements[0], elements[1]]
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(lattice_constant)
        return Crystal(species, positions, lattice)

    elif structure_type == "L1_0":
        a = lattice_constant
        c = kwargs.get("c", a * 0.974)
        species = [elements[0], elements[1]]
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.tetragonal(a, c)
        return Crystal(species, positions, lattice)


__all__ = ["generate_ordered_alloy", "generate_intermetallic"]
