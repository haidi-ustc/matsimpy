# MatSimPy Core and IO API Cleanup Design

## Purpose

This design defines a staged cleanup for MatSimPy's core structure API, IO API, and AI skill surface. The goal is to make `matsimpy.io` the single public boundary for file IO, third-party object conversion, and presentation export, while fixing the core mutability and cache bugs identified during code review.

The user-approved direction is:

- Use a staged approach for bug fixes and API cleanup.
- Remove `matsimpy.adapters` and `matsimpy.export` from the public API immediately.
- Keep convenient structure methods such as `from_file`, `to_file`, `from_ase`, `to_ase`, `from_pymatgen`, and `to_pymatgen`.
- Include AI skills/runtime cleanup in the same work so removed public packages do not leave broken tool surfaces.

## Current Code Evidence

The existing high-level IO path is already present:

- `matsimpy/io/core.py` defines `read()` and `write()` as registry-backed entry points.
- `matsimpy/io/registry.py` defines `FormatRegistry`, handler lookup, extension detection, and Crystal/Molecule write compatibility checks.
- `matsimpy/io/__init__.py` exports file readers/writers, but not third-party object conversion or LaTeX table export.

The public API is currently split:

- `matsimpy/adapters/ase.py` and `matsimpy/adapters/pymatgen.py` provide object conversion.
- `matsimpy/export/latex.py` provides LaTeX table export.
- `matsimpy/core/crystal.py` and `matsimpy/core/molecule.py` import conversion helpers from `matsimpy.adapters`.
- `matsimpy/ai/skills/adapters.py` imports from `matsimpy.adapters`.
- `matsimpy/ai/skills/export.py` imports from `matsimpy.export`.
- `matsimpy/builders/bulk/random.py` imports `from_pymatgen` from `matsimpy.adapters`.
- Tests currently expect `adapters` and `export` AI skills in `tests/ai/test_skill_loader.py`.

Core bug risks to fix in the same change:

- `Crystal.sites` and `Molecule.sites` return cached site objects that can be externally mutated.
- `Structure.substitute`, `Crystal.substitute`, and `Molecule.substitute` accept negative indices through Python list semantics, unlike `remove_atom`.
- `SymmOp` exposes writable matrix views through `rotation_matrix` and `translation_vector`.
- `Molecule.get_center_of_mass` returns its cached list directly.
- Calculator offline `read_results()` does not clearly bind parsed results to a structure hash.
- `Element.get_element()` can raise unstable errors for non-string direct inputs.
- `Composition` only parses integer formula counts; decimal composition support or rejection should be explicit.
- `Lattice.from_parameters()` relies on downstream finite/volume validation for extreme angle combinations.
- Serialization needs regression coverage to keep `Crystal.as_dict()` using fractional coordinates rather than the base Cartesian `positions` view.

## Public API Design

### IO as the single public boundary

The new public IO API should be:

```python
from matsimpy.io import read, write
from matsimpy.io import read_file, write_file
from matsimpy.io import to_ase, from_ase
from matsimpy.io import to_pymatgen, from_pymatgen
from matsimpy.io import structures_to_latex_table, save_latex_table
```

`read_file` and `write_file` are aliases for `read` and `write`. They exist because structure instance methods naturally read as `from_file` and `to_file`, while module-level helpers often read better as `read_file` and `write_file`.

### Removed public API

These public surfaces should be removed immediately, without deprecation wrappers:

- `matsimpy.adapters`
- `matsimpy.export`
- `matsimpy.ai.skills.adapters`
- `matsimpy.ai.skills.export`

Any import or test that uses these surfaces should be migrated to `matsimpy.io`.

### Core convenience methods

Core structure classes should keep user-friendly conversion methods, but each method must be a thin wrapper around `matsimpy.io`.

Required methods:

```python
Structure.from_file(filename, format=None, **kwargs)
structure.to_file(filename, format=None, **kwargs)

Crystal.from_file(filename, format=None, **kwargs)
Molecule.from_file(filename, format=None, **kwargs)

Crystal.to_ase()
Crystal.from_ase(ase_atoms)
Crystal.to_pymatgen()
Crystal.from_pymatgen(pymatgen_structure)

Molecule.to_ase()
Molecule.from_ase(ase_atoms)
Molecule.to_pymatgen()
Molecule.from_pymatgen(pymatgen_molecule)
```

`Structure.from_file` may return either `Crystal` or `Molecule`.

`Crystal.from_file` must return `Crystal`; if the reader returns `Molecule`, it raises `TypeError` or the project-standard structure type exception.

