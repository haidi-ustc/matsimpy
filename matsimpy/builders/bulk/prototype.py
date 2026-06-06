"""
Prototype-based bulk crystal generation.

Generate crystals from common structural prototypes (FCC, BCC, diamond, etc.).
"""

from typing import List, Optional, Union, Dict
import numpy as np
import math
import re
from ...core import Crystal, Lattice
from ...transformation.chemical import substitute


# Common crystal structure prototypes
# Note: Many structures use primitive cells (rhombohedral for FCC-based structures)
# to match standard conventions (e.g., ASE)
CRYSTAL_PROTOTYPES = {
    "fcc": {
        "species": ["X"],
        "positions": [[0, 0, 0]],
        "lattice_type": "rhombohedral",  # FCC primitive cell is rhombohedral
        "description": "Face-centered cubic (primitive)",
    },
    "bcc": {
        "species": ["X"],
        "positions": [[0, 0, 0]],
        "lattice_type": "rhombohedral",  # BCC primitive cell is rhombohedral
        "description": "Body-centered cubic (primitive)",
    },
    "diamond": {
        "species": ["X", "X"],
        "positions": [[0, 0, 0], [0.25, 0.25, 0.25]],
        "lattice_type": "rhombohedral",  # Diamond primitive cell is rhombohedral (FCC-based)
        "description": "Diamond structure (primitive)",
    },
    "zincblende": {
        "species": ["X", "Y"],
        "positions": [[0, 0, 0], [0.25, 0.25, 0.25]],
        "lattice_type": "rhombohedral",  # Zincblende primitive cell is rhombohedral (FCC-based)
        "description": "Zincblende (sphalerite) structure (primitive)",
    },
    "rocksalt": {
        "species": ["X", "Y"],
        "positions": [[0, 0, 0], [0.5, 0.5, 0.5]],
        "lattice_type": "rhombohedral",  # Rocksalt primitive cell is rhombohedral
        "description": "Rocksalt (NaCl) structure (primitive)",
    },
    "wurtzite": {
        "species": ["X", "Y"],
        "positions": [[1 / 3, 2 / 3, 0], [1 / 3, 2 / 3, 3 / 8]],
        "lattice_type": "hexagonal",
        "description": "Wurtzite structure",
    },
    "perovskite": {
        "species": ["X", "Y", "O", "O", "O"],
        "positions": [
            [0, 0, 0],
            [0.5, 0.5, 0.5],
            [0.5, 0.5, 0],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ],
        "lattice_type": "cubic",
        "description": "Cubic perovskite ABO3",
    },
    "hcp": {
        "species": ["X", "X"],
        "positions": [[1 / 3, 2 / 3, 1 / 4], [2 / 3, 1 / 3, 3 / 4]],
        "lattice_type": "hexagonal",
        "description": "Hexagonal close-packed",
    },
    "sc": {
        "species": ["X"],
        "positions": [[0, 0, 0]],
        "lattice_type": "cubic",
        "description": "Simple cubic",
    },
}


def _parse_compound_formula(formula: str) -> List[str]:
    """
    Parse a compound formula string into a list of element symbols.

    For binary compounds like "SiC", extracts elements in order: ['Si', 'C']
    For single elements like "Si", returns: ['Si']

    Args:
        formula: Chemical formula string (e.g., 'SiC', 'GaN', 'Si')

    Returns:
        List of element symbols in order

    Examples:
        >>> _parse_compound_formula('SiC')
        ['Si', 'C']
        >>> _parse_compound_formula('GaN')
        ['Ga', 'N']
        >>> _parse_compound_formula('Si')
        ['Si']
    """
    # Pattern to match element symbols (capital letter followed by optional lowercase)
    element_pattern = r"([A-Z][a-z]*)"
    elements = re.findall(element_pattern, formula)

    if not elements:
        raise ValueError(
            f"Could not parse formula '{formula}'. Expected chemical formula like 'SiC' or 'GaN'."
        )

    return elements


