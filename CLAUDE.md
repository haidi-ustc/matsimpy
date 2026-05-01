# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode with dev deps (pytest, pytest-cov, pytest-xdist)
pip install -e .[dev]

# Run all tests (1295+ tests)
pytest

# Run specific test modules
pytest tests/test_core*.py -v                    # Core (Structure, Crystal, Molecule, Lattice, Composition)
pytest tests/test_graph*.py -v                   # Graph analysis
pytest tests/test_builders_*.py -v               # Structure builders
pytest tests/test_transformation*.py -v           # Transformations
pytest tests/test_composite*.py -v               # High-throughput (pipeline, sweep, batch)
pytest tests/test_io_*.py -v                     # File I/O
pytest tests/test_calculator_*.py -v              # Calculators

# Skip slow tests or tests requiring optional deps
pytest -m "not slow"
pytest -m "not requires_torch and not requires_ase and not requires_pymatgen"

# Quick run (no output, show slowest)
pytest --tb=no -q
pytest tests/ -v --durations=10

# Coverage
pytest --cov=matsimpy --cov-report=html
```

## Core Architecture

### Class Hierarchy

```
Structure (ABC, MSONable)    # core/structure.py — shared logic, species/positions/editing
├── Crystal                  # core/crystal.py — periodic, has Lattice, frac+cart coords, PBC
└── Molecule                 # core/molecule.py — non-periodic, no lattice, Cartesian only
```

Supporting core classes: `Lattice`, `Composition`, `Site`, `CrystalSite`, `Element` (all MSONable).

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

### Transformation Modules

Transformations live in `matsimpy/transformation/` and are organized by domain:
- `geometric/` — translate, rotate (both Crystal + Molecule)
- `lattice/` — strain, scale, transform (Crystal only)
- `atomic/` — move, swap, merge atoms
- `chemical/` — substitute
- `structural/` — supercell, molecular ops
- `composite/` — `TransformationPipeline`, `ParameterSweep`, `BatchProcessor`

All transformation functions return new objects. The `matsimpy.transformation` top-level package re-exports everything from all submodules.

### Builders (`matsimpy/builders/`)

Six subdomains: `bulk/`, `surface/`, `alloy/`, `molecule/`, `defects/`, `nanostructure/`. Most have optional dependencies (pyxtal, rdkit). `from_prototype()` in `bulk/prototype.py` supports 9 prototype structures (fcc, bcc, hcp, diamond, rocksalt, perovskite, etc.).

### IO (`matsimpy/io/`)

High-level `read()`/`write()` in `io/core.py` auto-detect format from file extension. Format-specific modules: `vasp`, `cif`, `xyz`, `pdb`, `mol`, `xsf`, `json`, `ase`. Converters to pymatgen/ASE live in `io/converters.py`. LaTeX table export in `io/latex.py`.

### Config (`matsimpy/config/`)

Singleton `ConfigManager` with YAML-backed persistence. Accessed via `get_config("key.path")`.

### Optional Dependencies

All non-core deps are optional and organized as pip extras: `cli`, `ml` (torch, torch-geometric), `io` (pymatgen, ase), `builders` (pyxtal, rdkit), `analysis` (spglib), `storage` (maggma). Tests use markers (`requires_torch`, `requires_ase`, `requires_pymatgen`) to skip when deps are absent. The core suite (no optional deps) includes: Structure, Crystal, Molecule, Lattice, Composition, Site, Element, graph, and all non-IO transformations.

### Serialization

All core objects implement monty's `MSONable` (via `as_dict()` / `from_dict()`). The `@module` and `@class` fields enable polymorphic deserialization. `Structure.from_dict` reconstructs the correct subclass (Crystal or Molecule) based on these fields.
