# MatSimPy Generation Module Guide

## Overview

The `matsimpy.generation` module provides comprehensive tools for generating crystal and molecular structures using various strategies and methods.

## Generation Strategies

### 1. Random Generation

Generate structures with random atomic positions while respecting symmetry constraints.

```python
from matsimpy.generation import random_crystal

# Generate random crystal with space group
crystal = random_crystal(
    dim=3,
    group=225,  # Fm-3m
    species=['Si', 'O'],
    num_ions=[2, 4]
)
```

### 2. Symmetry-Based Generation

Generate structures from space groups and point groups.

```python
from matsimpy import Lattice
from matsimpy.generation import generate_from_spacegroup, generate_from_pointgroup

# From space group
lattice = Lattice.cubic(5.0)
crystal = generate_from_spacegroup(
    spacegroup=225,  # Fm-3m
    species=['Na', 'Cl'],
    positions=[[0, 0, 0], [0.5, 0.5, 0.5]],
    lattice=lattice
)

# From point group (for molecules)
from matsimpy import Molecule
mol = Molecule(['H', 'O'], [[0,0,0], [0,0,1]])
symmetric_mol = generate_from_pointgroup('C2v', mol)
```

### 3. Template-Based Generation

Generate structures from common prototypes.

```python
from matsimpy.generation import from_prototype, list_prototypes

# List available prototypes
prototypes = list_prototypes()
# Returns: {'fcc': 'Face-centered cubic', 'bcc': 'Body-centered cubic', ...}

# Generate FCC structure
fcc_cu = from_prototype('fcc', 'Cu', 3.61)

# Generate rocksalt structure
nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)

# Generate perovskite
batio3 = from_prototype('perovskite', ['Ba', 'Ti', 'O'], 4.0)

# Generate wurtzite with c/a ratio
gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
```

**Available Prototypes:**
- `fcc` - Face-centered cubic
- `bcc` - Body-centered cubic  
- `diamond` - Diamond structure
- `zincblende` - Zincblende (sphalerite)
- `rocksalt` - Rocksalt (NaCl)
- `wurtzite` - Wurtzite structure
- `perovskite` - Cubic perovskite ABO₃
- `hcp` - Hexagonal close-packed

**Custom Templates:**

```python
from matsimpy.generation import create_custom_template, TemplateGenerator

# Register custom template
create_custom_template(
    'my_structure',
    species=['X', 'Y'],
    positions=[[0, 0, 0], [0.5, 0.5, 0.5]],
    lattice_type='cubic',
    description='My custom structure'
)

# Use template generator for complex workflows
gen = TemplateGenerator('fcc')
structure = gen.generate(species='Al', lattice_constant=4.05)
```

### 4. AI-Based Generation

Leverage machine learning for structure generation.

```python
from matsimpy.generation import (
    VAEGenerator, 
    GANGenerator,
    generate_with_gnn,
    evolutionary_algorithm
)

# VAE-based generation
vae_gen = VAEGenerator(model_path='path/to/vae.pth')
structures = vae_gen.generate(n_structures=10, temperature=1.0)

# GNN-based generation (e.g., CDVAE, M3GNet)
structures = generate_with_gnn('TiO2', space_group=136, n_samples=5)

# Evolutionary algorithm
def fitness(crystal):
    return -crystal.volume  # Minimize volume

best = evolutionary_algorithm(
    initial_population=population,
    fitness_function=fitness,
    n_generations=100
)
```

## Structure Types

### Surface Slabs

Generate surface slabs from bulk crystals.

```python
from matsimpy import Crystal, Lattice
from matsimpy.generation import generate_slab, add_adsorbate

# Create bulk structure
bulk = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))

# Generate (111) surface slab
slab = generate_slab(
    bulk,
    miller_index=(1, 1, 1),
    min_slab_size=10,      # Angstroms
    min_vacuum_size=15,    # Angstroms
    center_slab=True
)

# Or specify number of layers
slab = generate_slab(bulk, (1,0,0), layers=5, min_vacuum_size=15)

# Generate symmetric slab (same termination both sides)
symmetric_slab = generate_symmetric_slab(bulk, (1,1,0), 15, 10)

# Add adsorbate to surface
with_ads = add_adsorbate(slab, 'O', position=(0.5, 0.5), height=2.0)

# Generate all low-index slabs
from matsimpy.generation import get_all_slabs
slabs = get_all_slabs(bulk, max_index=2, min_slab_size=10, min_vacuum_size=15)
for (h,k,l), slab in slabs:
    print(f"({h},{k},{l}): {len(slab.species)} atoms")
```

