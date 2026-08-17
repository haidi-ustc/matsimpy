# Native MatSimPy VASP Models Design

## Goal

Make every production module under `matsimpy/calculator/vasp` self-supported by
MatSimPy. Runtime and type-checking code in that package must not import
`pymatgen`. Pymatgen remains permitted only in validation tests as an optional
reference oracle.

All Python verification commands run through the `pmg` conda environment.

## Dependency Boundary

The enforceable boundary is imports, object construction, inheritance, and
runtime calls. No file under `matsimpy/calculator/vasp` may import or lazily load
`pymatgen`, including inside `TYPE_CHECKING` blocks. Validation tests may import
pymatgen when marked `requires_pymatgen` or guarded by `pytest.importorskip`.

Historical attribution, compatibility metadata, existing environment-variable
names, and hash-database filenames may retain the word `pymatgen` where changing
them would remove attribution or break data compatibility. These references do
not create a runtime dependency.

## Architecture

Use focused MatSimPy-native modules rather than VASP-local fallback stubs or a
broad reimplementation of pymatgen. Each module implements only the behavior
consumed by MatSimPy's VASP package and exposes ordinary MatSimPy objects.

The native model surface is:

- `matsimpy.electronic_structure.core`: spin, orbital, orbital-type, and magnetic
  moment value objects.
- `matsimpy.electronic_structure.dos`: total and site/projected density-of-states
  containers, including normalized DOS construction used by `Vasprun`.
- `matsimpy.electronic_structure.bandstructure`: regular and symmetry-line band
  structures plus branch reconstruction used by VASP output parsing.
- `matsimpy.core.entries`: computed energy entries with optional native
  `Crystal` structures.
- `matsimpy.core.trajectory`: ordered native-structure trajectories.
- `matsimpy.core.units`: lightweight unit metadata/decorator behavior required by
  current VASP properties.
- `matsimpy.io.common`: the volumetric-data base behavior consumed by CHGCAR,
  LOCPOT, and related VASP readers.
- `matsimpy.io.wannier90`: the `Unk` data/write behavior used by WAVEDER/Wannier
  output paths.
- `matsimpy.calculator.input_generator`: a native serializable input-generator
  base class.
- `matsimpy.symmetry`: native structure matching, space-group analysis, and
  high-symmetry k-path support built on MatSimPy structures and optional
  `spglib`.

Existing core concepts are reused instead of duplicated: `Crystal` replaces
Structure/IStructure/SiteCollection checks, `CrystalSite` replaces PeriodicSite,
and `Element` replaces Species where VASP needs element metadata.

## VASP Integration

`inputs.py` remains based on `Crystal`, `Lattice`, and `Element`; its type hints
must use MatSimPy-native types only.

`outputs.py` imports the native electronic-structure, entry, trajectory, units,
volumetric, parsing-error, and Wannier models unconditionally. The current
`try/except ImportError` pymatgen block and `None`/dummy fallbacks are removed.
Public methods such as `complete_dos`, `get_computed_entry`,
`get_band_structure`, and `get_trajectory` return native MatSimPy objects.

`sets.py` imports native input-generator and symmetry utilities. Site/species
branches are adapted to `Crystal`, `CrystalSite`, and `Element`. Citation-only
decorators become a small internal no-op or are removed when they do not affect
behavior.

`calculator.py` and the VASP package exports continue to expose the existing
public VASP API. Native replacement objects should preserve the attributes,
serialization shape, and operations that current VASP code actually uses so
that callers do not need a pymatgen installation.

## Graceful Capability Handling

Optional algorithms may depend on `spglib`, but never on pymatgen. When an
optional native backend is absent, the method that needs it raises a clear
`ImportError` naming the MatSimPy extra to install. Importing the VASP package,
parsing ordinary VASP files, and using unrelated features must continue to work.

If an advanced pymatgen API has no VASP consumer, it is out of scope. If a VASP
consumer needs behavior that cannot be implemented faithfully in the first
pass, the native method raises a specific `NotImplementedError` at that narrow
operation. It must not return `None`, construct a dummy class, or silently emit
incorrect scientific data.

## Validation Strategy

Development follows test-first migration, one native concept at a time:

1. Add a static contract test that rejects any `pymatgen` import in
   `matsimpy/calculator/vasp`.
2. Add focused tests for every new native value/container type and its VASP-used
   serialization or numerical behavior.
3. Add VASP integration tests proving native return types for computed entries,
   trajectories, DOS, band structures, volumetric data, input sets, and symmetry
   paths that are covered by fixtures.
4. Keep optional pymatgen comparisons in validation tests only. These compare
   scientific values and file semantics, not production object identity.
5. Run targeted tests, the VASP test suite, lint/static checks available in the
   repository, and then the full test suite with `conda run -n pmg`.

## Compatibility and Scope

The migration preserves existing VASP parsing and input-generation behavior.
It does not attempt to reproduce the entire pymatgen public API, remove the
optional pymatgen IO conversion feature elsewhere in MatSimPy, or rewrite
non-VASP calculators. Public VASP methods retain their names; returned advanced
objects become MatSimPy-native equivalents.

The work is complete when the VASP package contains no pymatgen imports, its
covered APIs return native objects without pymatgen being importable, optional
pymatgen validation comparisons pass in the `pmg` environment, and the full
test suite has no regression attributable to the migration.
