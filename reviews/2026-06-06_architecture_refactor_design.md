# MatSimPy Architecture Refactoring — Design Spec

Date: 2026-06-06
Status: Design approved
Based on: `reviews/codex_20260606_architecture_module_boundaries.md`

## Summary

Refactor MatSimPy's architecture to formalize module boundaries, introduce registries, separate concerns, and prepare for plugin extensibility. This is a clean break at v0.3.0 — no backward compatibility wrappers.

## Design Decisions

| Decision | Choice |
|---|---|
| Scope | Full target architecture, implemented in phases |
| Backward compatibility | Clean break — no compat wrappers |
| Builders/Transformations relationship | Builders depend on transformations internally; public API: builders construct, transformations modify |
| TransformationSpec | Structured dataclass with required metadata fields |
| Storage backends | MemoryBackend + MaggmaBackend (two) |
| Test reorganization | Contracts + reorganize + deduplicate |

---

## 1. Target Package Structure

```
matsimpy/
├── core/                    # domain model only
│   ├── structure.py         # trim IO + graph references
│   ├── crystal.py           # remove from_file/to_file
│   ├── molecule.py          # remove from_file/to_file
│   ├── lattice.py
│   ├── composition.py
│   ├── site.py
│   ├── periodic_table.py
│   ├── _validation.py
│   └── protocols.py         # NEW — StructureLike, CrystalLike, MoleculeLike
│
├── exceptions.py             # NEW — domain exception hierarchy
│
├── analysis/                # expanded
│   ├── graph.py             # moved from core.graph
│   ├── neighbors.py         # moved from core.neighbors
│   ├── bonding.py
│   ├── topology.py
│   └── structure.py
│
├── transformation/          # + registry + spec
│   ├── geometric/
│   ├── lattice/
│   ├── atomic/              # + defect operations from builders
│   ├── chemical/            # + alloy operations from builders
│   ├── structural/          # + interface operations from builders
│   ├── composite/
│   │   ├── pipeline.py      # PipelineExecutor
│   │   ├── batch.py         # BatchExecutor
│   │   ├── sweep.py         # SweepExecutor
│   │   └── plan.py          # NEW — TransformationPlan, TransformationStep
│   ├── spec.py              # NEW — TransformationSpec
│   └── registry.py          # NEW — TransformationRegistry
│
├── builders/                # constructors only
│   ├── bulk/                # from_prototype, random_crystal
│   ├── surface/             # generate_slab only (adsorbate → transformation)
│   ├── molecule/            # geometry constructors, smiles
│   ├── nanostructure/       # nanotube, twisted
│   └── registry.py          # NEW — BuilderRegistry
│   (defects/, alloy/, interface/ → transformation)
│
├── io/                      # table-driven dispatch
│   ├── registry.py          # NEW — FormatHandler, FormatRegistry
│   ├── core.py              # refactored: delegates to registry.read/write
│   ├── vasp.py, cif.py, xyz.py, pdb.py, xsf.py, mol.py, json.py, ase.py
│   └── utils.py             # trimmed
│   (converters.py → adapters/)
│   (latex.py → export/)
│
├── adapters/                # NEW — external library conversions
│   ├── __init__.py
│   ├── pymatgen.py          # to_pymatgen, from_pymatgen
│   └── ase.py               # to_ase, from_ase
│
├── export/                  # NEW — presentation/export
│   ├── __init__.py
│   └── latex.py             # moved from io/latex.py
│
├── storage/                 # split concerns
│   ├── schema.py            # NEW — DocumentEnvelope, stable ID generation
│   ├── codec.py             # NEW — DocumentCodec (encode/decode)
│   ├── backend.py           # NEW — StoreBackend protocol
│   ├── memory_store.py      # NEW — MemoryBackend
│   ├── maggma_store.py      # refactored as MaggmaBackend
│   └── facade.py            # DataStorage composing codec + backend
│
├── calculator/              (unchanged)
├── symmetry/                (unchanged)
├── config/                  (unchanged)
├── ai/                      (unchanged)
├── ui/                      (unchanged)
├── visualization/           (unchanged)
├── constants.py
└── __init__.py
```

### Dependency Rules (Enforced)

```
core — imports nothing from matsimpy except constants.py
transformation → core, exceptions, constants
builders → core, transformation (for internal modification steps), exceptions
analysis → core, exceptions
io → core, adapters, exceptions
adapters → core (lazy-import pymatgen/ase at use time)
export → core
storage → core (serialization), exceptions
```

---

## 2. TransformationSpec & Registry

### TransformationSpec (`matsimpy/transformation/spec.py`)

