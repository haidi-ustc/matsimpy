"""
Template-based structure generation.

This module provides functions for generating structures from templates and prototypes.
Includes common crystal prototypes, molecular templates, and custom template systems.
"""

from typing import List, Optional, Union, Dict, Callable
import numpy as np
from ..core import Crystal, Lattice, Molecule


# Common crystal structure prototypes
CRYSTAL_PROTOTYPES = {
    'fcc': {
        'species': ['X'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Face-centered cubic'
    },
    'bcc': {
        'species': ['X'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Body-centered cubic'
    },
    'diamond': {
        'species': ['X', 'X'],
        'positions': [[0, 0, 0], [0.25, 0.25, 0.25]],
        'lattice_type': 'cubic',
        'description': 'Diamond structure'
    },
    'zincblende': {
        'species': ['X', 'Y'],
        'positions': [[0, 0, 0], [0.25, 0.25, 0.25]],
        'lattice_type': 'cubic',
        'description': 'Zincblende (sphalerite) structure'
    },
    'rocksalt': {
        'species': ['X', 'Y'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Rocksalt (NaCl) structure'
    },
    'wurtzite': {
        'species': ['X', 'Y'],
        'positions': [[1/3, 2/3, 0], [1/3, 2/3, 3/8]],
        'lattice_type': 'hexagonal',
        'description': 'Wurtzite structure'
    },
    'perovskite': {
        'species': ['X', 'Y', 'O', 'O', 'O'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Cubic perovskite ABO3'
    },
    'hcp': {
        'species': ['X', 'X'],
        'positions': [[1/3, 2/3, 1/4], [2/3, 1/3, 3/4]],
        'lattice_type': 'hexagonal',
        'description': 'Hexagonal close-packed'
    },
}


def from_prototype(
    prototype: str,
    species: Union[str, List[str]],
    lattice_constant: Union[float, List[float]],
    **kwargs
) -> Crystal:
    """
    Generate crystal from a prototype structure.
    
    Args:
        prototype: Name of prototype ('fcc', 'bcc', 'diamond', 'rocksalt', etc.)
        species: Element symbol(s) to substitute into prototype
        lattice_constant: Lattice constant(s) in Angstroms
        **kwargs: Additional parameters (e.g., c/a ratio for hexagonal)
    
    Returns:
        Crystal: Generated crystal structure
        
    Examples:
        >>> from matsimpy.generation.template import from_prototype
        >>> # Generate FCC Cu
        >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
        >>> # Generate rocksalt NaCl
        >>> nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        >>> # Generate wurtzite GaN with c/a ratio
        >>> gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
    """
    if prototype not in CRYSTAL_PROTOTYPES:
        raise ValueError(
            f"Unknown prototype '{prototype}'. Available: {list(CRYSTAL_PROTOTYPES.keys())}"
        )
    
    template = CRYSTAL_PROTOTYPES[prototype]
    
    # Parse species
    if isinstance(species, str):
        species = [species]
    
    # Substitute species into template
    template_species = template['species']
    unique_template = list(set(template_species))
    
    if len(species) != len(unique_template):
        raise ValueError(
            f"Prototype '{prototype}' requires {len(unique_template)} species, "
            f"but {len(species)} provided"
        )
    
    # Create species mapping
    species_map = {unique_template[i]: species[i] for i in range(len(species))}
    final_species = [species_map[s] for s in template_species]
    
    # Create lattice
    lattice_type = template['lattice_type']
    if lattice_type == 'cubic':
        if isinstance(lattice_constant, (list, tuple)):
            lattice_constant = lattice_constant[0]
        lattice = Lattice.cubic(lattice_constant)
    
    elif lattice_type == 'hexagonal':
        if isinstance(lattice_constant, (list, tuple)):
            a, c = lattice_constant[0], lattice_constant[1]
        else:
            a = lattice_constant
            c = kwargs.get('c', a * 1.633)  # Ideal c/a ratio
        lattice = Lattice.hexagonal(a, c)
    
    else:
        raise NotImplementedError(f"Lattice type '{lattice_type}' not yet implemented")
    
    return Crystal(final_species, template['positions'], lattice)


def from_template_file(
    filepath: str,
    substitutions: Optional[Dict[str, str]] = None,
    scale: float = 1.0,
    **kwargs
) -> Crystal:
    """
    Load structure from template file and apply substitutions.
    
    Args:
        filepath: Path to template structure file
        substitutions: Dictionary mapping template species to actual species
        scale: Scaling factor for lattice constants
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Generated structure from template
        
    Examples:
        >>> from matsimpy.generation.template import from_template_file
        >>> crystal = from_template_file('template.vasp', {'X': 'Fe', 'Y': 'O'})
    """
    # Load template
    crystal = Crystal.from_file(filepath)
    
    # Apply substitutions
    if substitutions:
        for old_spec, new_spec in substitutions.items():
            indices = [i for i, s in enumerate(crystal.species) if s == old_spec]
            for idx in indices:
                crystal.species = (
                    crystal.species[:idx] + 
                    (new_spec,) + 
                    crystal.species[idx+1:]
                )
    
    # Scale lattice
    if scale != 1.0:
        new_vectors = crystal.lattice.lattice_vectors * scale
        crystal.lattice = Lattice(new_vectors)
    
    return crystal


def create_custom_template(
    name: str,
    species: List[str],
    positions: List[List[float]],
    lattice_type: str,
    description: str = ""
) -> None:
    """
    Register a custom template for future use.
    
    Args:
        name: Template name
        species: List of species (use 'X', 'Y', 'Z' for generic)
        positions: Fractional positions
        lattice_type: 'cubic', 'hexagonal', etc.
        description: Template description
        
    Examples:
        >>> from matsimpy.generation.template import create_custom_template
        >>> create_custom_template(
        ...     'my_structure',
        ...     ['X', 'Y'],
        ...     [[0, 0, 0], [0.5, 0.5, 0.5]],
        ...     'cubic',
        ...     'My custom structure'
        ... )
    """
    CRYSTAL_PROTOTYPES[name] = {
        'species': species,
        'positions': positions,
        'lattice_type': lattice_type,
        'description': description
    }


def list_prototypes() -> Dict[str, str]:
    """
    List all available crystal prototypes.
    
    Returns:
        Dictionary mapping prototype names to descriptions
        
    Examples:
        >>> from matsimpy.generation.template import list_prototypes
        >>> prototypes = list_prototypes()
        >>> for name, desc in prototypes.items():
        ...     print(f"{name}: {desc}")
    """
    return {name: info['description'] for name, info in CRYSTAL_PROTOTYPES.items()}


class TemplateGenerator:
    """
    Advanced template-based structure generator with customization.
    
    Allows for complex template manipulations and parameterized generation.
    """
    
    def __init__(self, template: Union[str, Crystal]):
        """
        Initialize template generator.
        
        Args:
            template: Prototype name or Crystal object to use as template
        """
        if isinstance(template, str):
            if template not in CRYSTAL_PROTOTYPES:
                raise ValueError(f"Unknown prototype: {template}")
            self.template_name = template
            self.template_data = CRYSTAL_PROTOTYPES[template]
            self.template = None  # Will be generated on demand
        else:
            self.template_name = "custom"
            self.template_data = None
            self.template = template
    
    def generate(
        self,
        species: Optional[Union[str, List[str]]] = None,
        lattice_constant: Optional[Union[float, List[float]]] = None,
        substitutions: Optional[Dict[str, str]] = None,
        scale: float = 1.0,
        **kwargs
    ) -> Crystal:
        """
        Generate structure from template with parameters.
        
        Args:
            species: Species to use (for prototypes)
            lattice_constant: Lattice constant(s)
            substitutions: Species substitutions
            scale: Scaling factor
            **kwargs: Additional parameters
        
        Returns:
            Generated crystal structure
        """
        if self.template_data is not None:
            # Generate from prototype
            if species is None or lattice_constant is None:
                raise ValueError("species and lattice_constant required for prototype")
            crystal = from_prototype(self.template_name, species, lattice_constant, **kwargs)
        else:
            # Use existing template
            crystal = self.template.copy()
            
            # Apply substitutions
            if substitutions:
                for old_spec, new_spec in substitutions.items():
                    indices = [i for i, s in enumerate(crystal.species) if s == old_spec]
                    for idx in indices:
                        crystal.species = (
                            crystal.species[:idx] + 
                            (new_spec,) + 
                            crystal.species[idx+1:]
                        )
            
            # Scale lattice
            if scale != 1.0:
                new_vectors = crystal.lattice.lattice_vectors * scale
                crystal.lattice = Lattice(new_vectors)
        
        return crystal
    
    def with_defects(
        self,
        crystal: Crystal,
        defect_type: str,
        concentration: float,
        **kwargs
    ) -> Crystal:
        """
        Add defects to generated structure.
        
        Args:
            crystal: Base crystal structure
            defect_type: 'vacancy', 'interstitial', 'substitutional'
            concentration: Defect concentration (0-1)
            **kwargs: Additional defect parameters
        
        Returns:
            Crystal with defects
        """
        # Placeholder for defect generation
        return crystal


__all__ = [
    'CRYSTAL_PROTOTYPES',
    'from_prototype',
    'from_template_file',
    'create_custom_template',
    'list_prototypes',
    'TemplateGenerator',
]

