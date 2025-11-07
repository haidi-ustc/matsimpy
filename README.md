# MatSimPy

**MatSimPy** (Materials Simulation in Python) is a comprehensive Python package for molecular and materials simulation, designed to provide a modern, efficient, and user-friendly interface for materials science research.

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-Alpha-orange)](https://gitee.com/haidi-hfut/MatSimPy)
[![Tests](https://img.shields.io/badge/tests-700%2B%20passed-brightgreen)](tests/)

## Features

- **Core Data Structures**: Crystal, Molecule, Lattice, Composition, Site, Element
- **Structure Builders**: Bulk, surface, alloy, molecule, defects, nanostructures
- **Transformations**: Geometric, lattice, atomic, chemical operations
- **High-Throughput Tools**: Transformation pipelines, parameter sweeps, batch processing
- **Calculators**: Classical potentials (LJ), ML potentials (Mattersim), DFT interfaces
- **Symmetry Analysis**: Space group determination, conventional cell conversion
- **Configuration System**: Global config with environment variable overrides
- **Data Storage**: Persistent storage for structures and calculation results (maggma)
- **File I/O**: High-level `read()`/`write()` interface with auto-format detection, supporting VASP, CIF, XYZ, PDB, MOL, XSF, JSON, ASE formats
- **Performance**: Optimized with caching and KDTree for efficient neighbor finding
- **Comprehensive Examples**: 14+ example files demonstrating all features

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

### Optional Features

Install with optional dependencies:

```bash
# With storage support (maggma)
pip install MatSimPy[storage]

# With all optional features
pip install MatSimPy[all]
```

Or clone and install from source:

```bash
git clone https://gitee.com/haidi-hfut/MatSimPy.git
cd MatSimPy
pip install -e .
```

## Quick Start

### Core Structures

```python
from matsimpy import Crystal, Molecule, Lattice, Composition
from matsimpy.builders.bulk import from_prototype

# Create a crystal structure using prototype builder
# NaCl rocksalt structure (conventional cell with 8 atoms)
nacl = from_prototype('rocksalt', 'NaCl', 5.64).get_conventional_cell()
print(nacl.formula)      # Cl4Na4
print(len(nacl))         # 8 atoms
print(nacl.volume)       # ~179.4 Å³

# Or create directly with Crystal class
lattice = Lattice.cubic(5.0)
crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)
print(crystal.formula)   # ClNa
print(crystal.volume)    # 125.0 Å³

# Create a molecule
molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
print(molecule.formula)  # H2O
print(molecule.get_center_of_mass())

# Work with composition
comp = Composition('Fe2O3')
print(comp['Fe'])  # 2
print(comp['O'])   # 3
```

### Structure Builders

```python
from matsimpy.builders import (
    from_prototype, generate_slab, generate_random_alloy,
    build_tetrahedral, create_vacancy, build_nanotube
)

# Build bulk structures from prototypes
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
bcc_fe = from_prototype('bcc', 'Fe', 2.87)
diamond_c = from_prototype('diamond', 'C', 3.57)

# Create surface slabs
slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)

# Generate alloys
from matsimpy.transformation.structural import make_supercell
supercell = make_supercell(fcc_cu, [4, 4, 4])
alloy = generate_random_alloy(supercell, ['Ni'], 'Cu', [0.25])

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

### High-Throughput Transformations

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

# Apply to multiple structures in parallel
results = pipeline.apply_batch([crystal1, crystal2, crystal3], parallel=True, n_workers=4)

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
    print(f"Strain: {params['strain']}")
    run_calculation(struct)

# 3. Batch processing with error handling
processor = BatchProcessor(
    transformations=[
        lambda s: make_supercell(s, [2, 2, 2]),
        lambda s: apply_strain(s, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
    ],
    n_workers=4,
    progress=True,
    error_handling='skip'  # or 'raise', 'log'
)

results = processor.process([crystal1, crystal2, ..., crystal1000])
for result in results:
    if result.success:
        process_structure(result.structure)
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

### Symmetry Analysis

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

### Data Storage

```python
from matsimpy.storage import DataStorage
from matsimpy import Crystal, Lattice

# Initialize storage (uses config default path)
storage = DataStorage()

# Store crystal structure (proper diamond structure with 2 atoms)
from matsimpy.builders.bulk import from_prototype
crystal = from_prototype('diamond', 'Si', 5.43)
doc_id = storage.store_data(crystal, metadata={'description': 'Si primitive cell'})

# Store calculation results
results = {'energy': -10.5, 'forces': [[0,0,0]]}
storage.store_data(results, metadata={'calculator': 'LJ'})

# Retrieve and query
retrieved = storage.retrieve_data(doc_id)
lj_results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})
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
│   ├── vasp.py        # VASP POSCAR/CONTCAR
│   ├── xyz.py         # XYZ format
│   └── json.py        # JSON serialization
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
├── utils/             # Utility functions
├── code/              # DFT code interfaces
├── ai/                # AI/ML integration
└── analysis/          # Analysis tools
```

## Examples

Comprehensive examples are available in the `examples/` directory:

- **Core Module**: `core_basic.py`, `core_advanced.py`
- **Builders**: `builders_bulk.py`, `builders_surface.py`, `builders_alloy.py`, `builders_molecule.py`, `builders_defects.py`, `builders_nanostructure.py`
- **Transformations**: `transformation_geometric.py`, `transformation_lattice.py`, `transformation_chemical.py`, `transformation_structural.py`
- **IO**: `io_basic.py`
- **Workflows**: `workflow_basic.py`

Run an example:

```bash
python examples/core_basic.py
python examples/builders_bulk.py
```

## Key Capabilities

### Structure Builders

- **Bulk Structures**: 9+ prototypes (FCC, BCC, diamond, rocksalt, perovskite, etc.)
- **Surface Structures**: Slab generation with customizable Miller indices and vacuum spacing
- **Alloys**: Random and ordered alloys, intermetallic compounds
- **Molecules**: Linear, bent, tetrahedral geometries, SMILES parsing (with RDKit)
- **Defects**: Vacancy, interstitial, substitution, Frenkel, Schottky, antisite defects
- **Nanostructures**: Nanotubes (CNT, h-BN, MoS2, etc.), twisted bilayers, magic-angle structures

### Transformations

- **Geometric**: Translation, rotation (with center options)
- **Lattice**: Strain application, scaling, volume setting, lattice transformations
- **Atomic**: Atom movement, swapping, sorting, centering
- **Chemical**: Single/multiple substitutions, bulk substitutions
- **Structural**: Supercell generation, molecular operations
- **High-Throughput**: 
  - **TransformationPipeline**: Reusable transformation sequences with save/load
  - **ParameterSweep**: Systematic parameter variation (cartesian product or zip mode)
  - **BatchProcessor**: Parallel batch processing with progress tracking and error handling

### Calculators

- **Classical Potentials**: Lennard-Jones potential with periodic boundary conditions
- **ML Potentials**: Machine learning calculators (Mattersim framework)
- **DFT Calculators**: Base classes for VASP, Quantum Espresso (future)
- **ASE-Style Interface**: Calculators attach to structures via `structure.calc`
- **Config Integration**: Default parameters from global configuration

### Configuration System

- **Global Config**: `~/.matsimpy/config.yaml` for user settings
- **Environment Overrides**: `MATSIMPY_*` environment variables
- **Calculator Defaults**: Default parameters for all calculator types
- **Path Management**: Centralized paths for models, cache, output

### Data Storage

- **Persistent Storage**: Store structures and calculation results
- **MSONable Support**: Automatic serialization of Crystal, Molecule objects
- **Query Support**: Query stored data by ID or criteria
- **Metadata**: Attach metadata for organization and search
- **Memory & File Stores**: In-memory for testing, JSON file for persistence

### Symmetry Analysis

- **Space Group Determination**: Get space group number, symbol, point group, crystal system
- **Conventional Cell**: Convert primitive cells to standard conventional cells
- **Symmetry Operations**: Access to rotation matrices and translation vectors
- **Integration**: Direct methods on Crystal objects (`get_symmetry_info()`, `get_conventional_cell()`)

### Performance Features

- **Caching**: Formula and composition caching for faster repeated access
- **KDTree**: Optimized neighbor finding for large structures
- **Lazy Evaluation**: Sites and properties computed on-demand
- **Vectorized Operations**: Efficient numpy-based coordinate transformations
- **Parallel Processing**: Multiprocessing support for batch operations

## Module Reference

### Core Module

```python
from matsimpy import (
    Structure, Crystal, Molecule,
    Lattice, Composition, Site, CrystalSite, Element
)
```

### Builders Module

```python
from matsimpy.builders import (
    # Bulk
    from_prototype, random_crystal, from_space_group,
    # Surface
    generate_slab, add_adsorbate,
    # Alloy
    generate_random_alloy, generate_ordered_alloy, generate_intermetallic,
    # Molecule
    build_linear, build_bent, build_tetrahedral, build_from_smiles,
    # Defects
    create_vacancy, create_interstitial, create_substitution,
    create_frenkel, create_schottky, create_antisite,
    # Nanostructure
    build_nanotube, build_carbon_nanotube,
    build_twisted_bilayer, build_magic_angle_twisted
)
```

### Transformation Module

```python
from matsimpy.transformation import (
    # Geometric
    translate, rotate,
    # Lattice
    apply_strain, scale_lattice, set_volume,
    # Atomic
    move_atoms, swap_atoms, sort_atoms,
    # Chemical
    substitute,
    # Structural
    make_supercell
)

# High-throughput composite transformations
from matsimpy.transformation.composite import (
    TransformationPipeline,  # Reusable pipelines
    ParameterSweep,           # Parameter variation
    BatchProcessor,           # Batch processing
    BatchResult               # Result metadata
)
```

## Requirements

### Core Dependencies

- Python 3.6+
- NumPy
- SciPy
- monty (for MSONable serialization)
- tabulate (for formatted output)

### Optional Dependencies

- `pymatgen` - For pymatgen interoperability
- `ase` - For ASE interoperability
- `rdkit` - For SMILES parsing in molecule builders
- `pyxtal` - For random crystal generation
- `spglib` - For symmetry analysis

## Testing

The project includes comprehensive tests with **700+ passing tests**:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=matsimpy --cov-report=html

# Run specific test file
pytest tests/test_core_structure_comprehensive.py -v

# Run composite transformation tests
pytest tests/test_composite_*.py -v
```

## Documentation

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

**Note**: MatSimPy is currently in Alpha development. The API may change in future versions.