```python
@dataclass(frozen=True)
class TransformationSpec:
    """Metadata for a registered transformation."""

    name: str                    # "translate", "create_vacancy", "make_supercell"
    category: str                # "geometric" | "lattice" | "atomic" | "chemical" | "structural"
    callable: Callable           # the actual function
    description: str             # one-line human-readable

    # Type constraints
    applicable_types: tuple      # (Crystal,) | (Crystal, Molecule) | (Molecule,)
    output_type: type            # Crystal | Molecule

    # Behavior metadata
    preserves_composition: bool  # True for translate/rotate, False for substitution
    preserves_lattice: bool      # True for translate, False for strain/scale
    preserves_site_properties: bool
    preserves_pbc: bool

    # Parameter schema
    parameter_schema: dict       # JSON Schema fragment for **kwargs

    # Versioning
    version: str = "1.0.0"
```

### TransformationRegistry (`matsimpy/transformation/registry.py`)

```python
class TransformationRegistry:
    """Singleton registry for all transformation specs."""

    _specs: dict[str, TransformationSpec]

    def register(self, spec: TransformationSpec) -> None
    def get(self, name: str) -> TransformationSpec
    def list_by_category(self, category: str) -> list[TransformationSpec]
    def list_applicable(self, structure_type: type) -> list[TransformationSpec]
    def apply(self, name: str, structure, **kwargs) -> Structure
    def apply_plan(self, plan: TransformationPlan, structure) -> Structure

registry = TransformationRegistry()
```

### TransformationPlan (`matsimpy/transformation/composite/plan.py`)

```python
@dataclass
class TransformationStep:
    spec_name: str          # registry key
    params: dict            # kwargs for the callable
    label: str | None

@dataclass
class TransformationPlan:
    steps: list[TransformationStep]
    name: str | None
    description: str | None

    def to_dict(self) -> dict
    def from_dict(cls, d: dict) -> TransformationPlan

# Execution strategies (separate from plan definition):
PipelineExecutor.apply(plan, structure)       # sequential
BatchExecutor.apply(plan, structures)         # parallel over structures
SweepExecutor.apply(plan, structure, params)  # grid search over params
```

### Migration

- Direct function calls (`translate(crystal, [1,0,0])`) continue to work unchanged
- Registry is additive — functions are registered at import time
- `Pipeline`/`BatchProcessor`/`ParameterSweep` are refactored to consume `TransformationPlan` and delegate to the registry
- New plugins use `'matsimpy.transformations'` entry point to register

---

## 3. IO FormatHandler Registry

### FormatHandler (`matsimpy/io/registry.py`)

```python
@dataclass(frozen=True)
class FormatHandler:
    name: str                    # "vasp-poscar", "cif", "xyz"
    extensions: tuple[str, ...]  # (".vasp", ".poscar", "POSCAR")
    aliases: tuple[str, ...]     # ("poscar", "vasp")
    description: str

    reader: Callable | None      # read_POSCAR(filename, **kwargs) -> Structure
    writer: Callable | None      # write_POSCAR(structure, filename, **kwargs)

    supports_crystal: bool
    supports_molecule: bool

    strict_by_default: bool
    options_schema: dict         # JSON Schema for format-specific **kwargs
```

### FormatRegistry (`matsimpy/io/registry.py`)

```python
class FormatRegistry:
    _by_name: dict[str, FormatHandler]
    _by_extension: dict[str, FormatHandler]
    _by_alias: dict[str, FormatHandler]

    def register(self, handler: FormatHandler) -> None
    def detect(self, filename: str) -> FormatHandler | None
    def get(self, name: str) -> FormatHandler | None
    def read(self, filename: str, format: str | None = None, **kwargs) -> Structure
    def write(self, structure, filename: str, format: str | None = None, **kwargs) -> None

registry = FormatRegistry()
```

### Refactored io/core.py

Shrinks from 237 lines (if/elif chain) to ~15 lines:

```python
from .registry import registry

def read(filename, format=None, **kwargs):
    return registry.read(filename, format=format, **kwargs)

def write(structure, filename, format=None, **kwargs):
    registry.write(structure, filename, format=format, **kwargs)
```

### Registration Pattern

Each format module registers at import time:

```python
# matsimpy/io/vasp.py (bottom of file)
from .registry import registry, FormatHandler

handler = FormatHandler(
    name="vasp-poscar",
    extensions=(".vasp", ".poscar", "POSCAR"),
    aliases=("poscar", "vasp"),
    description="VASP POSCAR format",
    reader=read_POSCAR,
    writer=write_POSCAR,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
    options_schema={...}
)
registry.register(handler)
```

