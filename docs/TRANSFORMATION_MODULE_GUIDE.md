# MatSimPy Transformation Module Guide

## Overview

The `matsimpy.transformation` module provides comprehensive tools for transforming crystal and molecular structures. All transformations support both functional (returns new object) and in-place modes.

## Transformation Categories

### 1. Geometric Transformations

#### Translation

Move structures in space.

```python
from matsimpy import Molecule
from matsimpy.transformation import translate, translate_to_origin

# Create molecule
mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])

# Translate by vector
translated = translate(mol, [5, 5, 5])  # Returns new molecule

# In-place translation
translate(mol, [5, 5, 5], inplace=True)  # Modifies mol

# Translate to origin (center of mass)
centered = translate_to_origin(mol)
```

#### Rotation

Rotate structures around axes.

```python
from matsimpy.transformation import rotate, rotate_around_axis

# Rotate 90 degrees around z-axis
rotated = rotate(mol, angle=90, axis=[0, 0, 1])

# Rotate around specific axis through a point
rotated = rotate_around_axis(mol, axis=[1, 0, 0], angle=45, origin=[0, 0, 0])

# In-place rotation
rotate(mol, 90, [0, 0, 1], inplace=True)
```

### 2. Lattice Operations

Manipulate crystal lattices with various operations.

#### Strain and Deformation

```python
from matsimpy import Crystal, Lattice
from matsimpy.transformation import apply_strain, apply_deformation

crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))

# Apply 1% tensile strain in x direction
strain_tensor = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
strained = apply_strain(crystal, strain_tensor)

# Apply shear deformation
shear_matrix = [[1, 0.1, 0], [0, 1, 0], [0, 0, 1]]
deformed = apply_deformation(crystal, shear_matrix)

# Deform lattice only (keep fractional coordinates)
deformed = apply_deformation(crystal, shear_matrix, deform_positions=False)
```

#### Scaling

```python
from matsimpy.transformation import scale_lattice, set_volume

# Uniform 10% expansion
scaled = scale_lattice(crystal, 1.1)

# Anisotropic scaling
scaled = scale_lattice(crystal, [1.1, 1.0, 0.95])

# Scale to specific volume
scaled = set_volume(crystal, 1000.0)  # Angstrom^3
```

#### Optimization

```python
from matsimpy.transformation import optimize_lattice, standardize_cell

# Optimize to match experimental density
optimized = optimize_lattice(crystal, target_density=2.33)  # g/cm^3

# Optimize to specific volume
optimized = optimize_lattice(crystal, target_volume=500.0)

# Standardize cell using spglib conventions
standardized = standardize_cell(crystal)

# Convert to primitive cell
primitive = standardize_cell(crystal, to_primitive=True)
```

#### Advanced Lattice Operations

```python
from matsimpy.transformation import (
    rotate_lattice, 
    transform_lattice,
    get_niggli_reduced
)
import numpy as np

# Rotate lattice (and atoms)
angle = np.pi / 4
R = [[np.cos(angle), -np.sin(angle), 0],
     [np.sin(angle), np.cos(angle), 0],
     [0, 0, 1]]
rotated = rotate_lattice(crystal, R)

# Apply general transformation
T = [[0.5, 0.5, 0], [0, 0.5, 0.5], [0.5, 0, 0.5]]
transformed = transform_lattice(crystal, T)

# Get Niggli-reduced cell
reduced = get_niggli_reduced(crystal)
```

### 3. Atom Operations

Manipulate individual atoms and groups of atoms.

#### Moving Atoms

```python
from matsimpy.transformation import move_atoms

# Move single atom
moved = move_atoms(crystal, index=0, displacement=[0.1, 0, 0])

# Move multiple atoms
moved = move_atoms(crystal, indices=[0, 1, 2], displacement=[0.1, 0.1, 0])

# Move in fractional coordinates
moved = move_atoms(crystal, 0, [0.05, 0, 0], cartesian=False)

# In-place move
move_atoms(crystal, 0, [0.1, 0, 0], inplace=True)
```

