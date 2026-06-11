# MatSimPy

**MatSimPy (Materials Simulation in Python)** is a Python library for building, transforming, analyzing, and storing crystal/molecular structures with a clean, ASE-like workflow.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-Beta-brightgreen)](https://gitee.com/haidi-hfut/MatSimPy)
[![Tests](https://img.shields.io/badge/tests-core%20suite-brightgreen)](tests/)

**Version**: v0.8.0

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Conventions](#core-conventions)
- [AI Command Line](#ai-command-line-interface)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [Testing](#testing)
- [Documentation](#documentation)

## Features

- **Core**: `Crystal` (periodic + lattice), `Molecule` (non-periodic), `Lattice` (14 Bravais types), `Composition`, `Site`, `Element` (118 elements). Immutable-return — `add_atom`, `remove_atom`, `substitute`, `sort_atoms` return new objects
- **Builders** (7 domains, 27 functions): `from_prototype` (9 prototypes: fcc/bcc/hcp/diamond/rocksalt/perovskite/zincblende/sc/CsCl), `generate_slab`, `generate_random_alloy`, `build_nanotube`, `create_vacancy`, `add_adsorbate`, `build_heusler`, etc. Registered via `BuilderRegistry`
- **Transformations** (5 categories, 26 functions): `translate`, `rotate`, `apply_strain`, `make_supercell`, `substitute`, `move_atoms`, `scale_lattice`, etc. Registered via `TransformationRegistry` with `TransformationSpec` metadata. `TransformationPlan` for reproducible pipelines
- **Analysis** (6 modules): `BondAnalyzer` (bonds/angles/dihedrals/orders), `StructureAnalyzer` (COM/inertia/density), `TopologyAnalyzer` (connectivity/rings/paths), graph/neighbor functions, `AtomSelection` (9 selectors)
- **IO** (9 formats): VASP/CIF/XYZ/PDB/XSF/MOL/JSON/ASE — auto-detected, table-driven `FormatRegistry`. `read()`/`write()`, third-party conversion, and LaTeX table helpers
- **Storage**: `DataStorage` with `MemoryBackend` (testing) + `MaggmaBackend` (persistent). Content-addressed sha256 IDs. `DocumentEnvelope` schema
- **Extensibility**: Plugin entry points for registries, including IO formats
- **AI REPL**: Optional LLM function calling via DeepSeek models. Built-in MatSimPy skills expose core, builders, transformations, analysis, IO, storage, calculators, and symmetry tools. Use `matsimpy-ai -c "build fcc Cu"` for single-shot mode
- **Calculators**: `LennardJones` (classical). ML (MatterSim), DFT file/workflow interfaces for VASP, Gaussian, and LAMMPS — optional

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
- pyyaml

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

# AI REPL
pip install -e .[ai]

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

### Graph analysis

```python
from matsimpy.analysis import MoleculeGraph, create_structure_graph
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
from matsimpy.analysis import get_adjacency_matrix, get_coordination_numbers
adj = get_adjacency_matrix(molecule, cutoff=3.0)
coord = get_coordination_numbers(crystal, cutoff=5.0)
```

### LaTeX export

```python
from matsimpy.io import crystals_to_latex_table, save_latex_table
from matsimpy import Molecule, Crystal, Lattice

# Export crystals to LaTeX table
crystal1 = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.63))
crystal2 = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
crystals = [crystal1, crystal2]
latex = crystals_to_latex_table(
    crystals,
    caption='NaCl polymorphs',
    label='tab:nacl',
)
print(latex)

# Save to file
save_latex_table(crystals, 'structures.tex')
```

### Builders

```python
from matsimpy.builders import (
    from_prototype, generate_slab,
    build_tetrahedral, build_carbon_nanotube,
    create_vacancy, create_interstitial, add_adsorbate,
    generate_random_alloy, create_simple_interface,
)

# Build bulk structures from prototypes
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
bcc_fe = from_prototype('bcc', 'Fe', 2.87)
diamond_c = from_prototype('diamond', 'C', 3.57)

# Create surface slabs with adsorbates
slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)
with_ads = add_adsorbate(slab, 'O', (0.5, 0.5), 2.0)

# Generate supercell
from matsimpy.transformation import make_supercell
supercell = make_supercell(fcc_cu, [4, 4, 4])

# Build molecules
ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)

# Create defects
with_vacancy = create_vacancy(fcc_cu, 0)
with_interstitial = create_interstitial(fcc_cu, 'H', position=[0.5, 0.5, 0.5])

# Generate alloys
alloy = generate_random_alloy(supercell, ['Ni'], 'Cu', [0.25])

# Build nanotubes
cnt = build_carbon_nanotube(10, 0)

# Create interfaces
interface = create_simple_interface(fcc_cu, bcc_fe)
```

### Transformations

Transformation helpers are functional: they return new structures and preserve
the original object. Crystal-returning transformations preserve periodic
boundary conditions (`pbc`) unless a function explicitly documents otherwise.
Site metadata (`site_properties`) is preserved, reindexed, duplicated, or
dropped by an explicit policy for transformations that reorder or synthesize
sites.

```python
from matsimpy.transformation import (
    translate, rotate, apply_strain, scale_lattice,
    substitute, make_supercell, move_atoms,
)
from matsimpy.transformation.registry import registry

# Geometric transformations
translated = translate(crystal, [1, 1, 1])
rotated = rotate(translated, 90.0, [0, 0, 1])

# Lattice transformations
strained = apply_strain(
    crystal,
    [[0.05, 0, 0], [0, 0, 0], [0, 0, 0]],  # 5% uniaxial strain
)
scaled = scale_lattice(crystal, 1.1)              # Scale by 10%

# Chemical transformations
substituted = substitute(crystal, [0], 'Ge')

# Atomic transformations
moved = move_atoms(crystal, [0, 1], [0.1, 0, 0])

# Structural transformations
supercell = make_supercell(crystal, [2, 2, 2])    # 2x2x2 supercell

# Registry — apply transformations by name with type validation
result = registry.apply('translate', crystal, vector=[1, 0, 0])
spec = registry.get('translate')                   # TransformationSpec metadata
```

Metadata and capability notes:

- `swap_atoms()` and `sort_atoms()` reindex `site_properties` with the atoms.
- `merge_atoms()` keeps the merged site's source metadata; `split_atom()` copies
  the source site's metadata to each split site.
- `make_supercell()` preserves `pbc` and repeats site metadata for generated
  images, including non-diagonal integer scaling matrices.
- `standardize_cell()` uses spglib when available and intentionally drops
  `site_properties` when the standardized cell may reorder or change sites.
- APIs that are not implemented yet, such as `get_niggli_reduced()`,
  `fragment_molecule()`, and `generate_conformers()`, raise
  `NotImplementedError` instead of returning placeholder structures.

### High-throughput transformations

```python
from matsimpy.transformation.composite import (
    TransformationPipeline, ParameterSweep, BatchProcessor
)
from matsimpy.transformation import make_supercell, apply_strain
from matsimpy.transformation.registry import registry
from matsimpy.builders.bulk import from_prototype

# 1. TransformationPlan — serializable sequence of named, registered transforms
from matsimpy.transformation import TransformationStep, TransformationPlan

plan = TransformationPlan(
    steps=[
        TransformationStep("make_supercell", {"scaling_matrix": [2, 2, 2]}),
        TransformationStep("translate", {"vector": [1.0, 0, 0]}),
    ],
    name="2x2x2 supercell + shift",
)
crystal = from_prototype('diamond', 'Si', 5.43)
result = registry.apply_plan(plan, crystal)

# 2. Parameter sweep
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
    mode='cartesian'
)
for struct, params in sweep:
    print(f"Strain: {params['strain']}, Formula: {struct.formula}")

# 3. Batch processing
def make_2x2x2_supercell(s):
    return make_supercell(s, [2, 2, 2])

processor = BatchProcessor(
    transformations=[make_2x2x2_supercell],
    n_workers=1,
    progress=True,
    error_handling='skip'
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

```python
from matsimpy.storage import DataStorage, MemoryBackend
from matsimpy.builders.bulk import from_prototype

# In-memory storage (for testing)
storage = DataStorage(backend=MemoryBackend())

# For persistent storage, use MaggmaBackend:
# from matsimpy.storage import MaggmaBackend
# storage = DataStorage(backend=MaggmaBackend(store_path='mydata.json'))

# Store crystal structure — returns stable sha256 ID
crystal = from_prototype('diamond', 'Si', 5.43)
doc_id = storage.store_data(crystal, metadata={'description': 'Si primitive cell'})

# Store calculation results
results = {'energy': -10.5, 'forces': [[0,0,0]]}
storage.store_data(results, metadata={'calculator': 'LJ'})

# Retrieve — auto-decodes to Crystal or raw dict
retrieved = storage.retrieve_data(doc_id)
print(retrieved.formula)  # Si2

# Query by metadata
lj_results = storage.query({'metadata.calculator': 'LJ'})

# ID is content-addressed — same data → same ID
id1 = storage.store_data(crystal)
id2 = storage.store_data(crystal)
assert id1 == id2

storage.close()
```

### AI REPL

Interactive LLM-powered assistant. Chat in natural language — the AI calls MatSimPy functions.

```bash
# Install with AI extras
pip install -e .[ai]

# Set API key
export DEEPSEEK_API_KEY="sk-..."

# Interactive REPL
matsimpy-ai
matsimpy-ai --workspace ~/my-project --model deepseek-v4-pro

# Single-shot command
matsimpy-ai -c "create fcc Cu crystal and save to cu.vasp"
matsimpy-ai -v -c "analyze bonds in nacl.cif"
```

```python
from matsimpy.ai import AIEngine, SkillManager, Skill
from matsimpy.ai.skills import core, builders, analysis

engine = AIEngine(model="deepseek-v4-pro")
for mod in (core, builders, analysis):
    engine.skill_manager.register(Skill(mod.SKILL_NAME, mod.SKILL_DESCRIPTION, mod.get_functions()))
engine.skill_manager.load("core")

# Natural language → function calls
response = engine.chat("Create an FCC Cu crystal and analyze its structure")
print(response)
```

Skills load progressively — builders load when user mentions "slab" or "vacancy", analysis loads for "bond" or "symmetry". Agent memory persists across sessions (`~/.matsimpy/ai/memory/`).

The AI REPL and `matsimpy-ai -c` share the same agent runtime. The runtime records searchable task traces in `~/.matsimpy/ai/state.db`, keeps compact memory files in `~/.matsimpy/ai/memory/`, and proposes reusable workflow skills as drafts. Draft skills are disabled until approved with `/approve-skill <name>`.

Runtime commands:

```text
/trace
/drafts
/approve-skill <name>
```

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

## Project Structure

```
matsimpy/
├── core/              # Core data structures
│   ├── crystal.py     # Crystal class
│   ├── molecule.py    # Molecule class
│   ├── structure.py   # Structure ABC
│   ├── lattice.py     # Lattice class
│   ├── composition.py # Composition class
│   ├── site.py        # Site classes
│   ├── periodic_table.py  # Element and periodic table
│   ├── _validation.py # Core validation helpers
│   └── protocols.py   # StructureLike, CrystalLike, MoleculeLike
│
├── builders/          # Structure builders
│   ├── bulk/          # Bulk crystal structures (prototypes, symmetry)
│   ├── surface/       # Surface slabs and adsorbates
│   ├── alloy/         # Alloy generation (random, ordered, intermetallic, Heusler)
│   ├── molecule/      # Molecular structure builders
│   ├── defects/       # Point defect creation (vacancy, interstitial, substitution, etc.)
│   ├── interface/     # Interface/hybrid structure builders
│   ├── nanostructure/ # Nanotubes and twisted structures
│   ├── registry.py    # BuilderRegistry + BuilderSpec
│   └── _register.py   # Auto-registration of built-in builders
│
├── transformation/    # Structure transformations
│   ├── geometric/     # Translation, rotation
│   ├── lattice/       # Lattice strain, scaling, transformations
│   ├── atomic/        # Atom manipulation and organization
│   ├── chemical/      # Chemical substitutions
│   ├── structural/    # Supercell, molecular operations
│   ├── composite/     # Pipeline, ParameterSweep, BatchProcessor, TransformationPlan
│   ├── spec.py        # TransformationSpec dataclass
│   ├── registry.py    # TransformationRegistry singleton
│   └── _register.py   # Auto-registration of built-in transformations
│
├── io/                # File IO, converters, and export helpers
│   ├── core.py        # High-level read/write interface
│   ├── registry.py    # FormatHandler + FormatRegistry (table-driven dispatch)
│   ├── vasp.py        # VASP POSCAR/CONTCAR
│   ├── cif.py         # CIF format
│   ├── xyz.py         # XYZ format
│   ├── pdb.py         # PDB format
│   ├── mol.py         # MOL format
│   ├── xsf.py         # XSF format
│   ├── ase.py         # ASE format and converters
│   ├── pymatgen.py    # pymatgen converters
│   ├── latex.py       # LaTeX table export
│   └── json.py        # JSON serialization
│
├── analysis/          # Analysis tools
│   ├── graph.py       # StructureGraph, MoleculeGraph, CrystalGraph
│   ├── neighbors.py   # Neighbor finding (find_points_in_spheres)
│   ├── bonding.py     # BondAnalyzer (bonds, angles, dihedrals)
│   ├── structure.py   # StructureAnalyzer (COM, inertia, density)
│   ├── topology.py    # TopologyAnalyzer (connectivity, rings, paths)
│   └── selection.py   # AtomSelection + select_by_species, etc.
│
├── storage/           # Data storage
│   ├── facade.py      # DataStorage (user-facing API)
│   ├── schema.py      # DocumentEnvelope + stable ID generation
│   ├── codec.py       # DocumentCodec (encode/decode)
│   ├── backend.py     # StoreBackend protocol
│   ├── memory_store.py # MemoryBackend (in-memory, for testing)
│   └── maggma_store.py # MaggmaBackend (persistent, via maggma)
│
├── utils/             # General-purpose utilities
│   ├── validation.py  # validate_vector3, validate_positive_scalar, etc.
│   ├── dict_utils.py  # get_nested_value, set_nested_value, copy_properties
│   └── path_utils.py  # expand_path
│
├── calculator/        # Energy/force calculators
├── config/            # Global configuration (ConfigManager)
├── symmetry/          # Symmetry analysis (spglib)
├── ai/                # Optional AI REPL and skill runtime
├── exceptions.py      # MatSimPyError, FormatError, StructureTypeError, etc.
├── plugins.py         # Plugin discovery via entry points
└── constants.py       # POSITION_TOL, LATTICE_TOL
```

## AI Command-Line Interface

MatSimPy includes an optional AI command-line interface in the `[ai]` extra:

```bash
# Install AI dependencies
pip install -e .[ai]

# Launch interactive REPL
matsimpy-ai

# Run a single natural-language task
matsimpy-ai -c "create fcc Cu crystal and save to cu.vasp"
```

The AI CLI provides natural-language access to structure generation, transformations, analysis, format conversion, storage, and calculator helpers through MatSimPy tool calls.

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

**Note**: v0.8.0 — optional AI REPL with LLM function calling, shared agent runtime, task traces, agent memory, and approval-gated draft skills.