Plugin entry point: `'matsimpy.io_formats'`

### Moves

- `io/converters.py` → `adapters/pymatgen.py` + `adapters/ase.py`
- `io/latex.py` → `export/latex.py`

---

## 4. Storage — Schema / Codec / Backend / Facade

### DocumentEnvelope (`matsimpy/storage/schema.py`)

```python
@dataclass
class DocumentEnvelope:
    doc_id: str              # stable hash-based ID (content-addressed, sha256)
    payload: dict            # core object's as_dict() output
    schema_version: str      # "1.0.0"
    created_at: str          # ISO 8601
    metadata: dict           # user-provided tags/labels/provenance

    RESERVED_FIELDS = frozenset({"doc_id", "payload", "schema_version",
                                  "created_at", "metadata"})

    @staticmethod
    def generate_id(payload: dict, metadata: dict | None = None) -> str

    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, d: dict) -> DocumentEnvelope
```

### DocumentCodec (`matsimpy/storage/codec.py`)

```python
class DocumentCodec:
    def encode(self, obj: MSONable, metadata: dict | None = None,
               schema_version: str = "1.0.0") -> DocumentEnvelope
    def decode(self, envelope: DocumentEnvelope) -> Structure
```

### StoreBackend Protocol (`matsimpy/storage/backend.py`)

```python
@runtime_checkable
class StoreBackend(Protocol):
    def connect(self) -> None: ...
    def put(self, doc_id: str, document: dict) -> None: ...
    def get(self, doc_id: str) -> dict | None: ...
    def query(self, criteria: dict, limit: int = 100, offset: int = 0) -> list[dict]: ...
    def delete(self, doc_id: str) -> bool: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...
```

Two implementations: `MemoryBackend` (`memory_store.py`), `MaggmaBackend` (`maggma_store.py`).

### DataStorage Facade (`matsimpy/storage/facade.py`)

```python
class DataStorage:
    def __init__(self, backend: StoreBackend | None = None):
        self.codec = DocumentCodec()
        self.backend = backend or MemoryBackend()
        self.backend.connect()

    def store_data(self, obj: MSONable, metadata: dict | None = None) -> str
    def retrieve_data(self, doc_id: str) -> Structure
    def query(self, criteria: dict, limit=100, offset=0) -> list[Structure]
    def delete(self, doc_id: str) -> bool
    def flush(self) -> None
    def close(self) -> None
```

User API unchanged:

```python
storage = DataStorage()                             # defaults to MemoryBackend
storage = DataStorage(backend=MaggmaBackend(...))   # production
doc_id = storage.store_data(crystal, metadata={"source": "icsd"})
crystal = storage.retrieve_data(doc_id)
```

---

## 5. Error Handling Policy

### Exception Hierarchy (`matsimpy/exceptions.py`)

```python
class MatSimPyError(Exception): pass          # base
class FormatError(MatSimPyError): pass        # malformed files
class StructureTypeError(MatSimPyError, TypeError): pass  # type mismatch
class RegistryError(MatSimPyError): pass      # duplicate/unknown spec
class ValidationError(MatSimPyError, ValueError): pass   # invalid structure
class StorageError(MatSimPyError): pass       # backend failures
```

### Error Policy

| Situation | Exception | Example |
|---|---|---|
| Invalid scientific input | `ValueError` | Negative lattice parameter |
| Wrong type | `TypeError` | Molecule to lattice-only transform |
| Missing optional dependency | `ImportError` (at use time) | pyxtal not installed |
| Unsupported feature | `NotImplementedError` | `get_stress()` on Molecule |
| Malformed file / format | `FormatError` | Corrupted POSCAR |
| Document not found | `KeyError` | Unknown doc_id |
| Structure type mismatch | `StructureTypeError` | Crystal to .xyz |
| Tolerant parsing | opt-in via `strict=False` | `read('file.cif', strict=False)` |

Default: strict. Tolerant behavior requires explicit `strict=False`.

---

## 6. Core Cleanup

### Removed from Crystal / Molecule

- `Crystal.from_file()` → use `io.read(filename)`
- `Crystal.to_file()` → use `io.write(crystal, filename)`
- `Molecule.from_file()` → use `io.read(filename)`
- `Molecule.to_file()` → use `io.write(molecule, filename)`

### Moved out of core

- `core/graph.py` → `analysis/graph.py`
- `core/neighbors.py` → `analysis/neighbors.py`
- `core.__init__` stops exporting graph + neighbor functions

### New: core/protocols.py