#### Swapping and Merging

```python
from matsimpy.transformation import swap_atoms, merge_atoms

# Swap two atoms (positions and species)
swapped = swap_atoms(crystal, index1=0, index2=1)

# Merge two atoms into one
merged = merge_atoms(crystal, index1=0, index2=1)  # At midpoint

# Merge with specific species and position
merged = merge_atoms(crystal, 0, 1, species='C', position=[0.25, 0.25, 0.25])
```

#### Organizing Atoms

```python
from matsimpy.transformation import sort_atoms, center_structure

# Sort by species (alphabetically)
sorted_struct = sort_atoms(crystal, key='species')

# Sort by atomic number
sorted_struct = sort_atoms(crystal, key='z')

# Sort by distance from origin
sorted_struct = sort_atoms(crystal, key='distance')

# Custom sort function
def custom_key(structure, index):
    return structure.cart_positions[index][2]  # Sort by z coordinate

sorted_struct = sort_atoms(crystal, key=custom_key)

# Center molecule at origin
centered = center_structure(molecule)

# Center at specific point
centered = center_structure(molecule, center=[5, 5, 5])
```

#### Perturbations

```python
from matsimpy.transformation import perturb_positions

# Add random perturbations (for phonon calculations, etc.)
perturbed = perturb_positions(crystal, amplitude=0.1)  # 0.1 Angstrom

# Perturb specific atoms
perturbed = perturb_positions(crystal, amplitude=0.05, indices=[0, 1, 2])

# With random seed for reproducibility
perturbed = perturb_positions(crystal, amplitude=0.1, seed=42)
```

### 4. Chemical Transformations

#### Substitution

```python
from matsimpy.transformation import substitute, substitute_all

# Substitute single atom
substituted = substitute(crystal, index=0, new_species='Ge')

# Substitute all atoms of a species
substituted = substitute_all(crystal, old_species='Si', new_species='Ge')

# In-place substitution
substitute(crystal, 0, 'Ge', inplace=True)
```

#### Supercell

```python
from matsimpy.transformation import make_supercell

# Simple 2x2x2 supercell
supercell = make_supercell(crystal, [2, 2, 2])

# General transformation matrix
supercell = make_supercell(crystal, [[2,0,0], [0,2,0], [0,0,2]])

# In-place (note: creates new atoms, but modifies original object)
make_supercell(crystal, [2, 2, 2], inplace=True)
```

### 5. Composite Transformations

Chain multiple transformations together.

```python
from matsimpy.transformation import chain, apply_transformations

# Chain transformations (executed left to right)
result = chain(
    crystal,
    lambda c: translate(c, [1, 1, 1]),
    lambda c: rotate(c, 90, [0, 0, 1]),
    lambda c: scale_lattice(c, 1.1)
)

# Apply list of transformations
transforms = [
    ('translate', {'displacement': [1, 1, 1]}),
    ('rotate', {'angle': 90, 'axis': [0, 0, 1]}),
    ('scale_lattice', {'scale_factor': 1.1})
]
result = apply_transformations(crystal, transforms)
```

## Common Workflows

### Creating Strained Structures

```python
from matsimpy import Crystal, Lattice
from matsimpy.transformation import apply_strain, make_supercell

# Create base structure
crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))

# Make supercell first
supercell = make_supercell(crystal, [3, 3, 3])

# Apply biaxial strain
strain = [[0.02, 0, 0],   # 2% tensile in a
          [0, 0.02, 0],   # 2% tensile in b  
          [0, 0, -0.01]]  # 1% compressive in c (Poisson effect)
strained = apply_strain(supercell, strain)
```

### Building Complex Structures

