# Atom Selection Guide

## Overview

MatSimPy provides flexible atom selection utilities that can be used for substitution, analysis, transformations, and other operations. The selection functions are located in `matsimpy.utils.selection`.

**Two approaches are available:**
1. **Functional functions** - Direct function calls for compatibility
2. **AtomSelection class** - Fluent, chainable API (recommended for new code)

## AtomSelection Class (Recommended)

The `AtomSelection` class provides a fluent, chainable API that is more elegant and easier to use:

```python
from matsimpy.utils.selection import AtomSelection
from matsimpy.core import Crystal, Lattice

crystal = Crystal(['Si', 'O', 'Si'], [[0,0,0], [5,0,0], [10,0,0]], 
                  Lattice.cubic(20), coords_are_cartesian=True)

# Simple selection and substitution
sel = AtomSelection(crystal).by_species('Si')
crystal.substitute(sel, 'Ge')

# Chaining multiple criteria
sel = AtomSelection(crystal).by_species('Si').near([0,0,0], 5.0)
crystal.substitute(sel, 'Ge')

# Using operators for combination
sel1 = AtomSelection(crystal).by_species('Si')
sel2 = AtomSelection(crystal).near([0,0,0], 5.0)
combined = sel1 & sel2  # Intersection (AND)
crystal.substitute(combined, 'Ge')
```

### AtomSelection Methods

All selection methods return `self` for chaining:
- `by_species(species)` - Filter by species
- `by_indices(indices)` - Filter by indices
- `near(center, radius)` - Filter by position (within radius)
- `in_box(min_coords, max_coords)` - Filter by box
- `by_property(key, value=None, condition=None)` - Filter by properties
- `by_custom(condition)` - Filter by custom condition

### AtomSelection Operators

- `sel1 & sel2` - Intersection (AND)
- `sel1 | sel2` - Union (OR)
- `sel1 - sel2` - Difference (subtract)

### AtomSelection Properties

- `sel.indices` - Get list of selected indices
- `len(sel)` - Number of selected atoms
- `bool(sel)` - True if any atoms selected
- `iter(sel)` - Iterate over indices

## Functional Functions (Legacy/Alternative)

## Selection Functions

### Basic Selection

#### `select_by_species(structure, species)`
Select atoms by species.

```python
from matsimpy.utils.selection import select_by_species
from matsimpy.core import Crystal, Lattice

crystal = Crystal(['Si', 'O', 'Si'], [[0,0,0], [0.5,0,0], [0,0.5,0]], Lattice.cubic(10))

# Select all Si atoms
si_indices = select_by_species(crystal, 'Si')  # [0, 2]

# Select multiple species
si_o_indices = select_by_species(crystal, ['Si', 'O'])  # [0, 1, 2]
```

#### `select_by_indices(structure, indices)`
Select atoms by index (with validation).

```python
from matsimpy.utils.selection import select_by_indices

# Select specific atoms
indices = select_by_indices(crystal, [0, 2])  # [0, 2]
```

#### `select_by_position(structure, center, radius, use_cartesian=True)`
Select atoms within a radius of a center point.

```python
from matsimpy.utils.selection import select_by_position

# Select atoms within 5 Å of origin
indices = select_by_position(crystal, [0, 0, 0], 5.0)

# Select using fractional coordinates (Crystal only)
indices = select_by_position(crystal, [0.5, 0.5, 0.5], 0.1, use_cartesian=False)
```

#### `select_by_box(structure, min_coords, max_coords, use_cartesian=True)`
Select atoms within a rectangular box.

```python
from matsimpy.utils.selection import select_by_box

# Select atoms in a box
indices = select_by_box(crystal, [0, 0, 0], [5, 5, 5])
```

#### `select_by_property(structure, property_key, value=None, condition=None)`
Select atoms by site properties.

```python
from matsimpy.utils.selection import select_by_property

# Select atoms with a property
indices = select_by_property(crystal, 'charge')

# Select atoms with specific property value
indices = select_by_property(crystal, 'charge', value=-2)

# Select atoms with property condition
indices = select_by_property(crystal, 'charge', condition=lambda x: x > 0)
```

#### `select_by_custom(structure, condition)`
Select atoms using a custom condition function.

```python
from matsimpy.utils.selection import select_by_custom

# Select every other atom
indices = select_by_custom(crystal, lambda i: i % 2 == 0)

# Select atoms with even indices
indices = select_by_custom(crystal, lambda i: i % 2 == 0)
```

### Utility Functions

#### `select_all(structure)`
Select all atoms.

```python
from matsimpy.utils.selection import select_all

indices = select_all(crystal)  # [0, 1, 2, ...]
```

#### `select_none(structure)`
Select no atoms (empty selection).

```python
from matsimpy.utils.selection import select_none

indices = select_none(crystal)  # []
```

### Combining Selections

#### `combine_selections(indices_list, operation='union')`
Combine multiple selections using set operations.

```python
from matsimpy.utils.selection import (
    select_by_species, select_by_position, combine_selections
)

# Select Si atoms
si_indices = select_by_species(crystal, 'Si')

# Select atoms near origin
near_indices = select_by_position(crystal, [0, 0, 0], 5.0)

# Union: Si atoms OR near origin (all atoms matching either condition)
all_indices = combine_selections([si_indices, near_indices], 'union')

# Intersection: Si atoms AND near origin (atoms matching both conditions)
both_indices = combine_selections([si_indices, near_indices], 'intersection')

# Difference: Si atoms NOT near origin
diff_indices = combine_selections([si_indices, near_indices], 'difference')
```