def from_prototype(
    prototype: str,
    species: Union[str, List[str]],
    lattice_constant: Union[float, List[float]],
    **kwargs,
) -> Crystal:
    """
    Generate crystal from a prototype structure.

    Args:
        prototype: Name of prototype ('fcc', 'bcc', 'diamond', 'rocksalt', etc.)
        species: Element symbol(s) to substitute into prototype.
                 Can be a single element string ('Si'), list (['Si', 'C']),
                 or binary compound formula ('SiC' for uniform distribution).
        lattice_constant: Lattice constant(s) in Angstroms
        **kwargs: Additional parameters (e.g., c/a ratio for hexagonal)

    Returns:
        Crystal: Generated crystal structure

    Examples:
        >>> from matsimpy.builders.bulk import from_prototype
        >>> # Generate FCC Cu
        >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
        >>> # Generate rocksalt NaCl (list)
        >>> nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        >>> # Generate diamond SiC (binary compound formula)
        >>> sic = from_prototype('diamond', 'SiC', 5.2)
        >>> # Generate wurtzite GaN with c/a ratio
        >>> gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
    """
    if prototype not in CRYSTAL_PROTOTYPES:
        raise ValueError(
            f"Unknown prototype '{prototype}'. "
            f"Available: {list(CRYSTAL_PROTOTYPES.keys())}"
        )

    template = CRYSTAL_PROTOTYPES[prototype]

    # Parse species - support both list and compound formula strings
    if isinstance(species, str):
        # Check if it's a compound formula (multiple elements) or single element
        parsed_elements = _parse_compound_formula(species)
        if len(parsed_elements) > 1:
            # Binary or multi-element compound
            species = parsed_elements
        else:
            # Single element
            species = [species]

    # Substitute species into template
    template_species = template["species"]
    # Preserve order when getting unique elements
    unique_template = []
    for s in template_species:
        if s not in unique_template:
            unique_template.append(s)

    # Validate species count
    # Allow 2 species for single-template types (for uniform binary distribution)
    if len(species) == 2 and len(unique_template) == 1:
        # Binary compound with uniform distribution - will be handled later
        pass
    elif len(species) != len(unique_template):
        raise ValueError(
            f"Prototype '{prototype}' requires {len(unique_template)} species, "
            f"but {len(species)} provided"
        )

    # Create lattice
    lattice_type = template["lattice_type"]
    if lattice_type == "cubic":
        if isinstance(lattice_constant, (list, tuple)):
            lattice_constant = lattice_constant[0]
        lattice = Lattice.cubic(lattice_constant)

    elif lattice_type == "hexagonal":
        if isinstance(lattice_constant, (list, tuple)):
            a, c = lattice_constant[0], lattice_constant[1]
        else:
            a = lattice_constant
            c = kwargs.get("c", a * 1.633)  # Ideal c/a ratio
        # Use convenience method for hexagonal lattice
        lattice = Lattice.hexagonal(a, c)

    elif lattice_type == "rhombohedral":
        # For FCC-based structures (FCC, diamond, zincblende):
        # Primitive cell is rhombohedral with a = a_cubic / sqrt(2), alpha = 60°
        # For BCC primitive: a = a_cubic * sqrt(3) / 2, alpha = arccos(-1/3) ≈ 109.47°
        # For rocksalt primitive: same as FCC
        if isinstance(lattice_constant, (list, tuple)):
            lattice_constant = lattice_constant[0]

        if prototype in ["fcc", "diamond", "zincblende", "rocksalt"]:
            # FCC primitive: b = a_cubic / 2, primitive a = sqrt(2) * b = a_cubic / sqrt(2)
            # Angle between primitive vectors is 60°
            a_prim = lattice_constant / math.sqrt(2)
            alpha = 60.0
        elif prototype == "bcc":
            # BCC primitive: a = a_cubic * sqrt(3) / 2, alpha = arccos(-1/3) ≈ 109.47°
            a_prim = lattice_constant * math.sqrt(3) / 2
            alpha = math.acos(-1 / 3) * 180 / math.pi
        else:
            raise ValueError(f"Unknown rhombohedral prototype: {prototype}")

        lattice = Lattice.rhombohedral(a_prim, alpha)

    else:
        raise NotImplementedError(f"Lattice type '{lattice_type}' not yet implemented")

    # Create structure with template species (placeholders)
    crystal = Crystal(template_species, template["positions"], lattice)

    # Use transformation module to substitute species
    # For binary compounds with uniform distribution (e.g., diamond with "SiC")
    if len(species) == 2 and len(unique_template) == 1:
        # Distribute uniformly: alternate between the two elements
        indices_to_substitute = []
        new_species_list = []
        for i, spec in enumerate(crystal.species):
            # Alternate between first and second element
            element_idx = i % len(species)
            indices_to_substitute.append(i)
            new_species_list.append(species[element_idx])
        # Substitute all at once for efficiency
        crystal = substitute(
            crystal, indices_to_substitute, new_species_list
        )
    else:
        # Use dict-based substitution for binary templates (X->species[0], Y->species[1])
        substitution_map = {unique_template[i]: species[i] for i in range(len(species))}
        crystal = substitute(
            crystal, list(range(len(crystal))), substitution_map
        )

    # Formula and composition are now properties that automatically update
    # when species change, so no manual update is needed

    return crystal


def list_prototypes() -> Dict[str, str]:
    """
    List all available crystal prototypes.

    Returns:
        Dictionary mapping prototype names to descriptions

    Examples:
        >>> from matsimpy.builders.bulk import list_prototypes
        >>> prototypes = list_prototypes()
        >>> for name, desc in prototypes.items():
        ...     print(f"{name}: {desc}")
    """
    return {name: info["description"] for name, info in CRYSTAL_PROTOTYPES.items()}


__all__ = ["from_prototype", "list_prototypes", "CRYSTAL_PROTOTYPES"]
