# MatSimPy

**MatSimPy (Materials Simulation in Python)** is a Python library for building, transforming, analyzing and storing crystal and molecular structures. It also simulates them, evaluating structures with a classical potential, an ML potential (MatterSim) or DFT through VASP, Gaussian and LAMMPS. An optional AI agent ([docs/ai.md](docs/ai.md)) can drive the library through its tools, Skills and MCP servers. Structures are immutable, so every change returns a new object and building, transforming and analyzing compose into reproducible scripts.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-Beta-brightgreen)](https://gitee.com/haidi-hfut/MatSimPy)
[![Tests](https://img.shields.io/badge/tests-core%20suite-brightgreen)](tests/)

**Version**: v0.11.0 (see [CHANGELOG.md](CHANGELOG.md))

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Conventions](#core-conventions)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [Testing](#testing)
- [Documentation](#documentation)

## Features

- 🧱 **Core structures** — `Crystal` (periodic + lattice), `Molecule` (non-periodic), `Lattice` (14 Bravais types), `Composition`, `Site`, `Element` (118 elements). Immutable: `add_atom`, `remove_atom`, `substitute` and `sort_atoms` return new objects
- 🏗️ **Builders** (7 domains, 29 functions) — `from_prototype` (9 prototypes: fcc/bcc/hcp/sc/diamond/rocksalt/zincblende/wurtzite/perovskite), `generate_slab` (primitive surface cells, any hkl), `generate_random_alloy`, `build_heusler`, `build_nanotube` (rolls any 2D sheet: hexagonal, square, rectangular), commensurate twisted bilayers and multilayers, `create_vacancy`, `add_adsorbate`, etc. via `BuilderRegistry`
- 🔁 **Transformations** (5 categories, 26 functions) — `translate`, `rotate`, `apply_strain`, `make_supercell`, `substitute`, `move_atoms`, `scale_lattice`, etc. via `TransformationRegistry` with `TransformationSpec` metadata, and `TransformationPlan` for reproducible pipelines
- 🔬 **Analysis** (6 modules) — `BondAnalyzer` (bonds/angles/dihedrals/orders), `StructureAnalyzer` (COM/inertia/density), `TopologyAnalyzer` (connectivity/rings/paths), graph/neighbor functions, `AtomSelection` (9 selectors)
- 💾 **IO** (9 formats) — VASP/CIF/XYZ/PDB/XSF/MOL/JSON/ASE, auto-detected through a table-driven `FormatRegistry`; `read()`/`write()`, third-party conversion and LaTeX table helpers
- 🔷 **Symmetry** — space groups, conventional/primitive cells, high-symmetry k-paths for 3D and 2D (layer) crystals, and AFLOW-style prototype identifiers (`AB_cF8_225_a_b`) with a `PrototypeDatabase`
- 🗄️ **Storage** — `DataStorage` with `MemoryBackend` (testing) and `MaggmaBackend` (persistent), content-addressed sha256 IDs and the `DocumentEnvelope` schema
- 🧩 **Extensibility** — plugin entry points for registries, including IO formats
- 🤖 **AI agent** — optional LLM agent (DeepSeek or any OpenAI-compatible API) that calls MatSimPy functions marked with `@tool`; extensible with Agent Skills and MCP servers, and itself an MCP server. See [docs/ai.md](docs/ai.md)
- ⚡ **Calculators** — `LennardJones` (classical), ML (MatterSim) and DFT file/workflow interfaces for VASP, Gaussian and LAMMPS (optional)

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

# I/O converters and VASP HDF5 (pymatgen, ase, h5py)
pip install -e .[io]

# Structure builders (pyxtal, rdkit)
pip install -e .[builders]

# Symmetry analysis (spglib)
pip install -e .[analysis]

# Reproduce VASP compatibility checks against the pinned oracle
pip install -e '.[dev,parity]'

# Data storage (maggma)
pip install -e .[storage]

# AI agent
pip install -e .[ai]

# Everything
pip install -e .[all]
```

The normal VASP runtime has no pymatgen dependency. `spglib` is needed only
when an input workflow asks MatSimPy to derive symmetry information (including
irreducible meshes and symmetry-standardized cells). `h5py` is needed only to
read and rewrite VASP HDF5 data. The `parity` extra is for development and
installs the pinned `pymatgen==2025.6.14` behavioral oracle; it is not a
runtime fallback.

## Quick Start

Structures are **immutable** — all mutation methods return new objects without modifying the original.

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

# Per-site properties (one value per atom) and structure-level metadata
magnetic = crystal.with_site_property('magmom', [1.0, -1.0])
print(magnetic.site_property('magmom'))       # [1.0, -1.0]
tagged = magnetic.with_metadata(source='example')
print(tagged.metadata['source'])              # example (read-only mapping)

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
from matsimpy import Crystal, Lattice, Molecule
molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
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
    build_tetrahedral, build_carbon_nanotube, build_nanotube,
    build_magic_angle_twisted, build_full_heusler,
    create_vacancy, create_interstitial, add_adsorbate,
    generate_random_alloy, create_simple_interface,
)
from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry import SpacegroupAnalyzer

# Build bulk structures from prototypes (primitive cells)
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
bcc_fe = from_prototype('bcc', 'Fe', 2.87)
diamond_c = from_prototype('diamond', 'C', 3.57)
mg = from_prototype('hcp', 'Mg', 3.21, c=5.21)
co2mnsi = build_full_heusler('Co', 'Mn', 'Si', 5.65)  # L2_1, Fm-3m

# Surface slabs: Miller indices refer to the cell given, so use the conventional one
cu_conventional = SpacegroupAnalyzer(fcc_cu).get_conventional_standard_structure()
slab = generate_slab(cu_conventional, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)
with_ads = add_adsorbate(slab, 'O', (1 / 3, 1 / 3), 1.2)

# Generate supercell
from matsimpy.transformation import make_supercell
supercell = make_supercell(fcc_cu, [4, 4, 4])

# Build molecules
ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)

# Create defects
with_vacancy = create_vacancy(fcc_cu, 0)
with_interstitial = create_interstitial(fcc_cu, 'H', [0.5, 0.5, 0.5])

# Generate alloys
alloy = generate_random_alloy(supercell, ['Ni'], 'Cu', [0.25])

# Build nanotubes: carbon, or rolled from any 2D sheet (thick sheets become coaxial shells)
cnt = build_carbon_nanotube(10, 0)
mos2 = Crystal(['Mo', 'S', 'S'], [[1/3, 2/3, 0.5], [2/3, 1/3, 0.578], [2/3, 1/3, 0.422]],
               Lattice.hexagonal(3.16, 20.0))
mos2_tube = build_nanotube(mos2, (10, 10))

# Twisted bilayer graphene at an exactly commensurate angle ((1, 2): 21.79 degrees)
graphene = Crystal(['C', 'C'], [[0, 0, 0.5], [1/3, 2/3, 0.5]], Lattice.hexagonal(2.46, 15.0))
tblg = build_magic_angle_twisted(graphene, 1, 2)

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
from matsimpy.builders import from_prototype
from matsimpy.transformation.registry import registry

crystal = from_prototype('diamond', 'Si', 5.43)

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
from matsimpy import Crystal, Lattice, Molecule

crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])

# Auto-detect format from file extension
write(crystal, 'structure.vasp')
write(molecule, 'molecule.xyz')

# Read structures (format auto-detected)
crystal = read('structure.vasp')
molecule = read('molecule.xyz')

# Explicit format specification
crystal = read('structure.vasp', format='vasp')
write(crystal, 'output.txt', format='cif', title='My Structure')
```

**Format-specific functions (advanced use):**

```python
from matsimpy.io.vasp import write_POSCAR, read_POSCAR
from matsimpy.io.xyz import write_XYZ, read_XYZ
from matsimpy import Crystal, Lattice, Molecule

crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])

# Direct format-specific access
write_POSCAR(crystal, 'structure.vasp')
write_XYZ(molecule, 'molecule.xyz')
molecule = read_XYZ('molecule.xyz')
```

### Calculators

```python
from matsimpy import Crystal, Lattice
from matsimpy.calculator import LennardJones

# Classical potential calculator
crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.0))
calc = LennardJones(sigma=3.4, epsilon=0.0104)

# Immutable, typed results (energy in eV, forces in eV/Å, stress in eV/Å³)
result = calc.compute(crystal)
print(result.energy, result.forces.shape, result.stress_voigt)

# Convenience getters share the same cache
energy = calc.get_potential_energy(crystal)
forces = calc.get_forces(crystal)
```

Results are cached on the calculator by the structure's exact fingerprint
(LRU over the last `calc.cache_size` structures, default 8), so one calculator
can be reused across many structures; structures never carry a calculator.

External codes (VASP, Gaussian, LAMMPS) use the same `compute()`; the two file
steps can also be called on their own (offline workflow):

```python notest
from matsimpy.calculator import VaspCalculator

calc = VaspCalculator(directory="si_run", incar={"ENCUT": 400}, kpoints=[4, 4, 4])
r = calc.compute(crystal)                  # write_input -> run VASP -> read_results
calc.write_input(crystal, "si_offline")    # inputs only; run VASP yourself
r = calc.read_results("si_offline")        # -> Results
```

MatterSim needs the separate `mattersim` package and either a valid local model
file or a supported pretrained-model shortcut. Model weights may be downloaded
by MatterSim and are not bundled with MatSimPy.

```python notest
from matsimpy.calculator import Mattersim

ml_calc = Mattersim(model_path='model.pth', model_type='mace')
energy = ml_calc.get_potential_energy(crystal)
```

### Configuration

```python
from matsimpy.config import get_config, ConfigManager

# Get configuration values
device = get_config('calculator.mattersim.default_device')  # 'cpu'
model_dir = get_config('paths.models')  # '~/.matsimpy/models'

# Modify configuration
config = ConfigManager()
config.set('calculator.mattersim.default_device', 'cuda', save=True)
```

### Symmetry analysis

```python
from matsimpy.builders.bulk import from_prototype
from matsimpy.symmetry import get_conventional_cell, get_symmetry_info

# Create crystal structure
crystal = from_prototype('diamond', 'Si', 5.43)

# Get symmetry information
sym_info = get_symmetry_info(crystal)
print(f"Space group: {sym_info['space_group_symbol']}")  # Fd-3m
print(f"Point group: {sym_info['point_group']}")        # m-3m
print(f"Crystal system: {sym_info['crystal_system']}")  # Cubic

# Get conventional cell
conventional = get_conventional_cell(crystal)
print(f"Primitive: {len(crystal)} atoms")         # 2 atoms
print(f"Conventional: {len(conventional)} atoms") # 8 atoms
```

High-symmetry k-paths follow `pbc`. A crystal with one non-periodic axis (a
monolayer in a slab cell) gets the path of its 2D Bravais lattice (`mp`, `op`,
`oc`, `tp` or `hp`), with no k-points along the vacuum axis. Fewer than two
periodic axes raise `ValueError`.

```python
from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry import HighSymmKpath

graphene = Crystal(['C', 'C'], [[1/3, 2/3, 0.5], [2/3, 1/3, 0.5]],
                   Lattice.hexagonal(2.46, 20.0), pbc=[True, True, False])
kpath = HighSymmKpath(graphene)
print(kpath.bravais)               # hp
print(kpath.kpath['path'])         # [['\\Gamma', 'M', 'K', '\\Gamma']]
print(kpath.kpath['kpoints']['K']) # fractional K point: (1/3, 1/3, 0)
```

Prototype identifiers name the structure type in the style of AFLOW labels:
anonymized formula, Pearson symbol of the conventional cell, space-group number
and canonical Wyckoff letters. They do not depend on the cell, origin, axis
order, atom order or elements. By default the symmetry tolerance is chosen per
crystal (`symprec=None`, 1/100 of the shortest interatomic distance, halved
until consistent).

```python
from matsimpy.builders.bulk import from_prototype
from matsimpy.symmetry import PrototypeDatabase, get_prototype, get_prototype_info

nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
print(get_prototype(nacl))         # AB_cF8_225_a_b
info = get_prototype_info(nacl)    # frozen PrototypeInfo
print(info.pearson_symbol, info.space_group_symbol, info.symprec)

# a read-only map from identifier to structure names (JSON load/save)
database = PrototypeDatabase().with_structures([('NaCl.vasp', nacl)])
print(database['AB_cF8_225_a_b'])  # ('NaCl.vasp',)
```

`matsimpy.builders.bulk.build_prototype_database(files)` builds a database from
structure files, and `structures_from_prototype(database, prototype,
structures_dir, element_substitutions)` makes new crystals from a prototype's
template by element substitution.

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

### AI agent

An optional LLM agent (`pip install -e .[ai]`) that works through MatSimPy functions.
The full guide, including adding tools, writing Skills and configuring MCP servers, is
[docs/ai.md](docs/ai.md).

```bash
export DEEPSEEK_API_KEY="sk-..."
matsimpy-ai                                   # interactive; /help lists the commands
matsimpy-ai -c "build rocksalt NaCl with a=5.64 angstrom and save it as nacl.cif"
matsimpy-ai doctor                            # check key, workspace, tools, skills, MCP
matsimpy-ai mcp serve -w ~/project            # serve MatSimPy's tools to other MCP clients
```

```python notest
from matsimpy.ai import Agent

with Agent(workspace="project") as agent:
    result = agent.run("Create FCC copper, analyze it, and save copper.cif")
    print(result.status, result.response, [call.name for call in result.tool_calls])
```

- **Tools** come from MatSimPy functions marked with `@tool`
  (`matsimpy.utils.tooling`). Their names, schemas and descriptions are read from the
  signature and docstring, so new library functions reach the model without wrappers.
- **Skills** are folders with a `SKILL.md` (Agent Skills format) and an optional
  `tools.py`. They are loaded only when activated. Manage them with
  `matsimpy-ai skills install|remove|validate`. Skills the model proposes stay drafts
  until `/approve`.
- **MCP**: servers listed in `~/.matsimpy/ai/mcp.json` or `<workspace>/mcp.json`
  (stdio or Streamable HTTP) add their tools to the agent.
- **Sessions** are JSON files in `<workspace>/.matsimpy/sessions/` (`/resume`,
  `/undo`, `/retry`).

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
│   ├── bulk/          # Bulk crystals: prototypes, prototype databases, random crystals
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
├── symmetry/          # Space groups, k-paths (3D and 2D), prototype identifiers (spglib)
├── ai/                # Optional LLM agent: tools, Skills, MCP, REPL (docs/ai.md)
├── exceptions.py      # MatSimPyError, FormatError, StructureTypeError, etc.
├── plugins.py         # Plugin discovery via entry points
└── constants.py       # POSITION_TOL, LATTICE_TOL
```

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
- **AI agent**: `ai/extending.py` (custom tool, Skill and MCP, offline) and `llm/` (live LLM scenarios with a judge)

Run an example:

```bash
python examples/core_basic.py
python examples/builders_bulk.py
```

## Testing

```bash
# Run all tests (single worker; the suite takes about 90 s)
pytest -q -p no:xdist

# Run specific packages
pytest tests/core -q
pytest tests/calculator -q
pytest tests/symmetry -q

# Show the slowest tests
pytest -q -p no:xdist --durations=10
```

Tests that compare against pymatgen or ASE are skipped when those optional
packages are not installed. VASP test data are unmodified pymatgen test files;
their sources are listed in `tests/calculator/fixtures/vasp/PROVENANCE.md`.

## Documentation

- **Changes and upgrades**: [CHANGELOG.md](CHANGELOG.md)
- **Examples**: the `examples/` directory
- **AI agent**: [docs/ai.md](docs/ai.md)
- **API reference**: module docstrings; `docs/conf.py` configures a Sphinx autodoc build
- **Third-party code**: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

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