## Usage Examples

### Example 1: Substitution Based on Selection

```python
from matsimpy.core import Crystal, Lattice
from matsimpy.utils.selection import AtomSelection

crystal = Crystal(['Si', 'O', 'Si'], [[0,0,0], [5,0,0], [10,0,0]], 
                  Lattice.cubic(20), coords_are_cartesian=True)

# Using AtomSelection (recommended)
sel = AtomSelection(crystal).by_species('Si').near([0, 0, 0], 5.0)
crystal.substitute(sel, 'Ge')  # Simple substitution

# Or using dict mapping (maps old species to new species)
crystal.substitute(sel, {'Si': 'Ge'})  # More explicit
```

### Example 2: Complex Selection for Analysis

```python
from matsimpy.utils.selection import AtomSelection

# Select all Si atoms with positive charge (using AtomSelection)
sel = AtomSelection(crystal).by_species('Si').by_property('charge', condition=lambda x: x > 0)

# Use for analysis
for idx in sel:
    print(f"Atom {idx}: {crystal.species[idx]}, charge: {crystal.site_properties[idx]['charge']}")
```

### Example 3: Selection for Transformation

```python
from matsimpy.transformation import substitute
from matsimpy.utils.selection import AtomSelection

# Select atoms in a specific region (using AtomSelection)
sel = AtomSelection(crystal).in_box([0, 0, 0], [5, 5, 5])

# Substitute them functionally (preserves original)
new_crystal = substitute(crystal, sel, 'Ge')  # Simple substitution
# Or with dict mapping
new_crystal = substitute(crystal, sel, {'Si': 'Ge', 'O': 'S'})  # Dict mapping
```

### Example 4: Multiple Criteria Selection

```python
from matsimpy.utils.selection import AtomSelection

# Complex selection: Si atoms, near surface, with charge > 0 (using AtomSelection)
sel = AtomSelection(crystal).by_species('Si').near([0, 0, 0], 5.0).by_property('charge', condition=lambda x: x > 0)

# Or using operators
sel1 = AtomSelection(crystal).by_species('Si')
sel2 = AtomSelection(crystal).near([0, 0, 0], 5.0)
sel3 = AtomSelection(crystal).by_property('charge', condition=lambda x: x > 0)
combined = sel1 & sel2 & sel3

# Substitute with dict mapping
crystal.substitute(combined, {'Si': 'Ge'})
```

## Best Practices

1. **Use AtomSelection for cleaner code**: AtomSelection provides fluent API
   ```python
   # Recommended: Using AtomSelection
   sel = AtomSelection(crystal).by_species('Si')
   crystal.substitute(sel, 'Ge')
   
   # Or with dict mapping
   crystal.substitute(sel, {'Si': 'Ge'})
   
   # Legacy: Using functional functions
   indices = select_by_species(crystal, 'Si')
   crystal.substitute(indices, ['Ge'] * len(indices))
   ```
   
2. **Use dict mapping for multi-species substitution**: More readable than lists
   ```python
   # Dict mapping: maps old species to new species
   crystal.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})
   
   # vs explicit list (less readable)
   crystal.substitute([0, 1, 2], ['Ge', 'S', 'Ge'])
   ```

2. **Combine selections for complex criteria**: Use `combine_selections` for AND/OR logic
   ```python
   combined = combine_selections([sel1, sel2], 'intersection')
   ```

3. **Validate selections**: Check that selections are not empty before using
   ```python
   indices = select_by_species(crystal, 'Si')
   if indices:
       crystal.substitute(indices, ['Ge'] * len(indices))
   ```

4. **Use for both Crystal and Molecule**: All selection functions work with both
   ```python
   mol_indices = select_by_species(molecule, 'C')
   crystal_indices = select_by_species(crystal, 'Si')
   ```

5. **Coordinate systems**: Be aware of Cartesian vs fractional coordinates
   ```python
   # Cartesian (default)
   indices = select_by_position(crystal, [0, 0, 0], 5.0)
   
   # Fractional (Crystal only)
   indices = select_by_position(crystal, [0.5, 0.5, 0.5], 0.1, use_cartesian=False)
   ```

## Integration with Other Modules

### Transformation Module
```python
from matsimpy.transformation import substitute
from matsimpy.utils.selection import AtomSelection

# Using AtomSelection
sel = AtomSelection(crystal).by_species('Si')
new_crystal = substitute(crystal, sel, 'Ge')  # Simple
new_crystal = substitute(crystal, sel, {'Si': 'Ge'})  # Dict mapping

# Or functional style
from matsimpy.utils.selection import select_by_species
indices = select_by_species(crystal, 'Si')
new_crystal = substitute(crystal, indices, ['Ge'] * len(indices))
```

### Analysis Module
```python
from matsimpy.utils.selection import select_by_species

# Analyze specific atoms
si_indices = select_by_species(crystal, 'Si')
for idx in si_indices:
    # Perform analysis on Si atoms
    pass
```

## Summary

The selection utilities provide a flexible and powerful way to identify atoms for various operations. They can be combined to create complex selection criteria and work seamlessly with substitution, transformation, and analysis operations.