### Interfaces and Heterostructures

Generate interfaces between different materials.

```python
from matsimpy.generation import (
    generate_interface,
    generate_grain_boundary,
    generate_multilayer
)

# Si/Ge interface
si = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
ge = Crystal(['Ge'], [[0,0,0]], Lattice.cubic(5.65))

interface = generate_interface(
    si, ge,
    miller1=(0, 0, 1),
    miller2=(0, 0, 1),
    vacuum=5.0
)

# Grain boundary
cu = Crystal(['Cu'], [[0,0,0]], Lattice.cubic(3.61))
gb = generate_grain_boundary(
    cu,
    rotation_axis=(0, 0, 1),
    rotation_angle=36.87,  # Sigma 5
    boundary_plane=(0, 0, 1)
)

# Multilayer (superlattice)
multilayer = generate_multilayer(
    structures=[si, ge, si],
    miller_indices=[(0,0,1), (0,0,1), (0,0,1)],
    layer_thicknesses=[20, 10, 20],
    vacuum_spacings=[0, 0]
)
```

### Alloys

Generate various types of alloy structures.

```python
from matsimpy.generation import (
    generate_random_alloy,
    generate_ordered_alloy,
    generate_sqs_alloy,
    generate_intermetallic,
    calculate_composition
)

# Random alloy
base = Crystal(['Al']*4, [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]], 
               Lattice.cubic(4.0))

# Al-Cu alloy with 50% Cu
alloy = generate_random_alloy(base, ['Cu'], 'Al', [0.5])

# Multi-component alloy: Al-Cu-Mg with 40% Cu, 10% Mg
alloy = generate_random_alloy(base, ['Cu', 'Mg'], 'Al', [0.4, 0.1])

# Ordered alloy (specific substitution pattern)
pattern = {0: 'Au', 1: 'Au', 2: 'Cu', 3: 'Cu'}
ordered = generate_ordered_alloy(base, pattern)

# SQS alloy (Special Quasi-random Structure)
sqs = generate_sqs_alloy(base, ['Ni'], 'Fe', [0.5])

# Intermetallic compounds
fept = generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)
ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)

# Check composition
composition = calculate_composition(alloy)
print(composition)  # {'Cu': 0.5, 'Al': 0.5}
```

## Advanced Usage

### Combining Generation Methods

```python
from matsimpy.generation import from_prototype, generate_slab, generate_random_alloy
from matsimpy.transformation import make_supercell

# 1. Start with prototype
bulk = from_prototype('fcc', 'Al', 4.05)

# 2. Make supercell
supercell = make_supercell(bulk, [2, 2, 2])

# 3. Create alloy
alloy = generate_random_alloy(supercell, ['Cu'], 'Al', [0.25])

# 4. Generate surface
slab = generate_slab(alloy, (1,1,1), min_slab_size=15, min_vacuum_size=10)
```

### Custom Structure Generation

```python
from matsimpy.generation import TemplateGenerator

class MyGenerator(TemplateGenerator):
    def generate_with_defects(self, defect_concentration):
        base = self.generate(species='Si', lattice_constant=5.43)
        # Add custom defect generation logic
        return base

gen = MyGenerator('diamond')
structure = gen.generate_with_defects(0.05)
```

## Tips and Best Practices

1. **Slab Generation:**
   - Use `center_slab=True` for symmetric calculations
   - Ensure sufficient vacuum (typically 10-15 Å)
   - Consider symmetric slabs for accurate surface energies

2. **Interface Generation:**
   - Check lattice mismatch with `strain_tolerance` parameter
   - Use supercells to minimize strain for large mismatches
   - Consider multiple interface configurations

3. **Alloy Generation:**
   - Use `seed` parameter for reproducible random alloys
   - For realistic random alloys, consider SQS method
   - Validate composition with `calculate_composition()`

4. **Template Usage:**
   - List prototypes with `list_prototypes()` to see all options
   - Create custom templates for frequently used structures
   - Use `TemplateGenerator` for complex generation workflows

5. **AI Generation:**
   - Pre-train or load appropriate models for your material system
   - Use constraints to guide generation
   - Validate generated structures with symmetry/energy analysis

## Performance Considerations

- **Slab Generation:** For large slabs, consider using smaller unit cells first
- **Interface Generation:** Lattice matching can be computationally expensive
- **Random Alloys:** Use smaller supercells for testing, then scale up
- **AI Methods:** Model inference time varies; batch generation when possible

## See Also

- [Transformation Module Guide](TRANSFORMATION_MODULE_GUIDE.md)
- [API Reference](API_REFERENCE.md)
- [Examples](../examples/)

