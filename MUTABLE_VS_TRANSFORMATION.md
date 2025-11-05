# Mutable Methods vs Transformation Module - Relationship Clarification

## Overview

MatSimPy provides **two complementary approaches** for structure manipulation:

1. **In-Place Methods** (Class methods) - Direct manipulation
2. **Transformation Module** (Functional interface) - Composable transformations

Both approaches are valid and serve different use cases.

## Architecture

### Class Methods (In-Place, Mutable)

**Location**: `Crystal` and `Molecule` classes in `matsimpy/core/`

**Methods**:
- `add_atom(species, position, site_properties=None)` - Add atom to structure
- `remove_atom(index)` - Remove atom from structure
- `translate(vector)` - Translate molecule (Molecule only)
- `rotate(angle, axis)` - Rotate molecule (Molecule only)

**Characteristics**:
- ✅ Modify structure in-place
- ✅ Memory efficient (no copying)
- ✅ Fast for single operations
- ✅ Simple, direct API
- ❌ Cannot easily chain operations
- ❌ Original structure is modified

**Use When**:
- Single, simple operation
- You want to modify the existing structure
- Performance is critical
- Memory usage is a concern

**Example**:
```python
molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
molecule.translate([1, 1, 1])  # Modifies molecule directly
molecule.add_atom('H', [2, 0, 0])  # Adds atom in-place
```

### Transformation Module (Functional, Immutable-Style)

**Location**: `matsimpy/transformation/`

**Functions**:
- `translate(structure, vector, inplace=False)` - Translate any structure
- `rotate(structure, angle, axis, center=None, inplace=False)` - Rotate any structure
- `substitute(structure, indices, new_species, inplace=False)` - Substitute atoms
- `make_supercell(crystal, scaling_matrix, inplace=False)` - Create supercell
- `chain(structure, transformations)` - Chain multiple operations

**Characteristics**:
- ✅ Functional style (returns new object by default)
- ✅ Composable and chainable
- ✅ Preserves original structure (default)
- ✅ Works with both Crystal and Molecule
- ✅ Can apply in-place when needed (inplace=True)
- ❌ Slightly more overhead (copying for functional mode)
- ❌ More verbose for single operations

**Use When**:
- You want to preserve the original structure
- Chaining multiple transformations
- Complex multi-step operations
- Functional programming style
- Testing (easier to verify results)

**Example**:
```python
from matsimpy.transformation import translate, rotate, substitute

# Functional (returns new)
molecule = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
new_molecule = translate(molecule, [1, 1, 1])  # Original unchanged
rotated = rotate(new_molecule, 90, [0, 0, 1])  # Chain operations

# In-place option
translate(molecule, [1, 1, 1], inplace=True)  # Modifies molecule

# Complex chaining
from matsimpy.transformation import chain
transformed = chain(molecule, [
    lambda s: translate(s, [1, 1, 1]),
    lambda s: rotate(s, 90, [0, 0, 1]),
    lambda s: substitute(s, 0, 'N')
])
```

## Relationship and Interaction

### How They Work Together

1. **Transformation module can use class methods internally**
   - For molecules: `translate()` uses `molecule.translate()` when `inplace=True`
   - For crystals: `translate()` directly manipulates positions

2. **Both are available - choose based on use case**
   - Simple operations → Use class methods
   - Complex/chained operations → Use transformation module

3. **Consistent behavior**
   - Both update caches correctly
   - Both update sites correctly
   - Both handle site_properties correctly

### Decision Tree

```
Need to modify structure?
├─ Single simple operation?
│  ├─ Yes → Use class method (add_atom, translate, etc.)
│  └─ No → Continue
├─ Need to preserve original?
│  ├─ Yes → Use transformation module (inplace=False)
│  └─ No → Continue
├─ Multiple operations?
│  ├─ Yes → Use transformation module (chain, apply_transformations)
│  └─ No → Use class method
└─ Working with Crystal?
   ├─ Yes → Use transformation module (translate/rotate not in Crystal class)
   └─ No → Either approach works
```

## Examples

### Example 1: Simple Translation
```python
# Option A: Class method (Molecule only)
molecule.translate([1, 1, 1])

# Option B: Transformation module (works for both)
from matsimpy.transformation import translate
translate(molecule, [1, 1, 1], inplace=True)  # Same as Option A
translate(crystal, [1, 1, 1], inplace=True)   # Works for Crystal too
```

### Example 2: Preserving Original
```python
# Class method - modifies original
molecule.translate([1, 1, 1])  # molecule is modified

# Transformation module - preserves original
from matsimpy.transformation import translate
new_molecule = translate(molecule, [1, 1, 1])  # molecule unchanged
```

### Example 3: Complex Transformation
```python
from matsimpy.transformation import translate, rotate, substitute, chain

# Chain multiple transformations
result = chain(molecule, [
    lambda s: translate(s, [1, 1, 1]),
    lambda s: rotate(s, 90, [0, 0, 1], center=[0, 0, 0]),
    lambda s: substitute(s, 0, 'N')
])

# Or use class methods with intermediate variables
molecule.translate([1, 1, 1])
molecule.rotate(90, [0, 0, 1])
# ... but need to implement substitution manually
```

### Example 4: Adding Atoms
```python
# Class method - direct
crystal.add_atom('O', [0.5, 0.5, 0.5], site_properties={'charge': -2})

# Transformation module - functional (if we add it)
# from matsimpy.transformation import add_atom
# new_crystal = add_atom(crystal, 'O', [0.5, 0.5, 0.5], site_properties={'charge': -2})
```

## Best Practices

1. **For simple operations**: Use class methods
   ```python
   molecule.translate([1, 1, 1])
   crystal.add_atom('O', [0.5, 0.5, 0.5])
   ```

2. **For complex operations**: Use transformation module
   ```python
   from matsimpy.transformation import chain, translate, rotate
   result = chain(structure, [translate_func, rotate_func])
   ```

3. **When preserving original**: Use transformation module with `inplace=False`
   ```python
   new_structure = translate(structure, [1, 1, 1])
   ```

4. **When performance matters**: Use class methods or `inplace=True`
   ```python
   structure.translate([1, 1, 1])  # Fastest
   translate(structure, [1, 1, 1], inplace=True)  # Fast
   ```

5. **For Crystal operations**: Use transformation module
   ```python
   # Crystal doesn't have translate/rotate methods
   from matsimpy.transformation import translate, rotate
   translate(crystal, [1, 1, 1])
   ```

## Summary

| Aspect | Class Methods | Transformation Module |
|--------|--------------|----------------------|
| **Style** | In-place, mutable | Functional (default) or in-place |
| **Speed** | Fastest | Fast (with inplace=True) |
| **Memory** | Efficient | May copy (if inplace=False) |
| **Composability** | Limited | Excellent |
| **Crystal Support** | Limited | Full support |
| **Preserve Original** | No | Yes (default) |
| **Use Case** | Simple ops | Complex/chain ops |

Both approaches are valid and complement each other. Choose based on your specific needs!

