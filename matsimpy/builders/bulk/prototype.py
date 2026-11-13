"""
Prototype-based bulk crystal generation.

Generate crystals from common structural prototypes (FCC, BCC, diamond, etc.).
"""

from matsimpy.utils.tooling import tool
from typing import Dict, List, Optional, Tuple, Union
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
        # P6_3mc, both species on 2b (z = 0 and the ideal u = 3/8)
        "species": ["X", "X", "Y", "Y"],
        "positions": [[1 / 3, 2 / 3, 0], [2 / 3, 1 / 3, 1 / 2], [1 / 3, 2 / 3, 3 / 8], [2 / 3, 1 / 3, 7 / 8]],
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


def _parse_compound_formula(formula: str) -> List[Tuple[str, int]]:
    """Split a formula such as ``'CaTiO3'`` into ``[('Ca', 1), ('Ti', 1), ('O', 3)]``.

    Raises ``ValueError`` for anything that is not a sequence of element symbols
    with optional counts (an element may appear only once).
    """
    tokens = re.findall(r"([A-Z][a-z]*)(\d*)", formula)
    if not tokens or "".join(symbol + count for symbol, count in tokens) != formula:
        raise ValueError(
            f"Could not parse formula '{formula}'. Expected a formula such as 'Cu', 'SiC' or 'CaTiO3'."
        )
    parsed = [(symbol, int(count) if count else 1) for symbol, count in tokens]
    symbols = [symbol for symbol, _ in parsed]
    if len(set(symbols)) != len(symbols):
        raise ValueError(f"Formula '{formula}' repeats an element")
    if any(count == 0 for _, count in parsed):
        raise ValueError(f"Formula '{formula}' has a zero count")
    return parsed


def _reduced(counts: List[int]) -> List[int]:
    divisor = 0
    for count in counts:
        divisor = math.gcd(divisor, count)
    return [count // divisor for count in counts]


def _lattice(prototype: str, lattice_type: str, lattice_constant, c: Optional[float]) -> Lattice:
    values = list(lattice_constant) if isinstance(lattice_constant, (list, tuple, np.ndarray)) else [lattice_constant]
    for value in values + ([] if c is None else [c]):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"Lattice constants must be finite and positive, got {value}")
    if lattice_type == "hexagonal":
        if len(values) not in (1, 2):
            raise ValueError(f"Prototype '{prototype}' takes lattice_constant a or [a, c], got {values}")
        if len(values) == 2 and c is not None:
            raise ValueError("Give c either in lattice_constant or as c, not both")
        a = values[0]
        if len(values) == 2:
            c = values[1]
        elif c is None:
            c = a * math.sqrt(8 / 3)  # ideal c/a
        return Lattice.hexagonal(a, c)
    if len(values) != 1:
        raise ValueError(f"Prototype '{prototype}' takes one lattice constant, got {values}")
    if c is not None:
        raise ValueError(f"c applies only to hexagonal prototypes, not '{prototype}'")
    a = values[0]
    if lattice_type == "cubic":
        return Lattice.cubic(a)
    if prototype in ("fcc", "diamond", "zincblende", "rocksalt"):
        # FCC primitive cell: a / sqrt(2), 60 degree angles
        return Lattice.rhombohedral(a / math.sqrt(2), 60.0)
    # BCC primitive cell: a * sqrt(3) / 2, arccos(-1/3) = 109.47 degree angles
    return Lattice.rhombohedral(a * math.sqrt(3) / 2, math.degrees(math.acos(-1 / 3)))


@tool
def from_prototype(
    prototype: str,
    species: Union[str, List[str]],
    lattice_constant: Union[float, List[float]],
    c: Optional[float] = None,
) -> Crystal:
    """
    Generate crystal from a prototype structure.

    fcc, bcc, diamond, zincblende and rocksalt return the primitive cell;
    lattice_constant is still the conventional cubic constant.

    Args:
        prototype: Name of prototype: fcc, bcc, sc, diamond, zincblende, rocksalt,
            wurtzite, hcp or perovskite (case-insensitive).
        species: Element symbol(s) for the prototype's distinct sites, in order: a
            symbol ('Cu'), a list (['Na', 'Cl']) or a formula ('NaCl', 'CaTiO3') whose
            counts must match the prototype. 'diamond' with two elements ('SiC') gives
            the zincblende arrangement.
        lattice_constant: Conventional lattice constant a in Angstroms, or [a, c] for
            hexagonal prototypes (hcp, wurtzite).
        c: The c lattice constant of a hexagonal prototype; the default is the ideal
            sqrt(8/3) * a.

    Returns:
        Crystal: Generated crystal structure

    Examples:
        >>> from matsimpy.builders.bulk import from_prototype
        >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
        >>> nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        >>> sic = from_prototype('diamond', 'SiC', 4.36)
        >>> gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
        >>> sto = from_prototype('perovskite', 'SrTiO3', 3.905)
    """
    key = prototype.lower() if isinstance(prototype, str) else prototype
    if key not in CRYSTAL_PROTOTYPES:
        raise ValueError(
            f"Unknown prototype '{prototype}'. "
            f"Available: {list(CRYSTAL_PROTOTYPES.keys())}"
        )
    prototype = key
    template = CRYSTAL_PROTOTYPES[prototype]
    template_species = template["species"]
    sites = list(dict.fromkeys(template_species))  # distinct template sites, in order
    site_counts = [template_species.count(site) for site in sites]

    if isinstance(species, str):
        parsed = _parse_compound_formula(species)
        species = [symbol for symbol, _ in parsed]
        counts = [count for _, count in parsed]
    else:
        species = list(species)
        counts = None

    # diamond with two elements: alternate them over the two sites (zincblende order)
    alternate = len(sites) == 1 and len(template_species) == 2 and len(species) == 2
    if alternate:
        sites, site_counts = ["X", "Y"], [1, 1]
    if len(species) != len(sites):
        raise ValueError(
            f"Prototype '{prototype}' requires {len(sites)} species, but {len(species)} provided"
        )
    if counts is not None and len(counts) > 1 and _reduced(counts) != _reduced(site_counts):
        expected = "".join(f"{s}{n if n > 1 else ''}" for s, n in zip(species, _reduced(site_counts)))
        raise ValueError(
            f"Formula counts do not match prototype '{prototype}': expected {expected}"
        )

    lattice = _lattice(prototype, template["lattice_type"], lattice_constant, c)
    if alternate:
        placed = [species[i % 2] for i in range(len(template_species))]
    else:
        mapping = dict(zip(sites, species))
        placed = [mapping[site] for site in template_species]
    crystal = Crystal(template_species, template["positions"], lattice)
    return substitute(crystal, list(range(len(crystal))), placed)


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
