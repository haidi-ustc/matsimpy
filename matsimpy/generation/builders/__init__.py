"""
Structure builders (specific structure types).

- slab: Surface/slab generation
- interface: Interface and grain boundary generation
- alloy: Alloy structure generation
- molecule: Molecule-specific builders
"""

from .slab import (
    generate_slab,
    generate_symmetric_slab,
    get_all_slabs,
    add_adsorbate,
)
from .interfaces import (
    generate_interface,
    generate_grain_boundary,
    generate_multilayer,
    find_coincident_sites,
)
from .alloy import (
    generate_random_alloy,
    generate_ordered_alloy,
    generate_sqs_alloy,
    generate_intermetallic,
    calculate_composition,
)
from .molecule import (
    build_linear_molecule,
    build_bent_molecule,
    build_from_smiles,
    build_from_xyz_string,
    combine_molecules,
)

__all__ = [
    # Slab
    'generate_slab',
    'generate_symmetric_slab',
    'get_all_slabs',
    'add_adsorbate',
    
    # Interface
    'generate_interface',
    'generate_grain_boundary',
    'generate_multilayer',
    'find_coincident_sites',
    
    # Alloy
    'generate_random_alloy',
    'generate_ordered_alloy',
    'generate_sqs_alloy',
    'generate_intermetallic',
    'calculate_composition',
    
    # Molecule
    'build_linear_molecule',
    'build_bent_molecule',
    'build_from_smiles',
    'build_from_xyz_string',
    'combine_molecules',
]