```python
from matsimpy.generation import from_prototype, generate_random_alloy
from matsimpy.transformation import make_supercell, perturb_positions

# 1. Start with prototype
bulk = from_prototype('fcc', 'Al', 4.05)

# 2. Make supercell
supercell = make_supercell(bulk, [4, 4, 4])

# 3. Create alloy
alloy = generate_random_alloy(supercell, ['Cu'], 'Al', [0.25])

# 4. Add perturbations (for MD initialization)
perturbed = perturb_positions(alloy, amplitude=0.05, seed=42)
```

### Surface Relaxation Preparation

```python
from matsimpy.generation import generate_slab, add_adsorbate
from matsimpy.transformation import move_atoms, sort_atoms

# Generate slab
slab = generate_slab(bulk, (1,1,1), min_slab_size=15, min_vacuum_size=10)

# Add adsorbate
with_ads = add_adsorbate(slab, 'O', (0.5, 0.5), height=2.0)

# Move adsorbate slightly
final = move_atoms(with_ads, -1, [0, 0, 0.1])  # Last atom

# Sort for organized output
final = sort_atoms(final, key='species')
```

### Defect Creation

```python
from matsimpy.transformation import move_atoms, merge_atoms
from matsimpy import Crystal

# Create vacancy: remove atom
crystal_with_vacancy = crystal.copy()
crystal_with_vacancy.remove_atom(0)

# Create interstitial: add atom
crystal_with_interstitial = crystal.copy()
crystal_with_interstitial.add_atom('Si', [0.25, 0.25, 0.25])

# Create Frenkel pair (vacancy + interstitial)
frenkel = crystal.copy()
frenkel.remove_atom(0)
frenkel.add_atom('Si', [0.6, 0.6, 0.6])

# Create antisite defect (swap species)
from matsimpy.transformation import swap_atoms
antisite = swap_atoms(crystal, 0, 1)
```

## Best Practices

1. **Functional vs In-place:**
   - Use functional style (default) for analysis and exploration
   - Use in-place for memory efficiency with large structures
   - Never mix in-place operations in complex pipelines

2. **Lattice Operations:**
   - Always check volume/density after scaling operations
   - Use `standardize_cell()` before symmetry analysis
   - Consider strain effects on atomic positions

3. **Atom Operations:**
   - Sort atoms before I/O for consistent output
   - Use `seed` parameter for reproducible perturbations
   - Validate structure after manipulations

4. **Chaining:**
   - Chain transformations for cleaner code
   - Be aware that each step creates a new object (unless in-place)
   - Consider memory usage for large structures

5. **Performance:**
   - Batch similar operations when possible
   - Use in-place for memory-intensive workflows
   - Cache intermediate results for repeated use

## Advanced Topics

### Custom Transformations

Create your own transformation functions:

```python
def my_transformation(structure, param1, param2, inplace=False):
    from matsimpy.transformation.base import _copy_structure
    
    if not inplace:
        structure = _copy_structure(structure)
    
    # Your transformation logic here
    # ...
    
    # Invalidate caches
    structure._neighbor_tree = None
    structure._neighbor_tree_positions = None
    
    return structure

# Use like built-in transformations
result = my_transformation(crystal, param1=1.0, param2=2.0)
```

### Transformation Pipelines

```python
class TransformationPipeline:
    def __init__(self):
        self.transforms = []
    
    def add(self, func, **kwargs):
        self.transforms.append((func, kwargs))
        return self
    
    def apply(self, structure):
        result = structure
        for func, kwargs in self.transforms:
            result = func(result, **kwargs)
        return result

# Use pipeline
pipeline = TransformationPipeline()
pipeline.add(translate, displacement=[1,1,1])
pipeline.add(rotate, angle=90, axis=[0,0,1])
pipeline.add(scale_lattice, scale_factor=1.1)

result = pipeline.apply(crystal)
```

## See Also

- [Generation Module Guide](GENERATION_MODULE_GUIDE.md)
- [Core Data Structures](CORE_STRUCTURES.md)
- [API Reference](API_REFERENCE.md)

