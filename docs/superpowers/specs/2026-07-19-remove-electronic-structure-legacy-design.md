# Remove Electronic-Structure Legacy Support

## Goal

Remove MatSimPy's compatibility path for decoding historical pymatgen MSON dictionaries. Keep the native electronic-structure result model required by the VASP readers, Monty serialization for native MatSimPy objects, and optional pymatgen parity tests.

This is an intentional public API break. MatSimPy will no longer advertise or provide `decode_legacy_pymatgen_dict`, and `matsimpy.electronic_structure.legacy` will no longer exist.

## Scope

The change will:

- delete `matsimpy/electronic_structure/legacy.py`;
- remove `decode_legacy_pymatgen_dict` from `matsimpy.electronic_structure` and its `__all__`;
- delete tests whose sole purpose is decoding pymatgen-authored MSON dictionaries;
- remove legacy-decoder documentation;
- add an architecture regression test that rejects restoration of the module or public symbol;
- retain native `Spin`, `Orbital`, `OrbitalType`, `Magmom`, `Dos`, `CompleteDos`, `BandStructure`, `BandStructureSymmLine`, `Kpoint`, `ComputedEntry`, and `ComputedStructureEntry` APIs used by MatSimPy;
- retain Monty as the native serialization framework; and
- retain pymatgen 2025.6.14 only as an optional development/test oracle.

This change will not add a migration package, deprecated forwarding stub, automatic pymatgen-object conversion, or runtime pymatgen dependency.

## Native Model Policy

The native classes are MatSimPy implementations, not vendored pymatgen implementations. Their behavior may be tested against pymatgen where VASP result parity is part of the existing contract, but their source will be independently designed around MatSimPy's data structures and parser needs.

During implementation, these classes may be optimized only when inspection or tests demonstrate a concrete issue such as incorrect validation, unnecessary copying, inefficient repeated lookup, inconsistent native serialization, or a missing operation required by the VASP readers. Any such change must have a focused regression test. Feature growth for the sake of matching pymatgen's broader API is out of scope.

No pymatgen code will be copied. If implementation reveals that copying is genuinely unavoidable, work must stop for explicit user approval and the copied portion must be clearly identified and attributed before it is introduced.

## Serialization Boundary

Monty round trips remain supported for dictionaries emitted by MatSimPy's native classes. Dictionaries identifying pymatgen modules or classes are no longer a supported input format. Removing the explicit decoder avoids preserving a second schema and prevents old pymatgen representations from defining the native model.

Existing generic Monty behavior outside `matsimpy.electronic_structure` is not changed by this project.

## Tests and Verification

Implementation will proceed test-first:

1. Add architecture assertions that `matsimpy.electronic_structure.legacy` is absent, `decode_legacy_pymatgen_dict` is not exported, and production electronic-structure modules do not import pymatgen.
2. Remove legacy-decoder fixtures and tests rather than converting them into a hidden compatibility path.
3. Run native electronic-structure tests, VASP output tests, architecture tests, and optional pymatgen parity tests in the conda `dev` environment.
4. Run the full feasible test suite to detect downstream consumers of the removed API.

Failures caused by callers importing the removed API are expected API-break evidence and will be resolved by removing internal usage, not by restoring compatibility. Unrelated failures or unrelated dirty working-tree changes will not be modified.

## Completion Criteria

The work is complete when the legacy module, public function, dedicated documentation, and dedicated tests are gone; native Monty round trips and VASP result tests pass; pymatgen remains absent from runtime dependencies and production imports; optional parity tests still compare native results with pymatgen; and no copied pymatgen implementation has been introduced.
