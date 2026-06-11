# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode with dev deps (pytest, pytest-cov, pytest-xdist)
pip install -e .[dev]

# Run all tests (1462+ tests)
pytest

# Run specific test modules
pytest tests/test_core*.py -v                    # Core (Structure, Crystal, Molecule, Lattice, Composition)
pytest tests/test_builders_*.py -v               # Structure builders
pytest tests/test_transformation*.py -v           # Transformations
pytest tests/test_io_*.py -v                     # File I/O
pytest tests/test_calculator_*.py -v              # Calculators
pytest tests/test_storage*.py -v                  # Storage
pytest tests/test_analysis*.py -v                 # Analysis (graph, bonding, topology)
pytest tests/contracts/ -v                        # Contract tests (parametrized over registries)
pytest tests/integration/ -v                      # Integration tests (cross-layer workflows)

# Skip slow tests or tests requiring optional deps
pytest -m "not slow"
pytest -m "not requires_torch and not requires_ase and not requires_pymatgen"

# Quick run (no output, show slowest)
pytest --tb=no -q
pytest tests/ -v --durations=10

# Coverage
pytest --cov=matsimpy --cov-report=html

# Run examples (uses conda env python for correct deps)
cd examples && bash run.sh
```

## Core Architecture

### Class Hierarchy

```
Structure (ABC, MSONable)    # core/structure.py — shared logic, species/positions/editing
├── Crystal                  # core/crystal.py — periodic, has Lattice, frac+cart coords, PBC
└── Molecule                 # core/molecule.py — non-periodic, no lattice, Cartesian only
```

Supporting core classes: `Lattice`, `Composition`, `Site`, `CrystalSite`, `Element` (all MSONable).

### Core Protocols (`matsimpy/core/protocols.py`)

`StructureLike`, `CrystalLike`, `MoleculeLike` — runtime-checkable protocols for type constraints. Used by transformations, IO handlers, and builders to declare input types without importing concrete classes (avoiding circular imports).

### Core Domain Rule

`core` must not import from `builders`, `transformation`, `io`, `storage`, or `analysis`. It may import from `utils` and `constants`.

### Immutability Contract

All mutation methods return **new** objects without modifying the original. This applies to `add_atom`, `remove_atom`, `substitute`, `sort_atoms`, all transformations, etc. Internal numpy arrays have `writeable=False`. Callers must capture the return value:

```python
doped = crystal.add_atom('H', [0.1, 0, 0])  # new Crystal, original unchanged
```

### `_construct` — Fast Internal Constructor

Every mutation route goes through `cls._construct(species, positions, lattice, **kwargs)`, which uses `cls.__new__(cls)` to bypass `__init__` and skip validation. This is the performance-critical path. Do not call `__init__` in mutation methods.

### Coordinate Convention (critical)

- **`Structure.positions`** is **always Cartesian** (Å) — the public API invariant across all subclasses.
- **`Structure._positions`** (backing field): convention varies by subclass. The base class stores whatever `__init__` receives with no conversion.
- **`Crystal._positions`** stores **fractional** coordinates. `Crystal.__init__` accepts `coords_are_cartesian=False` by default (fractional input). When `coords_are_cartesian=True`, Cartesian input is converted to fractional before calling `super().__init__()`. Crystal **overrides** `positions` to return `self.cart_positions` (computed from `_frac_positions @ lattice.matrix`), maintaining the Cartesian public API.
- **`Molecule._positions`** stores **Cartesian** directly — same as the public API. No override needed.

`Crystal.add_atom` overrides Structure's base method: if `coords_are_cartesian=True`, it converts to fractional before calling `_construct`. Molecule inherits the base `add_atom` (passes through to `_construct` as-is, always Cartesian).

### Subclass Extension Hooks

Subclasses that store per-atom data beyond `species`/`positions` (e.g., `site_properties`) use three hooks. The base class mutation methods (`add_atom`, `remove_atom`, `sort_atoms`) call these automatically:

- `_construct_kwargs()` — extra kwargs forwarded to `_construct` in every mutation
- `_filter_per_atom_data(kept_indices)` — called by `remove_atom` to trim per-atom lists
- `_reorder_per_atom_data(new_order)` — called by `sort_atoms` to reorder per-atom lists

### Calculator Pattern

Attach a calculator via `.calc = calculator`, then call `get_potential_energy()`, `get_forces()`, or `get_stress()`. The structure auto-triggers `calculator.calculate(self)` when state has changed (detected via hash comparison). `get_stress()` raises `NotImplementedError` on Molecule.

### Error Handling (`matsimpy/exceptions.py`)

Domain-specific exception hierarchy:
- `MatSimPyError` — base for all MatSimPy errors
- `FormatError` — malformed file input
- `StructureTypeError` (also TypeError) — structure type mismatch
- `RegistryError` — duplicate/unknown spec or handler
- `ValidationError` (also ValueError) — invalid structure data
- `StorageError` — backend failures

Default policy: **strict** — invalid input raises. Tolerant parsing requires explicit `strict=False`.

---

## Module Guide

### Transformation Modules (`matsimpy/transformation/`)

Organized by domain:
- `geometric/` — translate, rotate (both Crystal + Molecule)
- `lattice/` — strain, scale, transform (Crystal only)
- `atomic/` — move, swap, merge, split atoms (both)
- `chemical/` — substitute (both)
- `structural/` — supercell, molecular ops, interface
- `composite/` — Pipeline, BatchProcessor, ParameterSweep, TransformationPlan

**Registry** (`transformation/registry.py` + `spec.py` + `_register.py`):
- `TransformationSpec` — frozen dataclass: name, category, callable, applicable_types, output_type, preserves_* flags, parameter_schema (JSON Schema), version
- `TransformationRegistry` — singleton with `register()`, `get()`, `apply()` (type-validated), `apply_plan()`, `list_by_category()`, `list_applicable()`
- 26 built-in transforms auto-registered at import time
- Direct function calls still work: `translate(crystal, [1,0,0])`
- Plugin entry point: `matsimpy.transformations`

**TransformationPlan** (`composite/plan.py`):
- `TransformationStep` — spec_name + params + label
- `TransformationPlan` — serializable list of steps; execution separated from description
- `PipelineExecutor`, `BatchExecutor`, `SweepExecutor` consume plans

All transformations return new objects (immutable-return).

### Builders (`matsimpy/builders/`)

Seven subdomains: `bulk/`, `surface/`, `alloy/`, `molecule/`, `defects/`, `interface/`, `nanostructure/`.

**Key rule**: builders are **constructors** (from parameters/prototypes). For modifying existing structures, use transformations. Builders internally depend on transformation functions (e.g., defects use `substitute`) — no code duplication.

**Registry** (`builders/registry.py` + `_register.py`):
- `BuilderSpec` — frozen dataclass: name, category, callable, output_type, parameter_schema, requires_optional
- `BuilderRegistry` — singleton with `register()`, `get()`, `build()`, `list_by_category()`
- Built-in builders auto-registered at import time
- Plugin entry point: `matsimpy.builders`

### IO (`matsimpy/io/`)

**FormatRegistry** (`io/registry.py`):
- `FormatHandler` — frozen dataclass: name, extensions, aliases, reader, writer, supports_crystal/molecule, strict_by_default, options_schema
- `FormatRegistry` — singleton: `register()`, `detect()`, `get()`, `read()`, `write()`. Triple-indexed by name, extension, alias
- Table-driven dispatch replaces old if/elif chain. Plugin entry point: `matsimpy.io_formats`

**High-level** (`io/core.py`): `read(filename)` / `write(structure, filename)` — delegates to registry. Thin ~15 lines.

**Format modules**: `vasp.py`, `cif.py`, `xyz.py`, `pdb.py`, `xsf.py`, `mol.py`, `json.py`, `ase.py`. Each registers its FormatHandler at import time.

**Converters and export helpers**: `io/pymatgen.py`, `io/ase.py`, and `io/latex.py` expose third-party conversion and LaTeX table helpers through `matsimpy.io`. Lazy imports raise `ImportError` with install hints when optional dependencies are missing.

### Analysis (`matsimpy/analysis/`)

- `graph.py` — `StructureGraph`, `MoleculeGraph`, `CrystalGraph`, functional API (`get_adjacency_matrix`, `get_shortest_path`, etc.), NetworkX export
- `neighbors.py` — `find_points_in_spheres()`, `validate_cutoff()`
- `bonding.py` — `BondAnalyzer` (bonds, angles, dihedrals, bond orders, coordination numbers)
- `structure.py` — `StructureAnalyzer` (COM, radius of gyration, inertia tensor, density, pair distances)
- `topology.py` — `TopologyAnalyzer` (connectivity, rings, shortest path — wraps graph.py)
- `selection.py` — `AtomSelection` class + 9 selection functions (by_species, by_position, by_box, etc.)

### Storage (`matsimpy/storage/`)

Split into four concerns:
- `schema.py` — `DocumentEnvelope` (wraps payload with sha256 content-addressed ID, schema_version, timestamp, metadata). Reserved field enforcement.
- `codec.py` — `DocumentCodec` (encode Structure → envelope, decode via MontyDecoder)
- `backend.py` — `StoreBackend` protocol (connect, put, get, query, delete, flush, close)
- `memory_store.py` — `MemoryBackend` (dict-based, for testing)
- `maggma_store.py` — `MaggmaBackend` (persistent, via maggma JSONStore/MemoryStore)
- `facade.py` — `DataStorage` (user-facing API composing codec + backend). Default: `MemoryBackend`

### Utils (`matsimpy/utils/`)

General-purpose utilities (no domain imports):
- `validation.py` — `validate_vector3()`, `validate_positive_scalar()`, `validate_integer_matrix3()`
- `dict_utils.py` — `get_nested_value()`, `set_nested_value()`, `copy_properties()`
- `path_utils.py` — `expand_path()`

### Config (`matsimpy/config/`)

Singleton `ConfigManager` with YAML-backed persistence. Accessed via `get_config("key.path")`. Config stored at `~/.matsimpy/config.yaml`.

### Plugin Discovery (`matsimpy/plugins.py`)

Entry point groups: `matsimpy.transformations`, `matsimpy.builders`, `matsimpy.io_formats`, `matsimpy.storage_backends`. Call `discover_plugins()` or `discover_all()`.

### Optional Dependencies

All non-core deps are optional and organized as pip extras: `cli`, `ml` (torch, torch-geometric), `io` (pymatgen, ase), `builders` (pyxtal, rdkit), `analysis` (spglib), `storage` (maggma). Tests use markers (`requires_torch`, `requires_ase`, `requires_pymatgen`) to skip when deps are absent.

### Serialization

All core objects implement monty's `MSONable` (via `as_dict()` / `from_dict()`). The `@module` and `@class` fields enable polymorphic deserialization. `Structure.from_dict` reconstructs the correct subclass (Crystal or Molecule) based on these fields.

### Test Architecture

```
tests/
├── contracts/          # Parametrized over registries — all specs/handlers/backends
├── core/               # Domain model tests (focused regressions)
├── builders/           # Constructor + modification tests
├── transformation/     # Operation tests + registry/spec tests
├── io/                 # Format round-trips, converters, LaTeX, malformed-input tests
├── storage/            # Backend contract tests (parametrized)
├── analysis/           # Graph, bonding, topology tests
├── integration/        # Cross-layer workflow tests (builder → transform → io → storage)
├── calculator/
├── config/
└── symmetry/
```

### Dependency Rules (Enforced)

```
core — imports nothing from matsimpy except constants.py
transformation → core, exceptions, utils
builders → core, transformation, exceptions
analysis → core, exceptions
io → core, exceptions (lazy-import optional pymatgen/ase at use time)
storage → core (serialization), exceptions
config → utils
```
