# MatSimPy

**MatSimPy (Materials Simulation in Python)** is a Python library for building, transforming, analyzing, and storing crystal/molecular structures with a clean, ASE-like workflow.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-Beta-brightgreen)](https://gitee.com/haidi-hfut/MatSimPy)
[![Tests](https://img.shields.io/badge/tests-1295%20passed-brightgreen)](tests/)

**Version**: v0.3.0 — **core modules are stable** (API ergonomics + immutability + coordinate semantics are consistent).

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Conventions](#core-conventions)
- [CLI](#command-line-interface)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [Testing](#testing)
- [Documentation](#documentation)

## Features

- **Core data model**: `Crystal`, `Molecule`, `Structure`, `Lattice`, `Composition`, `Site`, `Element`
- **Immutable-by-default**: mutation returns new objects (safe caching, predictable pipelines)
- **Coordinate system clarity**: `Structure.positions` is **always Cartesian**; `Crystal` also supports `frac_positions`
- **Builders**: bulk/surface/alloy/molecule/defects/nanostructures
- **Transformations**: geometric, lattice, atomic, chemical, structural, plus composite (pipelines/sweeps/batch)
- **Analysis**: symmetry (spglib), graph connectivity (OOP + NetworkX export), convenience properties
- **Calculators**: classical + ML (optional), ASE/pymatgen I/O bridges (optional)
- **Storage**: persistent storage via maggma (optional)
- **CLI**: interactive menu for structure editing and utilities

## Installation

### Basic installation

```bash
pip install MatSimPy
```

This installs the core package with required dependencies:
- numpy
- scipy
- monty
- tabulate

### From source (editable)

Clone the repository and install in editable mode:

```bash
git clone https://gitee.com/haidi-hfut/MatSimPy.git
cd MatSimPy
pip install -e .
```

For development:

```bash
pip install -e .[dev]
```

This includes:
- pytest
- pytest-cov
- pytest-xdist

### Optional extras

MatSimPy supports optional features through extra dependencies:

```bash
# CLI (interactive menu)
pip install -e .[cli]

# Machine learning calculators (torch, torch-geometric)
pip install -e .[ml]

# I/O converters (pymatgen, ase)
pip install -e .[io]

# Structure builders (pyxtal, rdkit)
pip install -e .[builders]

# Symmetry analysis (spglib)
pip install -e .[analysis]

# Data storage (maggma)
pip install -e .[storage]

# Everything
pip install -e .[all]
```

## Quick Start

Structures are **immutable by default** — all mutation methods return new objects without modifying the original.

```python
from matsimpy import Crystal, Molecule, Lattice, Composition

# Crystal (fractional input by default)
crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
print(crystal.formula)   # NaCl
print(crystal.volume)    # ~179.4 Å³

# Mutation returns a new object — must capture the result
doped = crystal.add_atom(['H', 'O'], [[0.1, 0, 0], [0.9, 0, 0]])
print(len(crystal))      # 2 (original unchanged)
print(len(doped))        # 4 (new object)

# Chained mutations (returns new objects each step)
result = crystal.substitute(0, 'K').add_atom('H', [0.1, 0, 0])
print(result.formula)    # KClH

# Molecule (Cartesian)
molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
print(molecule.formula)  # OH2
print(molecule.get_center_of_mass())

# Transformations return new objects
translated = molecule.translate([1.0, 0, 0])
rotated = translated.rotate(90, [0, 0, 1])

# Work with composition
comp = Composition('Fe2O3')
print(comp['Fe'])     # 2
print(comp['O'])      # 3
print(comp.mass)      # Fast! (compute-once cached)

# Mass and mole fractions
mass_frac = comp.mass_fractions()   # {'Fe': 0.699, 'O': 0.301}
mole_frac = comp.mole_fractions()   # {'Fe': 0.4, 'O': 0.6}
```

### Graph analysis (optional)

```python
from matsimpy.core.graph import MoleculeGraph, create_structure_graph
from matsimpy import Molecule
molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
# OOP API (recommended)
graph = MoleculeGraph(molecule, cutoff=2.0)
print(graph.num_nodes)       # Number of atoms
print(graph.num_edges)       # Number of bonds
print(graph.is_connected)    # Connectivity check
print(graph.diameter)        # Graph diameter
print(graph.statistics)      # All stats at once

# Find shortest path
path = graph.get_shortest_path(0, 2)

# Convert to NetworkX
nx_graph = graph.to_networkx()

# Or use functional API
from matsimpy.core.graph import get_adjacency_matrix, get_coordination_numbers
adj = get_adjacency_matrix(molecule, cutoff=3.0)
coord = get_coordination_numbers(crystal, cutoff=5.0)
```

### LaTeX export

```python
from matsimpy.io import crystals_to_latex_table, molecules_to_latex_table
from matsimpy import Molecule, Crystal, Lattice

# Export crystals to LaTeX table
crystal1 = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.63))
crystal2 = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
crystal3 = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.65))
crystals = [crystal1, crystal2, crystal3]
latex = crystals_to_latex_table(
    crystals,
    caption='NaCl',
    label='tab:si_polymorphs',
    include_columns=['ID', 'Formula', 'Lattice', 'Volume'],
    use_mhchem=True  # Use \ce{} from mhchem package
)

# Export molecules
molecules = [molecule, molecule]
latex = molecules_to_latex_table(
    molecules,
    caption='Organic Molecules',
    include_columns=['ID', 'Formula', 'Mass', 'Atoms']
)

# Save to file
from matsimpy.io import save_latex_table
save_latex_table(crystals, 'structures.tex')
```

### Builders

```python
from matsimpy.builders import (
    from_prototype, generate_slab, create_interstitial,
    build_tetrahedral, create_vacancy, build_nanotube,build_carbon_nanotube
)

# Build bulk structures from prototypes
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
bcc_fe = from_prototype('bcc', 'Fe', 2.87)
diamond_c = from_prototype('diamond', 'C', 3.57)

# Create surface slabs
slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)

# Generate supercell
from matsimpy.transformation.structural import make_supercell
supercell = make_supercell(fcc_cu, [4, 4, 4])

# Build molecules
ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)

# Create defects
with_vacancy = create_vacancy(fcc_cu, 0)
with_interstitial = create_interstitial(fcc_cu, 'H', positions=[0.5, 0.5, 0.5])

# Build nanotubes
cnt = build_carbon_nanotube(10, 0, length=1)  # Zigzag CNT
```

### Transformations

```python
from matsimpy.transformation import (
    translate, rotate, apply_strain, scale_lattice,
    substitute, make_supercell
)

# Geometric transformations
translated = translate(crystal, [1, 1, 1])
rotated = rotate(translated, 90.0, [0, 0, 1])

# Lattice transformations
strained = apply_strain(crystal, [0.05, 0, 0])  # Uniaxial strain
scaled = scale_lattice(crystal, 1.1)            # Scale by 10%

# Chemical transformations
substituted = substitute(crystal, [0, 1], ['Ge', 'Ge'])

# Structural transformations
supercell = make_supercell(crystal, [2, 2, 2])  # 2x2x2 supercell
```

### High-throughput transformations

```python
from matsimpy.transformation.composite import (
    TransformationPipeline, ParameterSweep, BatchProcessor
)
from matsimpy.transformation import make_supercell, apply_strain
from matsimpy.builders.bulk import from_prototype

# 1. Reusable transformation pipeline
pipeline = TransformationPipeline("strain_study")
pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
pipeline.add_step(apply_strain, strain_matrix=[[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])

# Apply to structure
crystal = from_prototype('diamond', 'Si', 5.43)
result = pipeline.apply(crystal)

# Apply to multiple structures
structures = [from_prototype('diamond', 'Si', 5.43), from_prototype('fcc', 'Cu', 3.61)]
results = pipeline.apply_batch(structures)

# 2. Parameter sweep - generate structures with varying parameters
sweep = ParameterSweep(
    base_structure=crystal,
    transformations={
        'strain': {
            'func': apply_strain,
            'params': {
                'strain_matrix': [
                    [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],
                ]
            }
        }
    },
    mode='cartesian'  # All combinations
)

# Generate all structures
for struct, params in sweep:
    print(f"Strain: {params['strain']}, Formula: {struct.formula}")

# 3. Batch processing with error handling
def make_2x2x2_supercell(s):
    return make_supercell(s, [2, 2, 2])

def apply_1pct_strain(s):
    return apply_strain(s, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])

processor = BatchProcessor(
    transformations=[make_2x2x2_supercell, apply_1pct_strain],
    n_workers=1,
    progress=True,
    error_handling='skip'  # or 'raise', 'log'
)

structures = [from_prototype('fcc', 'Cu', 3.61) for _ in range(10)]
results = processor.process(structures)
for result in results:
    if result.success:
        print(f"Processed: {result.structure.formula}")
```

### File I/O

**High-level interface (recommended):**

```python
from matsimpy.io import read, write

# Auto-detect format from file extension
write(crystal, 'structure.vasp')
write(molecule, 'molecule.xyz')

# Read structures (format auto-detected)
crystal = read('structure.vasp')
molecule = read('molecule.xyz')

# Explicit format specification
crystal = read('file.txt', format='vasp')
write(crystal, 'output.txt', format='cif', title='My Structure')
```

**Class methods (alternative):**

```python
# Using class methods
crystal = Crystal.from_file('structure.vasp')
crystal.to_file('output.cif', title='My Crystal')

molecule = Molecule.from_file('molecule.xyz')
molecule.to_file('output.pdb', title='Water')
```

**Format-specific functions (advanced use):**

```python
from matsimpy.io.vasp import write_POSCAR, read_POSCAR
from matsimpy.io.xyz import write_XYZ, read_XYZ

# Direct format-specific access
write_POSCAR(crystal, 'structure.vasp')
molecule = read_XYZ('molecule.xyz')
```

### Calculators

```python
from matsimpy import Crystal, Lattice
from matsimpy.calculator import LennardJones, Mattersim

# Classical potential calculator
crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.0))
calc = LennardJones(sigma=3.4, epsilon=0.0104)
crystal.calc = calc

# Get energy and forces
energy = crystal.get_potential_energy()
forces = crystal.get_forces()

# ML calculator (uses config defaults)
ml_calc = Mattersim(model_path='model.pth', model_type='mace')
crystal.calc = ml_calc
energy = crystal.get_potential_energy()
```

### Configuration

```python
from matsimpy.config import get_config, ConfigManager

# Get configuration values
device = get_config('calculator.ml.default_device')  # 'cpu'
model_dir = get_config('paths.models')  # '~/.matsimpy/models'

# Modify configuration
config = ConfigManager()
config.set('calculator.ml.default_device', 'cuda', save=True)
```

### Symmetry analysis

```python
from matsimpy.builders.bulk import from_prototype
from matsimpy.symmetry import get_conventional_cell

# Create crystal structure
crystal = from_prototype('diamond', 'Si', 5.43)

# Get symmetry information
sym_info = crystal.get_symmetry_info()
print(f"Space group: {sym_info['space_group_symbol']}")  # Fd-3m
print(f"Point group: {sym_info['point_group']}")        # m-3m
print(f"Crystal system: {sym_info['crystal_system']}")  # Cubic

# Get conventional cell
conventional = crystal.get_conventional_cell()
print(f"Primitive: {len(crystal)} atoms")         # 2 atoms
print(f"Conventional: {len(conventional)} atoms") # 8 atoms
```

### Data storage

## Core Conventions

### Immutability

- All mutation APIs return **new** objects (`add_atom`, `remove_atom`, `substitute`, `sort_atoms`, transformations, etc.)
- Internal numpy arrays are read-only to prevent accidental in-place edits.

### Coordinates

- `Structure.positions` is **always Cartesian** (Å).
- `Crystal` stores fractional internally and provides:
  - `Crystal.frac_positions` (fractional)
  - `Crystal.cart_positions` (Cartesian)
  - `Crystal.positions` (Cartesian, consistent with `Structure`)

```python
from matsimpy.storage import DataStorage
from matsimpy.builders.bulk import from_prototype

# Initialize storage with a JSON file
storage = DataStorage(store_path='mydata.json')

# Store crystal structure
crystal = from_prototype('diamond', 'Si', 5.43)
doc_id = storage.store_data(crystal, metadata={'description': 'Si primitive cell'})

# Store calculation results
results = {'energy': -10.5, 'forces': [[0,0,0]]}
storage.store_data(results, metadata={'calculator': 'LJ'})

# Retrieve and query
retrieved = storage.retrieve_data(doc_id)    # Returns dict with full MSON data
lj_results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})

# Reconstruct Crystal from stored data
from matsimpy import Crystal
reconstructed = Crystal.from_dict(retrieved)
print(reconstructed.formula)                 # Si2
```

## Project Structure

```
matsimpy/
├── core/              # Core data structures
│   ├── crystal.py     # Crystal class
│   ├── molecule.py    # Molecule class
│   ├── lattice.py     # Lattice class
│   ├── composition.py # Composition class
│   ├── site.py        # Site classes
│   └── periodic_table.py  # Element and periodic table
│
├── builders/         # Structure builders
│   ├── bulk/          # Bulk crystal structures (prototypes, symmetry)
│   ├── surface/       # Surface slabs and adsorbates
│   ├── alloy/         # Alloy generation (random, ordered, intermetallic)
│   ├── molecule/      # Molecular structure builders
│   ├── defects/       # Point defect creation
│   └── nanostructure/ # Nanotubes and twisted structures
│
├── transformation/    # Structure transformations
│   ├── geometric/     # Translation, rotation
│   ├── lattice/       # Lattice strain, scaling, transformations
│   ├── atomic/        # Atom manipulation and organization
│   ├── chemical/      # Chemical substitutions
│   ├── structural/    # Supercell, molecular operations
│   └── composite/     # High-throughput transformation tools
│       ├── pipeline.py    # TransformationPipeline
│       ├── sweep.py       # ParameterSweep
│       └── batch.py       # BatchProcessor
│
├── io/                # File format support
│   ├── core.py        # High-level read/write interface
│   ├── vasp.py        # VASP POSCAR/CONTCAR
│   ├── cif.py         # CIF format
│   ├── xyz.py         # XYZ format
│   ├── pdb.py         # PDB format
│   ├── mol.py         # MOL format
│   ├── xsf.py         # XSF format
│   ├── ase.py         # ASE format
│   ├── json.py        # JSON serialization
│   └── utils.py       # Format detection utilities
│
├── calculator/        # Energy/force calculators
│   ├── base.py        # Base Calculator class
│   ├── classical/     # Classical potentials (LJ, etc.)
│   ├── ml/            # Machine learning calculators
│   └── dft/           # DFT calculators (VASP, QE, etc.)
│
├── config/            # Global configuration system
│   ├── manager.py     # ConfigManager class
│   ├── defaults.py    # Default configuration
│   └── utils.py       # Configuration utilities
│
├── storage/           # Data storage module
│   └── maggma_store.py  # Persistent storage using maggma
│
├── symmetry/          # Symmetry analysis
│   └── analyzer.py    # SymmetryAnalyzer, get_conventional_cell
├── ui/                # User interface
│   └── cli/           # Command-line interface and interactive menu
├── utils/             # Utility functions
├── code/              # DFT code interfaces
├── ai/                # AI/ML integration
├── analysis/          # Analysis tools
└── visualization/     # Visualization tools (planned)
```

## Command-Line Interface

MatSimPy includes an interactive CLI menu system for easy access to all features:

```bash
# Launch interactive menu
matsimpy

# Or specify menu file
matsimpy path/to/matsimpy_menu.json
```

The CLI provides access to structure generation/editing, analysis tools, format conversion, and more.

## Examples

Comprehensive examples are available in the `examples/` directory:

- **Core Module**: `core_basic.py`, `core_advanced.py`
- **Builders**: `builders_bulk.py`, `builders_surface.py`, `builders_alloy.py`, `builders_molecule.py`, `builders_defects.py`, `builders_nanostructure.py`
- **Transformations**: `transformation_geometric.py`, `transformation_lattice.py`, `transformation_chemical.py`, `transformation_structural.py`, `transformation_composite.py`
- **IO**: `io_basic.py`
- **Workflows**: `workflow_basic.py`
- **Calculators**: `calculator_basic.py`
- **Storage**: `storage_basic.py`
- **Symmetry**: `symmetry_basic.py`
- **Config**: `config_basic.py`

Run an example:

```bash
python examples/core_basic.py
python examples/builders_bulk.py
```

## Testing

The project includes comprehensive tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=matsimpy --cov-report=html

# Run specific modules
pytest tests/test_core*.py -v              # Core modules
pytest tests/test_graph*.py -v             # Graph analysis
pytest tests/test_io_latex.py -v           # LaTeX export
pytest tests/test_composite*.py -v         # High-throughput tools

# Performance and quality
pytest --tb=no -q                          # Quick run
pytest tests/ -v --durations=10            # Show slowest tests
```

Current status in CI/local runs varies by optional extras; core suite is green.

## Documentation

- **Sphinx Documentation**: See `docs/` directory for comprehensive Sphinx documentation
  - Build with: ``cd docs && make html``
  - View at: ``docs/_build/html/index.html``
- **AI Documentation**: See `AIdocs/` directory for AI-related documentation and session summaries
  - [November 2025 Quality Enhancement](AIdocs/SESSION_SUMMARY_2025_11.md) - Complete details of recent improvements
- **Examples**: See `examples/` directory for comprehensive usage examples
- **API Reference**: See module docstrings and `examples/` for detailed usage
- **Project Structure**: See above for module organization

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**haidi wang**  
Email: haidi@hfut.edu.cn  
Repository: https://gitee.com/haidi-hfut/MatSimPy

## Acknowledgments

MatSimPy is inspired by [pymatgen](https://github.com/materialsproject/pymatgen) and [ASE](https://wiki.fysik.dtu.dk/ase/) and aims to provide a modern, efficient alternative for materials simulation with comprehensive structure building capabilities.

---

**Note**: v0.3.0 is Beta; core modules are stable. Non-core modules and optional integrations may still evolve.
