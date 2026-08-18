# VASP Ownership and Native Reuse Cleanup Design

## Context

The VASP package is independent of pymatgen at runtime, but the initial native
cutover retained several copied or locally reconstructed abstractions. Some of
those abstractions are in the wrong layer, duplicate existing MatSimPy APIs, or
do not implement the behavior their callers expect.

Confirmed examples include:

- `matsimpy.calculator.vasp.inputs.Magmom` duplicates
  `matsimpy.electronic_structure.Magmom`.
- `get_el_sp` is local to `vasp.inputs`, while element normalization is a core
  domain concern; most VASP callers bypass it and construct `Element` directly.
- `calculator.utils.str_delimited` produces malformed INCAR rows.
- `outputs.micro_pyawk` accepts a mapping even though its callers provide a
  sequence of `(regex, predicate, action)` records.
- `calculator.utils.clean_lines` does not remove inline comments.
- `inputs.py` and `sets.py` each contain a broad `_safe_loadfn` that converts
  every loading failure into an empty dictionary.
- POTCAR parsing defines an `Orbital` tuple whose name conflicts with the
  electronic-structure orbital enum.
- `Element("H") in structure.species` compares an object with strings and does
  not detect hydrogen.

The relevant pre-change test selection passes (`107 passed`), demonstrating
that current tests do not constrain these behaviors precisely enough.

## Goals

1. Put domain types and generic utilities in their proper MatSimPy modules.
2. Make VASP code reuse native element, magnetic-moment, parsing, and formatting
   APIs instead of maintaining local substitutes.
3. Repair confirmed functional defects exposed by the ownership audit.
4. Replace masking resource fallbacks with explicit, contextual failures.
5. Preserve scientifically intentional VASP parsing behavior while removing
   migration-only names and aliases where they provide no domain value.
6. Keep production VASP code free of pymatgen imports and runtime dependencies.

## Non-Goals

- Reimplementing all pymatgen VASP functionality.
- Expanding native high-symmetry k-path support beyond its current documented
  scientific scope.
- Redesigning VASP input-set parameter policies.
- Refactoring unrelated calculator, core, or IO modules.
- Preserving compatibility with the temporary local VASP helper types and
  pymatgen-shaped names introduced during the initial cutover.

## Design

### 1. Core element normalization

Add public `get_el_sp(value) -> Element` to
`matsimpy.core.periodic_table` and export it from `matsimpy.core`.

The function will:

- return an existing `Element` unchanged;
- resolve non-boolean integral atomic numbers through `Element.from_Z()`;
- resolve strings through cached `Element.get_element()`;
- reject unsupported values with the native `TypeError`/`ValueError` evidence
  intact.

VASP modules will use this function whenever they need an `Element` object.
Callers that only need a normalized symbol may continue using core structure
normalization rather than converting to an `Element` and back.

The local `vasp.inputs.get_el_sp` and `_is_valid_symbol` implementations will
be removed. Validation loops will eagerly call the core helper; no lazy `map`
will be used for validation side effects.

### 2. Canonical magnetic moment model

`matsimpy.electronic_structure.Magmom` becomes the only magnetic-moment value
object used by VASP inputs and outputs.

It will provide the small protocol VASP needs:

- scalar or one-/three-component construction;
- immutable float components;
- sequence access and iteration;
- scalar conversion only for one-component moments;
- stable equality and representation;
- explicit MSON serialization and deserialization.

`vasp.inputs.Incar` will import this native type. The local VASP `Magmom` class
will be deleted. Scalar and non-collinear MAGMOM formatting will be tested as
observable INCAR text, not merely by checking that a name appears.

### 3. VASP-specific record naming

The POTCAR atomic-configuration tuples are VASP records, not general
electronic-structure orbitals. Rename them to:

- `PotcarOrbital`
- `PotcarOrbitalDescription`

They remain in `vasp.inputs` near `PotcarSingle`, because their fields and
parsing rules are specific to POTCAR metadata. Internal type checks and parsed
keyword construction will use the new names.

Rename `PmgVaspPspDirError` to `VaspPspDirError`. Provenance-bearing data-file
names may retain their historical filenames, but runtime API names and error
messages will describe MatSimPy/VASP rather than pymatgen configuration.

