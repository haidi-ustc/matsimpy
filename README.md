# MatSimPy

**MatSimPy** (Materials Simulation in Python) is a comprehensive Python package for molecular and materials simulation, designed to provide a modern, efficient, and user-friendly interface for materials science research.

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-Alpha-orange)](https://gitee.com/haidi-hfut/MatSimPy)

## Features

- **Core Data Structures**: Crystal, Molecule, Lattice, Composition, Site
- **File I/O**: Support for 8+ formats (VASP, CIF, XYZ, PDB, XSF, JSON, ASE, MOL)
- **Transformations**: Translate, rotate, substitute, supercell generation
- **Atom Selection**: Fluent API for flexible atom selection and manipulation
- **Performance**: Optimized with caching and KDTree (10-100x faster)
- **Interoperability**: Convert to/from pymatgen and ASE objects
- **Composition Formatting**: HTML and LaTeX output for chemical formulas

## Installation

Install MatSimPy using pip:

```bash
pip install MatSimPy
```

### Development Installation

For development with testing support:

```bash
pip install MatSimPy[dev]
```

## Quick Start

### Crystal Structures

```python
from matsimpy import Crystal, Lattice

# Create a crystal structure
species = ['Si', 'O', 'Si', 'O']
positions = [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0]]
lattice = Lattice.cubic(10.0)  # 10 Å cubic lattice
crystal = Crystal(species, positions, lattice)

# Access properties
print(crystal.formula)        # Si2O2
print(crystal.composition)     # Composition object
print(crystal.density)         # Density in g/cm³
print(crystal.volume)          # Volume in Å³

# Modify structure
crystal.add_atom('C', [0.25, 0.25, 0.25])
crystal.remove_atom(0)
```

### Molecules

```python
from matsimpy import Molecule

# Create a molecule
species = ['C', 'O', 'O']
positions = [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0]]
molecule = Molecule(species, positions)

# Access properties
print(molecule.formula)                    # CO2
print(molecule.get_center_of_mass())       # [1.2, 0.0, 0.0]
print(molecule.get_moment_of_inertia())    # Moment of inertia tensor

# Transformations
molecule.translate([1, 1, 1])
molecule.rotate(90, [0, 0, 1])  # Rotate 90° around z-axis

# Convert to crystal
crystal = molecule.to_crystal(vacuum=15.0)  # Auto-add box with 15 Å vacuum
```

### File I/O

```python
from matsimpy import Crystal, Molecule

# Read from file (auto-detects format)
crystal = Crystal.from_file('structure.vasp')
molecule = Molecule.from_file('molecule.xyz')

# Write to file
crystal.to_file('output.cif')
molecule.to_file('output.pdb')

# Supported formats
# Crystal: .vasp, .poscar, .cif, .xsf, .json, .ase
# Molecule: .xyz, .pdb, .mol, .json
```

### Transformations

```python
from matsimpy import Crystal, Lattice
from matsimpy.transformation import translate, rotate, substitute, make_supercell

crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(10))

# Functional style (returns new structure)
new_crystal = translate(crystal, [1, 1, 1])
rotated = rotate(new_crystal, 90, [0, 0, 1])
substituted = substitute(rotated, 0, 'Ge')

# In-place (modifies existing)
translate(crystal, [1, 1, 1], inplace=True)
rotate(crystal, 90, [0, 0, 1], inplace=True)

# Supercell
supercell = make_supercell(crystal, [2, 2, 2])  # 2x2x2 supercell
```

### Atom Selection and Substitution

```python
from matsimpy import Crystal, Lattice
from matsimpy.utils.selection import AtomSelection

crystal = Crystal(['Si', 'O', 'Si'], [[0,0,0], [5,0,0], [10,0,0]], 
                  Lattice.cubic(20), coords_are_cartesian=True)

# Fluent selection API
sel = AtomSelection(crystal).by_species('Si').near([0, 0, 0], 5.0)

# Substitute with AtomSelection
crystal.substitute(sel, 'Ge')

# Or with dict mapping
crystal.substitute(sel, {'Si': 'Ge'})

# Multiple partial substitutions
sel_ca = AtomSelection(crystal).by_species('Ca').by_indices([0])
sel_c = AtomSelection(crystal).by_species('C').by_indices([2])
combined = sel_ca | sel_c  # Union
crystal.substitute(combined, {'Ca': 'Ba', 'C': 'Si'})

# Chained selections
sel = (AtomSelection(crystal)
       .by_species('Si')
       .near([0, 0, 0], 5.0)
       .by_property('charge', condition=lambda x: x > 0))
```

### Composition Formatting

```python
from matsimpy import Composition

comp = Composition('Fe2O3')

# HTML output (for web pages)
html = comp.to_html()  # Fe<sub>2</sub>O<sub>3</sub>

# LaTeX output (for documents)
latex = comp.to_latex()  # Fe$_{2}$O$_{3}$

# With sorting
comp.to_html(sort_by='element')   # Sort by atomic number
comp.to_latex(sort_by='alphabet')  # Sort alphabetically
```

### Interoperability

```python
from matsimpy import Crystal
from matsimpy.io.converters import to_pymatgen, from_pymatgen, to_ase, from_ase

crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(10))

# Convert to pymatgen
pymatgen_structure = to_pymatgen(crystal)

# Convert from pymatgen
crystal = from_pymatgen(pymatgen_structure)

# Convert to ASE
ase_atoms = to_ase(crystal)

# Convert from ASE
crystal = from_ase(ase_atoms)
```

## Key Features

### Performance Optimizations

- **Property Caching**: 100x faster formula/composition calculations
- **KDTree Neighbor Finding**: 10-100x faster for large structures (O(n log n) vs O(n²))
- **Lazy Evaluation**: Sites and properties computed on-demand
- **Optimized Coordinate Conversions**: Cached inverse matrices

### File Format Support

| Format | Extension | Crystal | Molecule |
|--------|-----------|---------|----------|
| VASP | `.vasp`, `.poscar` | ✅ | ❌ |
| CIF | `.cif` | ✅ | ❌ |
| XYZ | `.xyz` | ❌ | ✅ |
| PDB | `.pdb` | ✅ | ✅ |
| XSF | `.xsf` | ✅ | ❌ |
| JSON | `.json` | ✅ | ✅ |
| ASE | `.ase` | ✅ | ❌ |
| MOL | `.mol` | ❌ | ✅ |

### Transformation Module

- **Translation**: `translate()`, `translate_to_origin()`
- **Rotation**: `rotate()`, `rotate_around_axis()`
- **Substitution**: `substitute()`, `substitute_all()`
- **Supercell**: `make_supercell()`
- **Chaining**: `chain()`, `apply_transformations()`

Both functional (returns new object) and in-place (modifies existing) modes supported.

### Atom Selection

Flexible atom selection with fluent API:

```python
# Select atoms by species
sel = AtomSelection(structure).by_species('Si')

# Select by position
sel = AtomSelection(structure).near([0, 0, 0], 5.0)

# Select in box
sel = AtomSelection(structure).in_box([0, 0, 0], [5, 5, 5])

# Select by properties
sel = AtomSelection(structure).by_property('charge', condition=lambda x: x > 0)

# Combine selections
sel1 = AtomSelection(structure).by_species('Si')
sel2 = AtomSelection(structure).near([0, 0, 0], 5.0)
combined = sel1 & sel2  # Intersection
combined = sel1 | sel2  # Union
combined = sel1 - sel2  # Difference
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Atom Selection Guide](docs/ATOM_SELECTION_GUIDE.md)** - Atom selection utilities
- **[Substitution API](docs/SUBSTITUTION_API_SUMMARY.md)** - Complete substitution reference
- **[Transformation Design](docs/TRANSFORMATION_DESIGN.md)** - Transformation module architecture
- **[Optimization Roadmap](docs/OPTIMIZATION_ROADMAP_UPDATED.md)** - Current status and future plans

## Requirements

- Python 3.6+
- NumPy
- SciPy
- monty
- tabulate

### Optional Dependencies

- `pymatgen` - For pymatgen interoperability
- `ase` - For ASE interoperability
- `pytest` - For testing (included in `[dev]` extras)

## Testing

Run the test suite:

```bash
pytest tests/
```

With coverage:

```bash
pytest tests/ --cov=matsimpy
```

## Project Structure

```
matsimpy/
├── core/           # Core data structures (Structure, Crystal, Molecule, etc.)
├── io/             # File format support
├── transformation/ # Structure transformations
├── utils/          # Utility functions (selection, constants)
├── analysis/       # Analysis tools (placeholder)
├── code/           # DFT code interfaces (VASP, Quantum Espresso)
├── generation/     # Structure generation (random, surfaces)
└── visualization/  # Visualization tools (placeholder)
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**haidi wang**  
Email: haidi@hfut.edu.cn  
Repository: https://gitee.com/haidi-hfut/MatSimPy

## Acknowledgments

MatSimPy is inspired by [pymatgen](https://github.com/materialsproject/pymatgen) and aims to provide a modern, efficient alternative for materials simulation.

---

**Note**: MatSimPy is currently in Alpha development. The API may change in future versions.