`Molecule.from_file` must return `Molecule`; if the reader returns `Crystal`, it raises `TypeError` or the project-standard structure type exception.

`to_file` should delegate to `matsimpy.io.write_file` and let the registry enforce format support.

## Module Layout

### `matsimpy.io.ase`

Keep file-level ASE reader/writer names:

- `read_ASE`
- `write_ASE`

Move third-party object conversion here:

- `to_ase`
- `from_ase`

The implementation should avoid ambiguity in errors by distinguishing "ASE file format" operations from "ASE Atoms object" conversion.

### `matsimpy.io.pymatgen`

Create a dedicated module for pymatgen object conversion:

- `to_pymatgen`
- `from_pymatgen`

This keeps optional pymatgen imports lazy and isolated to IO.

### `matsimpy.io.latex`

Move LaTeX table helpers here:

- `crystals_to_latex_table`
- `molecules_to_latex_table`
- `structures_to_latex_table`
- `save_latex_table`

LaTeX is treated as output formatting under IO, not a separate top-level export subsystem.

### `matsimpy.io.__init__`

Expose all supported public IO functions through `__all__`, including:

- `read`, `write`, `read_file`, `write_file`
- format-specific readers and writers
- `to_ase`, `from_ase`, `to_pymatgen`, `from_pymatgen`
- LaTeX table helpers
- registry objects

## AI Skill Design

Replace two AI skills with one:

- Remove `matsimpy/ai/skills/adapters.py`
- Remove `matsimpy/ai/skills/export.py`
- Add `matsimpy/ai/skills/io.py`

The `io` skill should cover:

- reading structures from files
- writing structures to files
- converting current or provided structures to ASE/pymatgen summaries
- converting provided ASE/pymatgen objects back to MatSimPy structures
- generating and saving LaTeX tables

Suggested skill metadata:

```python
SKILL_NAME = "io"
SKILL_DESCRIPTION = "Read, write, convert, and export MatSimPy structures"
SKILL_KEYWORDS = [
    "io", "read", "write", "file", "save", "load",
    "ase", "pymatgen", "convert", "conversion",
    "latex", "table", "report",
]
```

Tests should no longer expect `adapters` or `export` skills. They should expect a single `io` skill containing the relevant function names.

## Core Bug Fix Design

### Sites immutability

`Crystal.sites` and `Molecule.sites` should not return mutable cached site objects that can diverge from parent structure arrays.

Preferred fix:

- Return a tuple of freshly constructed `Site` or `CrystalSite` snapshots.
- Keep any internal `_sites` cache private and unreachable by callers, or remove the cache if construction cost is acceptable.

This preserves existing read access while preventing callers from corrupting the apparent structure state.

### Substitute index validation

All substitute paths should reject negative and out-of-range integer indices before mutation logic runs.

The rule should match `remove_atom`:

- valid index: `0 <= index < len(self.species)`
- invalid index: raise `IndexError`

This applies to:

- scalar index
- list/tuple of indices
- indices extracted from `AtomSelection`
- dict-based species mapping when used with selected indices

### SymmOp matrix safety

`SymmOp` should behave as a value object.

Required behavior:

- Store the affine matrix as a non-writable numpy array, or never expose mutable internal storage.
- `rotation_matrix` and `translation_vector` should return copies or read-only views.
- External writes to returned arrays must not mutate the `SymmOp`.

### Center of mass cache safety

`Molecule.get_center_of_mass()` should not return the cached list directly. It should return a copy of cached data or use an immutable tuple internally.

### Calculator offline result cache

The expected offline workflow must be clarified and locked with tests:

```python
structure.calc = calc
calc.calculate(structure)  # run=False writes inputs
calc.read_results()
structure.get_potential_energy()
```

If `read_results()` parses results for the calculator's current structure, it should set or preserve `_last_structure_hash` consistently. If no structure is bound, later `Structure.get_*` calls should fail clearly or force calculation according to the calculator mode.

The recommended behavior is:

- `Calculator.calculate(structure)` always records the structure hash, even when `run=False`.
- `read_results()` preserves that hash after parsing.
- `Structure.get_*` recomputes only when the attached structure hash differs.

### Element input validation

`Element.get_element()` should validate direct API inputs before calling string methods. Non-string inputs such as `1` or `None` should raise a clear `TypeError` or project-standard validation error, not an incidental `AttributeError`.

This should not change normal species normalization behavior. The goal is to make the direct public `Element.get_element()` contract stable.

### Composition formula count policy