### 4. Shared calculator parsing utilities

`matsimpy.calculator.utils` will own generic calculator text helpers:

- `clean_lines` will strip comments, support optional empty-line retention,
  and support right-strip-only mode.
- `str_delimited` will format a two-dimensional sequence by joining row
  elements with the requested delimiter and optional header.
- `micro_pyawk` will compile search expressions and execute the documented
  `(regex, predicate, action)` program against each line.

`vasp.outputs` will import `micro_pyawk` instead of defining a local version.
Debug callbacks, if retained, will be ordinary callables; interactive
`pdb.set_trace()` side effects will not be embedded in production parsing.

These helpers will receive direct unit tests. VASP integration tests will also
assert exact INCAR output and at least one OUTCAR-style scanning callback so a
future signature mismatch cannot pass unnoticed.

### 5. Strict VASP resource loading

Create one private VASP resource loader in a focused module such as
`matsimpy.calculator.vasp._resources`.

The loader will:

- resolve package-owned paths explicitly;
- call `monty.serialization.loadfn` once;
- return the parsed mapping for valid resources;
- raise `FormatError` with the resource path and original exception chained
  when a required file is missing or malformed;
- allow an explicit optional/default mode only at call sites where absence is
  a documented input state, not as a broad catch-all.

Both duplicated `_safe_loadfn` implementations will be removed. Required YAML
input-set configurations and packaged POTCAR metadata will fail at their source
instead of becoming unexplained empty dictionaries.

### 6. VASP call-site cleanup

Within the files touched by the migrations:

- replace repeated `Element(...)` construction with `get_el_sp` when an element
  object is required;
- compare normalized symbols with `structure.species` rather than comparing
  `Element` instances with strings;
- remove `Structure = Crystal` compatibility aliases and use `Crystal` in type
  annotations;
- remove migration-only comments and generated strings that claim MatSimPy
  output was generated by pymatgen;
- remove pure deprecated forwarding wrappers in the touched surface when they
  have no independent behavior and no internal consumers;
- preserve attribution comments and historical hash provenance where they are
  factually required.

Broad permissive parsing branches will not be changed merely because they use
exceptions. Each such branch requires a behavior-specific regression before a
change. The cleanup will immediately address only confirmed masking behavior:
required resource loading and write/archive failures that currently disappear
without evidence.

## Error Handling

- Invalid element inputs propagate native `TypeError` or `ValueError`.
- Invalid Magmom shapes fail at construction with a precise `ValueError`.
- Required packaged-resource failures raise `FormatError` with exception
  chaining.
- VASP parse failures use `VaspParseError` or a contextual native exception;
  they do not silently fabricate data.
- Optional progress reporting remains optional and must not affect parsing.

## Testing Strategy

Every behavior change follows red-green-refactor using the `pmg` conda
environment.

Required regression coverage:

1. `get_el_sp` handles `Element`, string, and atomic-number inputs and rejects
   booleans/unsupported objects.
2. VASP modules import the canonical core/electronic types rather than defining
   duplicates.
3. Native `Magmom` sequence, scalar, equality, representation, and MSON
   round-trip behavior.
4. Exact scalar and non-collinear INCAR text.
5. `clean_lines` comment stripping and whitespace modes.
6. `str_delimited` exact two-dimensional formatting.
7. `micro_pyawk` predicate/action execution against a temporary file.
8. POTCAR-specific orbital record names and parsed values.
9. Hydrogen-containing MD structures receive the intended time step.
10. Missing and malformed required resources fail with contextual `FormatError`.
11. Recursive AST verification confirms no production VASP pymatgen imports.

Verification order:

1. focused tests for each migrated unit;
2. all VASP calculator tests plus core/electronic-structure tests touched by the
   migration;
3. compileall and scoped static checks;
4. the full repository test suite in `pmg`.

Pymatgen may appear only in optional reference-validation tests, never in
production implementation.

## Change Safety

The current uncommitted edit in `matsimpy/calculator/vasp/inputs.py` removes a
duplicate `from __future__ import annotations`. It is user-owned and will be
preserved during implementation.

No dependency additions are required. Changes will be split by responsibility
and kept reviewable. Scientifically unsupported paths will continue to fail
explicitly rather than receiving speculative implementations.

