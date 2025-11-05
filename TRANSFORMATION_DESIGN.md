# Transformation Module Design

## Design Philosophy

### Two Approaches for Structure Manipulation

1. **In-Place (Mutable) Methods** - Direct manipulation on the object
   - `add_atom()`, `remove_atom()` - Modify structure directly
   - `translate()`, `rotate()` (Molecule) - Modify positions in-place
   - Fast, memory-efficient for single operations
   - **Use when**: You want to modify the existing structure

2. **Transformation Module** - Functional transformations
   - Returns new objects (immutable-style)
   - Composable, chainable operations
   - Better for complex multi-step transformations
   - **Use when**: You want to preserve original or create variations

## Implementation Strategy

### Pattern: Dual Interface

**Class Methods** (in-place):
```python
crystal.add_atom('O', [0.5, 0.5, 0.5])  # Modifies crystal
molecule.translate([1, 1, 1])  # Modifies molecule
```

**Transformation Functions** (functional):
```python
new_crystal = add_atom(crystal, 'O', [0.5, 0.5, 0.5])  # Returns new crystal
new_molecule = translate(molecule, [1, 1, 1])  # Returns new molecule
```

### Benefits

- **Flexibility**: Choose in-place or functional based on use case
- **Consistency**: Transformation module provides unified API
- **Composability**: Chain transformations easily
- **Testing**: Functional style easier to test

## Module Structure

```
transformation/
├── __init__.py          # Main exports
├── base.py              # Base transformation class/utilities
├── translation.py       # Translation operations
├── rotation.py          # Rotation operations
├── substitution.py     # Atom substitution
├── supercell.py         # Supercell generation
└── composite.py         # Composite transformations (chains)
```

## API Design

### Translation Module
```python
# Functional (returns new)
def translate(structure: Union[Crystal, Molecule], 
              vector: List[float], 
              inplace: bool = False) -> Union[Crystal, Molecule]:
    """
    Translate structure by a vector.
    
    Args:
        structure: Crystal or Molecule to translate
        vector: Translation vector [x, y, z]
        inplace: If True, modify structure in-place (default: False)
    
    Returns:
        Translated structure (new object if inplace=False, same object if inplace=True)
    """
```

### Rotation Module
```python
# Functional (returns new)
def rotate(structure: Union[Crystal, Molecule],
           angle: float,
           axis: List[float],
           center: Optional[List[float]] = None,
           inplace: bool = False) -> Union[Crystal, Molecule]:
    """
    Rotate structure around an axis.
    
    Args:
        structure: Crystal or Molecule to rotate
        angle: Rotation angle in degrees
        axis: Rotation axis [x, y, z]
        center: Rotation center (default: origin or COM for molecules)
        inplace: If True, modify structure in-place (default: False)
    
    Returns:
        Rotated structure
    """
```

### Substitution Module
```python
def substitute(structure: Union[Crystal, Molecule],
               indices: Union[int, List[int]],
               new_species: Union[str, List[str]],
               inplace: bool = False) -> Union[Crystal, Molecule]:
    """
    Substitute atoms with new species.
    
    Args:
        structure: Structure to modify
        indices: Atom index(es) to substitute
        new_species: New species symbol(s)
        inplace: If True, modify structure in-place (default: False)
    
    Returns:
        Structure with substituted atoms
    """
```

### Supercell Module
```python
def make_supercell(crystal: Crystal,
                   scaling_matrix: Union[List[int], np.ndarray],
                   inplace: bool = False) -> Crystal:
    """
    Create supercell from unit cell.
    
    Args:
        crystal: Unit cell to expand
        scaling_matrix: [a, b, c] or [[a1, a2, a3], [b1, b2, b3], [c1, c2, c3]]
        inplace: If True, modify crystal in-place (default: False)
    
    Returns:
        Supercell structure
    """
```

## Relationship with Mutable Methods

### Rule of Thumb

- **Simple operations** → Use class methods (`add_atom`, `remove_atom`, `translate`, `rotate`)
- **Complex operations** → Use transformation module functions
- **Chaining operations** → Use transformation module (functional style)
- **Single operation, modify existing** → Use class methods (in-place)

### Example Usage Patterns

```python
# Pattern 1: Direct manipulation (simple)
crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(10))
crystal.add_atom('O', [0.5, 0.5, 0.5])  # In-place

# Pattern 2: Functional transformation (preserve original)
from matsimpy.transformation import add_atom
crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(10))
crystal_with_o = add_atom(crystal, 'O', [0.5, 0.5, 0.5])  # New object

# Pattern 3: Chaining transformations (functional)
from matsimpy.transformation import translate, rotate, substitute
new_molecule = translate(
    rotate(
        substitute(molecule, 0, 'N'),
        angle=90, axis=[0, 0, 1]
    ),
    vector=[1, 1, 1]
)

# Pattern 4: Complex transformation (use module)
from matsimpy.transformation import make_supercell
supercell = make_supercell(crystal, [2, 2, 2])
```

## Implementation Notes

1. **Transformation functions should handle both Crystal and Molecule**
2. **Default to functional (inplace=False) for safety**
3. **Provide inplace option for performance when needed**
4. **Transformation module can use class methods internally**
5. **Document clearly when to use which approach**