`Composition` currently parses integer formula counts. Decimal formulas such as `Fe0.5Ni0.5` should either be explicitly rejected with a clear error or deliberately supported through a separate design.

For this implementation plan, prefer explicit rejection and tests unless broader fractional composition support is separately approved. Supporting decimals would affect formula normalization, mass/fraction math, serialization expectations, and possibly dummy species behavior.

### Lattice parameter edge cases

`Lattice.from_parameters()` should have tests around near-degenerate angles and angle combinations that can push the computed third vector component toward non-finite values. The implementation may continue to reject these through existing finite/volume checks, but the error behavior should be stable and intentional.

### Serialization coordinate semantics

`Crystal.as_dict()` must continue serializing fractional coordinates, while `Structure.positions` for crystals remains the Cartesian view. Regression tests should lock subclass serializer dispatch so future base-class changes do not accidentally serialize Cartesian coordinates and deserialize them as fractional coordinates.

## Testing Plan

Add or update tests for:

- `matsimpy.io` exports `to_ase`, `from_ase`, `to_pymatgen`, `from_pymatgen`, LaTeX helpers, `read_file`, and `write_file`.
- `matsimpy.adapters` and `matsimpy.export` are no longer part of the public API.
- `Crystal.to_ase`, `Molecule.to_ase`, `Crystal.from_pymatgen`, and related core methods call the IO path and still work.
- `Structure.from_file`, `Crystal.from_file`, and `Molecule.from_file` enforce return type contracts.
- AI skill discovery includes `io` and no longer includes `adapters` or `export`.
- The `io` AI skill exposes read/write/convert/latex functions with compact structure reference schemas.
- `builders/bulk/random.py` imports pymatgen conversion from `matsimpy.io`.
- Mutating `crystal.sites[0]` or `molecule.sites[0]` does not change or desynchronize the parent structure.
- `substitute(-1, ...)` raises consistently for `Structure`, `Crystal`, and `Molecule`.
- `SymmOp.rotation_matrix` and `translation_vector` cannot mutate internal state.
- `Molecule.get_center_of_mass()` returns data that callers cannot use to mutate the cache.
- Calculator offline `read_results()` cache behavior is stable.
- `Element.get_element(1)` and `Element.get_element(None)` raise clear validation errors.
- Decimal formulas such as `Composition("Fe0.5Ni0.5")` have an explicit tested policy.
- `Lattice.from_parameters()` rejects near-degenerate or non-finite angle combinations predictably.
- Crystal serialization round-trips through `Crystal.as_dict()` using fractional coordinates, not the Cartesian `positions` view.

## Implementation Sequence

1. Add regression tests for the current bug risks and new API contracts.
2. Move adapter conversion implementations into `matsimpy.io`.
3. Move LaTeX export implementation into `matsimpy.io`.
4. Update `matsimpy.io.__init__` and `matsimpy.io.core` public exports.
5. Update core conversion methods and add `from_file` / `to_file`.
6. Replace AI `adapters` and `export` skills with one `io` skill.
7. Update internal imports and tests.
8. Remove old public packages.
9. Fix core mutability, index validation, SymmOp, center-of-mass, calculator cache behavior, Element validation, Composition formula policy, and lattice/serialization edge cases.
10. Run targeted tests, then the full suite.

## Non-Goals

- No broad rewrite of the IO registry.
- No new dependency.
- No compatibility wrappers for `matsimpy.adapters` or `matsimpy.export`.
- No change to file format syntax beyond routing through the unified API.
- No redesign of AI runtime beyond replacing the two removed skills with the unified `io` skill.

## Risks

- Immediate removal of `matsimpy.adapters` and `matsimpy.export` is a breaking API change.
- `matsimpy.io.ase` will contain both file format helpers and object conversion helpers, so docstrings and errors must be clear.
- Returning fresh `Site` objects may break code that relied on object identity across repeated `sites` calls.
- Calculator cache behavior may need careful fake-calculator tests because real calculator backends may not share identical run/read semantics.

## Success Criteria

- Users can perform file IO, ASE conversion, pymatgen conversion, and LaTeX table generation through `matsimpy.io`.
- Core `Structure`, `Crystal`, and `Molecule` expose the requested `from_*`, `to_*`, `from_file`, and `to_file` convenience methods.
- No code in `matsimpy` imports from `matsimpy.adapters` or `matsimpy.export`.
- AI skill discovery exposes `io`, not `adapters` or `export`.
- Regression tests lock the identified core bug fixes.
- Full test suite passes after implementation.
