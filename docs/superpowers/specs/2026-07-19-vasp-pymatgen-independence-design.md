# MatSimPy VASP Pymatgen Independence Design

**Date:** 2026-07-19

## Objective

Remove every runtime dependency on `pymatgen` from `matsimpy.calculator.vasp` while preserving its current public APIs and numerical behavior. General scientific objects needed by VASP will become reusable MatSimPy-native implementations. `pymatgen==2025.6.14` remains an optional development and test dependency used only as a behavioral parity oracle.

## Scope

The migration covers the direct and guarded pymatgen dependencies in:

- `matsimpy.calculator.vasp.inputs`
- `matsimpy.calculator.vasp.outputs`
- `matsimpy.calculator.vasp.sets`
- related public exports from `matsimpy.calculator.vasp`

The work includes the MatSimPy-native domain objects and symmetry adapters required by those modules. It does not attempt to reimplement unrelated pymatgen APIs.

Compatibility applies to the VASP-facing public surface present in MatSimPy: public class and method names, accepted arguments, important attributes, enum values, return shapes and ordering, numerical results, warnings and errors, and Monty serialization. New native objects use their real `matsimpy.*` module and class identities. Explicit compatibility decoders accept legacy pymatgen-shaped dictionaries where required by existing VASP workflows.

## Constraints

1. Production code in the VASP package must not import pymatgen, directly, conditionally, lazily, or through a runtime adapter.
2. Supported public APIs must return real native objects rather than `None`, dictionaries standing in for domain objects, or placeholder classes.
3. All serializable domain objects continue using Monty `MSONable` conventions and provide compatible `as_dict()` and `from_dict()` behavior.
4. Implementations will be original work based on file-format specifications, mathematical definitions, existing MatSimPy conventions, public documentation, and black-box comparisons.
5. Pymatgen source may be consulted as a reference but will not be copied by default. If a narrow adaptation is genuinely necessary, the affected file must state the source repository, pymatgen version, original file, adapted scope, copyright, and license.
6. `pymatgen==2025.6.14` is permitted only in tests marked as requiring pymatgen.

## Architecture

### Native electronic-structure layer

A focused `matsimpy.electronic_structure` package will own reusable electronic-structure concepts needed by VASP:

- `Spin`, `Orbital`, and `OrbitalType`
- `Magmom`
- `Dos` and `CompleteDos`
- `BandStructure` and `BandStructureSymmLine`
- reconstructed-band-structure support used by the VASP parser

These classes will preserve the constructor contracts, public attributes, dictionary key behavior, array orientation, and methods exercised by the VASP API and its tests. They will depend on NumPy and MatSimPy core types, not calculator modules.

### Entries and trajectories

MatSimPy-native `ComputedEntry`, `ComputedStructureEntry`, and `Trajectory` types will live in a reusable domain package selected during implementation planning based on current core dependency rules. They will support the VASP parser's constructors, properties, equality-relevant data, and Monty round trips without creating a reverse dependency from core to calculators.

### Symmetry services

The existing `matsimpy.symmetry` package will be extended with the narrow capabilities currently consumed by VASP input sets:

- space-group analysis and standardized structures
- structure matching used by previous-run compatibility checks
- high-symmetry k-path generation

`spglib` may remain an optional low-level numerical backend for operations that require crystallographic symmetry calculation. Its absence raises a targeted feature-level `ImportError`; it never causes a pymatgen fallback. Native interfaces accept and return MatSimPy `Crystal`, `Lattice`, site, and element types.

### IO support types

Reusable volumetric-data behavior and Wannier `Unk` writing will live in MatSimPy IO support modules. VASP-specific subclasses or format handling remain under `calculator.vasp` when the behavior is inseparable from VASP file semantics.

### VASP integration

The VASP modules will import the native layers unconditionally. Guarded `_HAS_PYMATGEN_*` branches, dummy base classes, and `None` aliases will be removed. Existing VASP public exports remain available from their current paths.

## Data Flow

VASP parsing follows one explicit direction:

```text
VASP file -> parser primitives and NumPy arrays -> MatSimPy domain objects -> Monty serialization
```

Structure data uses `Crystal`, `Lattice`, `Element`, and `Composition` as the canonical representations. Parsers must not build an intermediate pymatgen structure. Domain objects must not depend on VASP parsers, so they remain independently testable and reusable.

