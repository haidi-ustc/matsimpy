# Substitution API - Complete Feature Summary

## Overview

The substitution functionality in MatSimPy now supports three powerful features:
1. **AtomSelection** - Fluent, chainable selection API
2. **Dict Mapping** - Species-to-species mapping for readability
3. **Traditional API** - Backward compatible with indices and lists

## Supported Input Types

### For `indices` parameter:
- `int` - Single atom index
- `List[int]` - List of atom indices
- `AtomSelection` - Selection object (recommended)

### For `new_species` parameter:
- `str` - Single species (applied to all selected atoms)
- `List[str]` - List of species (one per atom)
- `Dict[str, str]` - Mapping from old species to new species (e.g., `{'Si': 'Ge', 'O': 'S'}`)

## Usage Examples

### 1. Simple Substitution (Traditional)

```python
from matsimpy.core import Crystal, Lattice

crystal = Crystal(['Si', 'O', 'Si'], [[0,0,0], [5,0,0], [10,0,0]], 
                  Lattice.cubic(20), coords_are_cartesian=True)

# Single atom
crystal.substitute(0, 'Ge')

# Multiple atoms with explicit list
crystal.substitute([0, 2], ['Ge', 'Ge'])
```

### 2. AtomSelection (Recommended)

```python
from matsimpy.utils.selection import AtomSelection

# Simple selection
sel = AtomSelection(crystal).by_species('Si')
crystal.substitute(sel, 'Ge')

# Chained selection
sel = AtomSelection(crystal).by_species('Si').near([0,0,0], 5.0)
crystal.substitute(sel, 'Ge')

# Combined selections
sel1 = AtomSelection(crystal).by_species('Si')
sel2 = AtomSelection(crystal).near([0,0,0], 5.0)
combined = sel1 & sel2  # Intersection
crystal.substitute(combined, 'Ge')
```

### 3. Dict Mapping (Recommended for Multi-Species)

```python
# Dict mapping: automatically maps old species to new species
crystal.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})
# Result: Si->Ge, O->S for all selected atoms

# More readable than:
# crystal.substitute([0, 1, 2], ['Ge', 'S', 'Ge'])  # Need to know order
```

### 4. AtomSelection + Dict Mapping (Best of Both)

```python
# Select Si atoms and substitute with Ge
sel = AtomSelection(crystal).by_species('Si')
crystal.substitute(sel, {'Si': 'Ge'})

# Select all atoms and use dict mapping
sel = AtomSelection(crystal)  # All atoms
crystal.substitute(sel, {'Si': 'Ge', 'O': 'S'})

# Complex: Si atoms near surface
sel = AtomSelection(crystal).by_species('Si').near([0,0,0], 5.0)
crystal.substitute(sel, {'Si': 'Ge'})
```

### 5. Transformation Module (Functional Style)

```python
from matsimpy.transformation import substitute
from matsimpy.utils.selection import AtomSelection

# Preserves original (returns new structure)
sel = AtomSelection(crystal).by_species('Si')
new_crystal = substitute(crystal, sel, 'Ge')

# With dict mapping
new_crystal = substitute(crystal, sel, {'Si': 'Ge'})

# In-place
substitute(crystal, sel, 'Ge', inplace=True)
```

## Complete API Reference

### Structure.substitute()

```python
def substitute(
    indices: Union[int, List[int], AtomSelection],
    new_species: Union[str, List[str], Dict[str, str]]
) -> None:
    """
    Substitute atoms with new species.
    
    Args:
        indices: Atom index, list of indices, or AtomSelection object
        new_species: Species string, list of species, or dict mapping old->new
        
    Examples:
        # All these work:
        crystal.substitute(0, 'Ge')
        crystal.substitute([0, 1], ['Ge', 'Ge'])
        crystal.substitute(sel, 'Ge')
        crystal.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})
        crystal.substitute(sel, {'Si': 'Ge'})
    """
```

