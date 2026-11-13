"""
Ordered alloy generation.

Generate ordered intermetallic compounds and structured alloys.
"""

from matsimpy.utils.tooling import tool
from typing import Dict, List, Optional

import numpy as np

from ...core import Crystal, Lattice
from ...transformation.chemical.substitution import substitute


def generate_ordered_alloy(
    base_structure: Crystal, substitution_pattern: Dict[int, str]
) -> Crystal:
    """
    Generate ordered alloy with specific substitution pattern.

    Args:
        base_structure: Base crystal structure
        substitution_pattern: Dictionary mapping site indices to species

    Returns:
        Crystal: Ordered alloy structure

    Examples:
        >>> from matsimpy.builders.alloy import generate_ordered_alloy
        >>> from matsimpy.core import Crystal, Lattice
        >>> base = Crystal(['Cu'] * 4, [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        ...                Lattice.cubic(3.75))
        >>> generate_ordered_alloy(base, {0: 'Au', 1: 'Au'}).formula
        'Au2Cu2'
    """
    # Extract indices and species from pattern
    indices = list(substitution_pattern.keys())
    species_list = [substitution_pattern[idx] for idx in indices]

    # Validate indices
    for idx in indices:
        if isinstance(idx, bool) or not isinstance(idx, (int, np.integer)):
            raise TypeError(f"Site indices must be integers, got {idx!r}")
        if idx < 0 or idx >= len(base_structure.species):
            raise ValueError(f"Site index {idx} out of range")

    # Use transformation function for substitution
    return substitute(base_structure, indices, species_list)


_INTERMETALLICS = {
    # structure type: (composition, [(element index, fractional position)])
    "L1_2": ("A3B", [(0, (0.0, 0.5, 0.5)), (0, (0.5, 0.0, 0.5)), (0, (0.5, 0.5, 0.0)), (1, (0.0, 0.0, 0.0))]),
    "B2": ("AB", [(0, (0.0, 0.0, 0.0)), (1, (0.5, 0.5, 0.5))]),
    "L1_0": ("AB", [(0, (0.0, 0.0, 0.0)), (0, (0.5, 0.5, 0.0)), (1, (0.5, 0.0, 0.5)), (1, (0.0, 0.5, 0.5))]),
}


@tool
def generate_intermetallic(
    elements: List[str],
    composition: str,
    structure_type: str,
    lattice_constant: float,
    c: Optional[float] = None,
) -> Crystal:
    """
    Generate an ordered intermetallic compound in its conventional cell.

    - L1_2 (Cu3Au type, Pm-3m): A3B, A on the face centres, B on the corners.
    - B2 (CsCl type, Pm-3m): AB, A at the corner, B at the body centre.
    - L1_0 (CuAu type, P4/mmm): AB, alternating (001) planes of A and B in the
      face-centred tetragonal cell (4 atoms).

    Args:
        elements: The two element symbols [A, B]
        composition: The formula of the structure type in terms of A and B
            ('A3B' for L1_2, 'AB' for B2 and L1_0); checked against structure_type
        structure_type: 'L1_2', 'B2' or 'L1_0'
        lattice_constant: Cubic lattice constant a in Angstroms
        c: L1_0 only: the c lattice constant (default 0.974 a, typical of FePt-type
            compounds)

    Returns:
        Crystal: Intermetallic structure

    Examples:
        >>> from matsimpy.builders.alloy import generate_intermetallic
        >>> generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85, c=3.71).formula
        'Fe2Pt2'
        >>> generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56).formula
        'Ni3Al'
    """
    if structure_type not in _INTERMETALLICS:
        raise NotImplementedError(
            f"Intermetallic type '{structure_type}' is not supported. "
            f"Supported: {list(_INTERMETALLICS)}"
        )
    expected, sites = _INTERMETALLICS[structure_type]
    if isinstance(elements, str) or len(elements) != 2:
        raise ValueError(f"Structure type '{structure_type}' requires 2 elements, got {elements!r}")
    if composition != expected:
        raise ValueError(f"Structure type '{structure_type}' has composition '{expected}', got '{composition}'")
    for name, value in (("lattice_constant", lattice_constant), ("c", c)):
        if value is not None and (isinstance(value, bool) or not np.isfinite(value) or value <= 0):
            raise ValueError(f"{name} must be positive, got {value}")
    if structure_type == "L1_0":
        lattice = Lattice.tetragonal(lattice_constant, 0.974 * lattice_constant if c is None else c)
    elif c is not None:
        raise ValueError(f"c applies only to L1_0, not {structure_type}")
    else:
        lattice = Lattice.cubic(lattice_constant)
    species = [elements[index] for index, _ in sites]
    positions = [list(position) for _, position in sites]
    return Crystal(species, positions, lattice)


__all__ = ["generate_ordered_alloy", "generate_intermetallic"]