Input-set generation follows the reverse domain flow:

```text
MatSimPy Crystal -> native symmetry/domain services -> Incar/Kpoints/Poscar/Potcar -> VASP files
```

## Public Compatibility

Representative compatibility targets include:

- `Vasprun.complete_dos` and `complete_dos_normalized`
- `Vasprun.get_band_structure()`
- `Vasprun.get_computed_entry()`
- `Vasprun.get_trajectory()`
- spin- and orbital-keyed eigenvalue, projection, DOS, and OUTCAR data
- volumetric-data classes and arithmetic
- multi-branch band-structure reconstruction
- VASP input-set symmetry reduction, standardized cells, line-mode paths, and previous-run checks
- Monty serialization and deserialization of all newly native result types

For this project, preserving the public API means equivalence for the public VASP behavior implemented and exposed by MatSimPy. It does not mean implementing every method available on the corresponding full pymatgen classes. If an existing MatSimPy VASP path relies on a method, that method is in scope.

Numerical comparisons use explicit per-domain tolerances. Metadata keys, enum integer values, spin conventions, array dimensions, species/site ordering, labels, and serialization fields require exact agreement unless a documented MatSimPy convention intentionally differs.

## Error Handling

- Malformed VASP input continues to raise the existing parser errors, with a native `ParseError` base added where required.
- Optional dependencies such as `spglib` and `h5py` are checked only when the relevant feature is invoked, with installation guidance in the error.
- Unsupported compatibility behavior raises a specific `NotImplementedError`; it must not silently emit incomplete data.
- Existing strict/tolerant parsing switches and warning behavior remain intact.
- Importing any VASP module succeeds in an environment where pymatgen is absent.

## Validation Strategy

### Native tests

Native unit tests exercise constructors, enums, numerical methods, validation, serialization, and error cases without pymatgen installed or importable. Each new module has focused tests independent of VASP fixtures.

### Import-boundary tests

An architectural test rejects direct or guarded runtime pymatgen imports in the VASP package. A subprocess test blocks `pymatgen` imports, imports every VASP module, and parses representative files to catch indirect runtime dependencies and import-time placeholders.

### Optional parity tests

Tests marked `requires_pymatgen` compare native behavior with `pymatgen==2025.6.14`. Comparisons cover:

- INCAR, KPOINTS, POSCAR, and POTCAR-derived metadata
- vasprun.xml, OUTCAR, OSZICAR, PROCAR, volumetric, and trajectory parsing
- scalar values, NumPy arrays, structures, DOS, band structures, entries, and trajectories
- symmetry analysis, structure matching, standardized structures, and k-path results
- Monty round trips and stable field schemas

Pymatgen objects are converted into neutral comparison records before assertions where the class identities necessarily differ. Every generated golden fixture records the pymatgen version, source input, generation command or helper, and comparison tolerance.

### Regression tests

Existing calculator tests and the full test suite run after each migration slice. A slice is complete only when its native tests, optional parity tests when pymatgen is available, import-boundary tests, and affected regressions pass.

## Migration Sequence

Implementation planning will divide the work into independently verifiable slices:

1. Establish import-boundary and representative parity characterization tests.
2. Add native enums, magnetic moments, and parser errors.
3. Add DOS and band-structure domain objects.
4. Add entries and trajectory support.
5. Add volumetric and Wannier support.
6. Extend native symmetry and structure-matching services.
7. Replace VASP output dependencies and remove guarded fallbacks.
8. Replace VASP input-set dependencies and remove guarded fallbacks.
9. Run full parity, serialization, documentation, and regression validation.

The detailed implementation plan may reorder tightly coupled test-first steps, but it must retain a passing, pymatgen-free runtime boundary after each completed migration slice.

## Completion Criteria

The migration is complete when:

- no production module under `matsimpy.calculator.vasp` imports pymatgen;
- representative VASP workflows run with pymatgen unavailable;
- all existing VASP-facing public paths return functional native objects;
- native and import-boundary tests pass without pymatgen;
- optional parity tests pass against `pymatgen==2025.6.14` within documented tolerances;
- affected existing tests and the full feasible regression suite pass;
- Monty round trips preserve native object data and supported legacy dictionaries decode correctly; and
- any adapted third-party code is explicitly identified and licensed in both source and project documentation.