### transformation.substitute()

```python
def substitute(
    structure: Union[Crystal, Molecule],
    indices: Union[int, List[int], AtomSelection],
    new_species: Union[str, List[str], Dict[str, str]],
    inplace: bool = False
) -> Union[Crystal, Molecule]:
    """
    Functional interface for substitution.
    
    Args:
        structure: Structure to modify
        indices: Atom index, list, or AtomSelection
        new_species: Species string, list, or dict mapping
        inplace: If True, modify in-place (default: False)
        
    Returns:
        Modified structure (new if inplace=False, same if inplace=True)
    """
```

## Comparison Table

| Feature | Traditional | AtomSelection | Dict Mapping |
|---------|------------|---------------|--------------|
| **Single atom** | `substitute(0, 'Ge')` | `substitute(sel, 'Ge')` | `substitute(0, 'Ge')` |
| **Multiple atoms** | `substitute([0,1], ['Ge','Ge'])` | `substitute(sel, 'Ge')` | `substitute([0,1], {'Si':'Ge'})` |
| **Multi-species** | `substitute([0,1], ['Ge','S'])` | `substitute(sel, {'Si':'Ge','O':'S'})` | `substitute([0,1], {'Si':'Ge','O':'S'})` |
| **Complex selection** | ❌ Verbose | ✅ Fluent | ✅ Works with AtomSelection |
| **Readability** | ⚠️ Medium | ✅ High | ✅ Very High |
| **Flexibility** | ⚠️ Limited | ✅ High | ✅ High |

## Best Practices

### 1. Use AtomSelection for Selection
```python
# ✅ Recommended
sel = AtomSelection(crystal).by_species('Si').near([0,0,0], 5.0)
crystal.substitute(sel, 'Ge')

# ⚠️ Less elegant
si_indices = select_by_species(crystal, 'Si')
near_indices = select_by_position(crystal, [0,0,0], 5.0)
combined = combine_selections([si_indices, near_indices], 'intersection')
crystal.substitute(combined, ['Ge'] * len(combined))
```

### 2. Use Dict Mapping for Multi-Species
```python
# ✅ Recommended - More readable
crystal.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})

# ⚠️ Less readable - Need to know species order
crystal.substitute([0, 1, 2], ['Ge', 'S', 'Ge'])
```

### 3. Combine AtomSelection + Dict
```python
# ✅ Best practice - Clear and readable
sel = AtomSelection(crystal).by_species('Si')
crystal.substitute(sel, {'Si': 'Ge'})
```

## Error Handling

### KeyError: Missing Species in Dict
```python
# If dict doesn't contain a species, raises KeyError
try:
    crystal.substitute([0, 1], {'Si': 'Ge'})  # Missing 'O'
except KeyError as e:
    print(f"Error: {e}")  # "Species 'O' at index 1 not found in substitution mapping"
```

### ValueError: Wrong Structure
```python
# AtomSelection must be from the same structure
crystal1 = Crystal(...)
crystal2 = Crystal(...)
sel = AtomSelection(crystal1).by_species('Si')
try:
    crystal2.substitute(sel, 'Ge')  # Wrong structure
except ValueError as e:
    print(f"Error: {e}")  # "AtomSelection must be created from this structure"
```

## Summary

The substitution API now supports:
- ✅ **AtomSelection** - Fluent, chainable selection
- ✅ **Dict Mapping** - Species-to-species mapping
- ✅ **Traditional API** - Backward compatible
- ✅ **All combinations** - AtomSelection + Dict, etc.
- ✅ **Works everywhere** - Crystal, Molecule, transformation module

**Recommended usage:**
```python
from matsimpy.utils.selection import AtomSelection

# Select atoms
sel = AtomSelection(crystal).by_species('Si').near([0,0,0], 5.0)

# Substitute with dict mapping
crystal.substitute(sel, {'Si': 'Ge'})
```

This provides the cleanest, most readable, and most maintainable code!