```python
@runtime_checkable
class StructureLike(Protocol):
    species: tuple
    positions: np.ndarray
    lattice: object | None
    @property
    def formula(self) -> str: ...
    @property
    def composition(self) -> object: ...

@runtime_checkable
class CrystalLike(StructureLike, Protocol):
    lattice: object  # not None
    pbc: tuple[bool, bool, bool]
    @property
    def frac_positions(self) -> np.ndarray: ...
    @property
    def cart_positions(self) -> np.ndarray: ...

@runtime_checkable
class MoleculeLike(StructureLike, Protocol):
    lattice: None
```

### Core __init__.py

Exports domain model only: `Structure`, `Crystal`, `Molecule`, `Lattice`, `Composition`, `Site`, `CrystalSite`, `Element`.

---

## 7. Builders Refactoring

### Builder Moves

| From (builders/) | To (transformation/) |
|---|---|
| `defects/point.py` (6 functions) | `transformation/atomic/` — create_vacancy, create_interstitial, create_substitution, create_frenkel, create_schottky, create_antisite |
| `alloy/random.py` | `transformation/chemical/` — generate_random_alloy |
| `alloy/ordered.py` | `transformation/chemical/` — generate_ordered_alloy, generate_intermetallic |
| `surface/adsorbate.py` | `transformation/atomic/` — add_adsorbate |
| `interface/` | `transformation/structural/` — create_simple_interface |

### Builder Keeps

- `bulk/` — from_prototype(), random_crystal()
- `surface/slab.py` — generate_slab()
- `molecule/` — build_linear(), build_bent(), build_tetrahedral(), build_from_smiles()
- `nanostructure/` — build_nanotube(), build_carbon_nanotube(), build_twisted_bilayer(), build_magic_angle_twisted(), build_twisted_multilayer()

### BuilderRegistry (`matsimpy/builders/registry.py`)

```python
@dataclass(frozen=True)
class BuilderSpec:
    name: str
    category: str               # "bulk" | "surface" | "molecule" | "nanostructure"
    callable: Callable
    description: str
    output_type: type
    parameter_schema: dict
    requires_optional: tuple[str, ...]  # e.g. ("pyxtal",) or ()

class BuilderRegistry:
    _specs: dict[str, BuilderSpec]
    def register(self, spec: BuilderSpec) -> None
    def get(self, name: str) -> BuilderSpec
    def build(self, name: str, **kwargs) -> Structure
    def list_by_category(self, category: str) -> list[BuilderSpec]
```

### Builders Depend on Transformations (Internally)

Builders import and call transformation functions for modification steps — this is already the existing pattern, now made explicit:

```python
# matsimpy/builders/nanostructure/twisted.py
from matsimpy.transformation.structural import make_supercell
from matsimpy.transformation.geometric import rotate

def build_twisted_bilayer(bottom, top, angle):
    supercell = make_supercell(bottom, [n, n, 1])
    rotated_top = rotate(top, angle, [0, 0, 1])
    return stack_layers(supercell, rotated_top)
```

---

## 8. Public API & Namespace Cleanup

### Wildcard → Curated Exports

Both `builders/__init__.py` and `transformation/__init__.py` switch from `from .submodule import *` to explicit curated lists (~15 builders names, ~25 transformation names).

### Import Conventions (Documented)

- ✅ `from matsimpy.transformations.geometric import translate` — explicit, stable
- ✅ `from matsimpy.builders.bulk import from_prototype` — explicit, stable
- ✅ `from matsimpy.builders import from_prototype` — curated top-level (convenience)
- ⚠️ `from matsimpy.builders import *` — discouraged, warned in docs

### Removed from Top-Level Exports

- `structure_to_graph_data`, `find_points_in_spheres` from `core.__init__`
- All defect/alloy/interface functions from `builders.__init__`
- `get_reader_writer`, `is_crystal_format`, `is_molecule_format` from `io.__init__` (internal to registry)

---

## 9. Test Architecture

### Target Layout

```
tests/
├── contracts/                               # NEW
│   ├── test_structure_model_contract.py      # immutability, as_dict/from_dict, equality, hash
│   ├── test_transformation_contract.py       # all specs: new-object, properties, type constraints
│   ├── test_builder_contract.py              # all specs: output_type, optional deps
│   ├── test_io_format_contract.py            # all handlers: detect, round-trip, malformed→FormatError
│   └── test_storage_backend_contract.py      # MemoryBackend, MaggmaBackend: all 7 protocol methods
├── core/                    (focused regressions)
├── transformation/          (+ test_spec.py, test_registry.py)
├── builders/                (+ test_registry.py)
├── io/                      (+ test_registry.py)
├── adapters/                (NEW)
├── storage/                 (test_schema.py, test_codec.py, test_backend.py, test_facade.py)
├── integration/             (NEW — test_workflows.py)
├── calculator/
├── analysis/
├── config/
└── symmetry/
```

