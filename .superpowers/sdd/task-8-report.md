# Task 8 Report: Native VASP Input Sets

## Status

Implemented the pymatgen-independent VASP input-set stack using native matsimpy structures and the approved native symmetry services.

## RED evidence

Initial `pytest tests/calculator/test_vasp_sets_native.py -q` result: 6 failed, 1 passed.

- `sets.py` contained direct and guarded pymatgen imports.
- `DictSet.get_input_set()` called the missing pymatgen-style `Crystal.get_space_group_info()` path.
- standardization and line-mode k-points instantiated pymatgen symmetry classes with native crystals.
- NMR EFG generation assumed pymatgen `Species` objects.
- The NEB regression then failed on pymatgen-only `frac_coords` and translation APIs.
- The previous-run regression failed because native `Structure.copy()` does not accept pymatgen's `site_properties` keyword.
- The batch regression failed because native `Structure.copy()` does not accept pymatgen's `sanitize` keyword.
- The LLL compatibility regression failed because only Niggli reduction had initially been wired.

## GREEN implementation

- Replaced pymatgen `InputGenerator` with a native `MSONable` serialization base.
- Imported `SpacegroupAnalyzer`, `StructureMatcher`, and `HighSymmKpath` unconditionally from `matsimpy.symmetry`.
- Removed guarded, direct, and `TYPE_CHECKING` pymatgen imports and dummy aliases from `sets.py`.
- Replaced pymatgen site/species operations with narrow native crystal/site helpers.
- Added native NMR quadrupole lookup with explicit missing/ambiguous-isotope errors.
- Preserved stateless/stateful Monty round trips, user INCAR overrides, Niggli/LLL reduction options, previous-run properties, standardization, NEB crossing/path construction, and sanitized batch writing.
- Adapted reciprocal-density generation and irreducible meshes to the native lattice/symmetry APIs.
- Added a public native space-group-symbol service used for k-point centering.

## Verification

- `pytest tests/calculator/test_vasp_sets_native.py -m requires_pymatgen -q`: 5 passed (MITRelaxSet, MPRelaxSet, MPStaticSet, MPNonSCFSet, NEB parity).
- `pytest tests/calculator/test_vasp_sets_native.py tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py tests/symmetry tests/architecture/test_vasp_no_pymatgen.py -q`: 170 passed, 1 xfailed.
- Architecture AST inspection reports only `outputs.py:93`; `sets.py` has no pymatgen imports.
- `git diff --check`: clean.
- `ruff` was not available in the environment (`command not found`).

## Concerns

- The architecture test remains intentionally xfailed until Task 9 because `outputs.py` still imports pymatgen.
- Citation decorators formerly supplied by `pymatgen.util.due` were removed; class documentation retains the citations without requiring a replacement citation dependency.

## Review-fix RED evidence

Focused regression run initially reported 4 failures and 1 pass:

- native cubic and hexagonal `automatic_density_by_lengths()` both failed on the removed `Crystal.get_space_group_info()` API;
- `MPNMRSet` rejected B without an explicit isotope instead of selecting pinned pymatgen's first tabulated isotope;
- `standardize_structure(..., international_monoclinic=False)` returned normally while silently ignoring the requested convention;
- the pre-existing stateless Monty round trip passed.

## Review-fix GREEN evidence

- Replaced the remaining pymatgen-era length-density lattice/symmetry calls with native `Lattice` parameters and native `SpacegroupAnalyzer` symbol detection.
- Restored deterministic first-tabulated-isotope behavior for NMR EFG defaults while retaining explicit overrides and targeted missing-data errors.
- Made the unsupported Curtarolo monoclinic convention raise a targeted `NotImplementedError`; the international default remains unchanged.
- Added direct cubic/hexagonal grid/style tests, pinned optional parity, default/explicit B isotope parity, stateless/stateful Monty coverage, and a reciprocal-mesh reduction/weight assertion.
- `pytest tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_sets_native.py tests/symmetry tests/architecture/test_vasp_no_pymatgen.py -q`: 179 passed, 1 xfailed.
