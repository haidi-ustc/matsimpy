"""
Random alloy generation.

Generate random solid solution alloys with specified compositions.
"""

from typing import List, Optional
import numpy as np
from ...core import Crystal
from ...transformation.chemical.substitution import substitute


def generate_random_alloy(
    base_structure: Crystal,
    substitution_species: List[str],
    site_species: str,
    concentrations: Optional[List[float]] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> Crystal:
    """
    Generate random alloy by substituting atoms.

    Args:
        base_structure: Base crystal structure
        substitution_species: List of species to substitute
        site_species: Species to replace
        concentrations: Fractions of site_species to replace with each substitution_species.
                       Can sum to <=1.0 (remainder stays as site_species)
        seed: Random seed for reproducibility
        **kwargs: Additional parameters

    Returns:
        Crystal: Random alloy structure

    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.builders.alloy import generate_random_alloy
        >>> base = Crystal(['Al']*4, [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]],
        ...                Lattice.cubic(4.0))
        >>> # Al-Cu alloy: 50% Cu, 50% Al
        >>> alloy = generate_random_alloy(base, ['Cu'], 'Al', [0.5])
        >>> # Al-Cu-Mg alloy: 40% Cu, 10% Mg, 50% Al
        >>> alloy = generate_random_alloy(base, ['Cu', 'Mg'], 'Al', [0.4, 0.1])
    """
    if seed is not None:
        np.random.seed(seed)

    # Default equal concentrations if not specified
    if concentrations is None:
        concentrations = [1.0 / len(substitution_species)] * len(substitution_species)

    # Validate concentrations
    if len(concentrations) != len(substitution_species):
        raise ValueError(
            "Number of concentrations must match number of substitution species"
        )

    if sum(concentrations) > 1.0:
        raise ValueError(f"Concentrations cannot exceed 1.0, got {sum(concentrations)}")

    # Find all sites with the target species
    site_indices = [
        i for i, spec in enumerate(base_structure.species) if spec == site_species
    ]
    n_sites = len(site_indices)

    if n_sites == 0:
        raise ValueError(f"No sites with species '{site_species}' found")

    # Calculate number of each substitution
    n_substitutions = [int(np.round(conc * n_sites)) for conc in concentrations]

    # Total sites to substitute
    total_to_substitute = sum(n_substitutions)

    # Create substitution list for only the sites being substituted
    substitution_list = []
    for spec, n in zip(substitution_species, n_substitutions):
        substitution_list.extend([spec] * n)

    # Randomly select which sites to substitute
    sites_to_substitute = np.random.choice(
        site_indices, size=total_to_substitute, replace=False
    )

    # Shuffle substitution list
    np.random.shuffle(substitution_list)

    # Use transformation function for substitution
    return substitute(
        base_structure, sites_to_substitute, substitution_list
    )


__all__ = ["generate_random_alloy"]