### Contract Test Design

Each contract file is parametrized over the registry:

- **test_structure_model_contract.py**: parametrized over Crystal variants, Molecule variants. Tests immutable-return on all mutation methods, species tuple immutability, `positions` writeable=False, `as_dict`/`from_dict` round-trip, equality/hash consistency.
- **test_transformation_contract.py**: parametrized over all registered `TransformationSpec`s. Tests every spec returns new object, preserves/alters correct properties per spec, rejects incompatible types, parameter_schema is valid.
- **test_builder_contract.py**: parametrized over all registered `BuilderSpec`s. Tests output_type correctness, parameter_schema validity, optional dependency handling.
- **test_io_format_contract.py**: parametrized over all registered `FormatHandler`s. Tests detect by extension, read/write round-trip, malformed input raises `FormatError`, `strict=False` tolerant mode.
- **test_storage_backend_contract.py**: parametrized over MemoryBackend, MaggmaBackend. Tests all 7 protocol methods, ID stability, envelope round-trip, query pagination.

### Deduplication

- Redundant "returns new object" tests merged into `test_structure_model_contract.py`
- Duplicate immutability tests across test_crystal, test_molecule, test_structure → contract
- Tests asserting implementation details (internal cache structure, private method signatures) → removed
- Tests for removed APIs (from_file, to_file) → removed

### Kept

- Focused regression tests for historical bugs
- Edge-case tests for specific operations
- Format-specific parsing edge cases
- Domain-specific construction tests (geometry, symmetry, composition)

### Integration Tests (`tests/integration/test_workflows.py`)

```python
def test_builder_to_transform_to_io_to_storage():
    """End-to-end: build → transform → IO round-trip → storage round-trip."""
    crystal = from_prototype('fcc', 'Cu', 3.61)
    strained = apply_strain(crystal, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
    vac = create_vacancy(strained, 0)
    write(vac, '/tmp/test.cif')
    reloaded = read('/tmp/test.cif')
    storage = DataStorage(backend=MemoryBackend())
    doc_id = storage.store_data(reloaded)
    retrieved = storage.retrieve_data(doc_id)
    assert retrieved == reloaded

def test_pipeline_with_registry():
    """Pipeline executes registered transforms end-to-end."""
    plan = TransformationPlan(steps=[
        TransformationStep("make_supercell", {"scaling_matrix": [2, 2, 2]}),
        TransformationStep("create_vacancy", {"indices": [0]}),
    ])
    result = registry.apply_plan(plan, crystal)
    assert result.num_atoms == crystal.num_atoms * 8 - 1
```

### Plugin Entry Point Registry Tests

- `test_transformation_registry_entry_points`
- `test_builder_registry_entry_points`
- `test_io_format_registry_entry_points`
- `test_storage_backend_registry_entry_points`

---

## 10. Implementation Phases

### Phase 1: Foundation (0–3 months)
1. Create `matsimpy/exceptions.py`
2. Create `matsimpy/core/protocols.py`
3. Remove `from_file`/`to_file` from Crystal/Molecule
4. Move graph + neighbors to analysis
5. Clean up core `__init__.py` exports
6. Create IO FormatHandler registry, refactor `io/core.py`
7. Split storage into schema/codec/backend/facade
8. Move converters → adapters, latex → export
9. Add contract tests

### Phase 2: Registries & Separation (3–6 months)
1. Create TransformationSpec + TransformationRegistry
2. Create TransformationPlan, refactor Pipeline/Batch/Sweep
3. Create BuilderRegistry
4. Move defects → transformation/atomic
5. Move alloy → transformation/chemical
6. Move adsorbate → transformation/atomic
7. Move interface → transformation/structural
8. Clean up wildcard exports
9. Add registry tests and spec tests

### Phase 3: Plugin Readiness (6–12 months)
1. Add entry point discovery for transformations, builders, IO formats, storage backends
2. Document plugin SDK
3. Add integration workflow tests
4. Finalize public API documentation

---

## Non-Goals (Explicitly Out of Scope)

- Changing calculator, symmetry, AI, UI, visualization, or config modules
- Adding new storage backends beyond Memory and Maggma
- Adding network/provenance graph support
- Changing the MSONable serialization contract
- Changing `Structure._construct` or the coordinate convention
