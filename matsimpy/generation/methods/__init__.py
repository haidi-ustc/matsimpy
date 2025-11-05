"""
Generation methods (strategies for creating structures).

- random: Random structure generation with symmetry constraints
- symmetry: Space group and point group based generation
- template: Prototype-based generation (FCC, BCC, etc.)
- ai: ML-based generation (VAE, GAN, diffusion)
"""

from .random import random_crystal
from .symmetry import (
    generate_from_spacegroup,
    generate_from_pointgroup,
    apply_symmetry_operations,
    get_symmetry_operations,
)
from .template import (
    CRYSTAL_PROTOTYPES,
    from_prototype,
    from_template_file,
    create_custom_template,
    list_prototypes,
    TemplateGenerator,
)
from .ai import (
    StructureGenerator,
    VAEGenerator,
    GANGenerator,
    DiffusionGenerator,
    generate_with_gnn,
    evolutionary_algorithm,
    structure_prediction,
)

__all__ = [
    # Random
    'random_crystal',
    
    # Symmetry
    'generate_from_spacegroup',
    'generate_from_pointgroup',
    'apply_symmetry_operations',
    'get_symmetry_operations',
    
    # Template
    'CRYSTAL_PROTOTYPES',
    'from_prototype',
    'from_template_file',
    'create_custom_template',
    'list_prototypes',
    'TemplateGenerator',
    
    # AI
    'StructureGenerator',
    'VAEGenerator',
    'GANGenerator',
    'DiffusionGenerator',
    'generate_with_gnn',
    'evolutionary_algorithm',
    'structure_prediction',
]

