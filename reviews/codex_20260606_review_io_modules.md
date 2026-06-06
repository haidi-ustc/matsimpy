# IO Modules Code Review — 2026-06-06

## Scope

Reviewed all modules under `matsimpy/io`:

- `__init__.py`, `core.py`, `utils.py`
- Format parsers/writers: `ase.py`, `cif.py`, `json.py`, `mol.py`, `pdb.py`, `vasp.py`, `xsf.py`, `xyz.py`
- Conversion/export utilities: `converters.py`, `latex.py`
- Related test coverage under `tests/io`

Focus areas: data mapping accuracy, null/empty input handling, type conversions, exception handling, large-dataset performance, consistency between transformation pipelines, and test coverage gaps.

## Validation Evidence

- Ran IO test suite: `pytest -q tests/io`
- Result: `146 passed in 2.10s`
- Ran focused repro snippets for untested malformed/round-trip scenarios:
  - `.ase` molecule written by high-level `write()` cannot be read by high-level `read()`.
  - ASE reader accepts a header count of 3 but returns a 2-atom crystal when one coordinate line is missing.
  - PDB `as_crystal=True` without `CRYST1` returns `Molecule` instead of failing.
  - MOL reader accepts a count of 2 but returns a 1-atom molecule when one atom line is malformed.

## Executive Summary

The IO package has broad format coverage and a passing dedicated test suite, but several parsers are too permissive in ways that can silently drop atoms or change requested structure type. The highest data-integrity risks are in CIF import semantics, partial malformed record handling in ASE/MOL/PDB, and inconsistent high-level read/write behavior for dual-format `.ase`. Test coverage is strong for happy paths and basic invalid files, but it does not sufficiently lock malformed partial inputs, common real-world CIF features, or high-level round-trip contracts for all supported formats.

---

## Findings

### 1. ASE molecule high-level write/read pipeline is inconsistent

- **Location:** `matsimpy/io/utils.py:17-18`, `matsimpy/io/core.py:214-220`, `matsimpy/io/ase.py:103-110`, `matsimpy/io/ase.py:154-156`
- **Severity:** HIGH
- **Issue:** The registry and compatibility checks classify `.ase` as dual-format, and `write_ASE()` writes `Molecule` objects as standard XYZ-style files without lattice metadata. However `read_ASE()` rejects files without lattice information.
- **Why problematic:** A structure accepted by the high-level writer cannot be read back through the high-level reader using the same extension. This violates the package’s transformation pipeline consistency and makes `.ase` unsafe for molecule persistence.
- **Example failure:** `write(Molecule(...), "mol.ase")` succeeds, but `read("mol.ase")` raises `ValueError: ASE file does not contain cell/lattice information`.
- **Recommended fix:** Either make `read_ASE()` return `Molecule` when no lattice is present, or stop advertising/allowing `.ase` as molecule-compatible in `utils.py`/`core.py`. Add a high-level molecule `.ase` round-trip test.

### 2. ASE reader silently truncates atom lists when coordinates are missing or malformed

- **Location:** `matsimpy/io/ase.py:87-101`
- **Severity:** HIGH
- **Issue:** `read_ASE()` loops only to `min(2 + n_atoms, len(lines))` and silently `continue`s malformed coordinate lines. It only checks that at least one species was parsed, not that parsed atom count equals the declared header count.
- **Why problematic:** Corrupt or incomplete extended XYZ/ASE files can be imported as valid but smaller structures, causing silent composition and geometry corruption.
- **Example failure:** A file declaring `3` atoms with lattice metadata but only two coordinate lines returns a 2-atom `Crystal` instead of raising.
- **Recommended fix:** Require `len(lines) >= 2 + n_atoms`, raise on every malformed coordinate line, reject `n_atoms <= 0`, and verify `len(species) == n_atoms` before constructing the `Crystal`. Add malformed/missing-coordinate tests.

### 3. MOL reader silently accepts fewer atoms than the counts line declares

- **Location:** `matsimpy/io/mol.py:85-128`
- **Severity:** HIGH
- **Issue:** `read_MOL()` skips atom lines shorter than 30 characters and returns a molecule as long as at least one atom was parsed. It does not verify that the number of parsed atoms equals `n_atoms` from the counts line.
- **Why problematic:** A malformed MOL file can silently lose atoms, changing formulas, masses, and coordinates without an exception.
- **Example failure:** A V2000 file with count line `2 0` and one valid atom line plus one short malformed line returns a 1-atom molecule.
- **Recommended fix:** Treat each declared atom line as required: raise on short/malformed lines and assert `len(species) == n_atoms`. Add a regression test for malformed declared atom blocks.

### 4. PDB crystal request silently degrades to Molecule when CRYST1 is absent

- **Location:** `matsimpy/io/pdb.py:40-55`, `matsimpy/io/pdb.py:87-96`
- **Severity:** MEDIUM
- **Issue:** `read_PDB(..., as_crystal=True)` returns `Molecule` if no valid `CRYST1` record is found, despite the docstring saying crystal mode requires `CRYST1`.
- **Why problematic:** Callers requesting a periodic structure can receive a non-periodic object and continue with the wrong type unless they explicitly check the return value.
- **Example failure:** A PDB with atom coordinates but no `CRYST1` returns `Molecule` even when `as_crystal=True`.
- **Recommended fix:** If `as_crystal=True` and no valid lattice was parsed, raise a descriptive `ValueError`. Add a test for crystal-mode PDB input without `CRYST1`.

### 5. PDB reader silently drops malformed ATOM/HETATM records

- **Location:** `matsimpy/io/pdb.py:61-82`
- **Severity:** HIGH
- **Issue:** Coordinate parsing failures in ATOM/HETATM records are swallowed with `continue`.
- **Why problematic:** Partially corrupt PDB files import as valid smaller molecules/crystals, creating silent atom loss and incorrect downstream chemistry.
- **Example failure:** A protein/ligand PDB with one truncated coordinate record and hundreds of valid records will load without the bad atom, changing atom count and possibly bonding assumptions.
- **Recommended fix:** Raise on malformed atom records by default, or provide an explicit `strict=False` mode that records skipped lines. Tests should cover one malformed atom among valid atoms.

### 6. PDB element inference loses two-letter elements when element columns are absent

- **Location:** `matsimpy/io/pdb.py:64-72`
- **Severity:** MEDIUM
- **Issue:** If columns 76-78 are absent, the fallback uses only `atom_name[0]`. This maps two-letter elements such as `CL`, `NA`, `FE`, or `MG` to `C`, `N`, `F`, or `M`/invalid symbols.
- **Why problematic:** Data mapping accuracy depends on correct element symbols; misclassification changes formulas, masses, and validation behavior.
- **Example failure:** A minimal PDB line with atom name `CL` and no element column is imported as carbon rather than chlorine.
- **Recommended fix:** Implement PDB-style element inference that strips digits/charge decorations and tries valid two-letter symbols before one-letter symbols. Add tests for two-letter elements with missing element columns.

### 7. CIF reader ignores occupancy and imports partial/disordered sites as full atoms

- **Location:** `matsimpy/io/cif.py:205-263`, `matsimpy/io/cif.py:314-323`
- **Severity:** HIGH
- **Issue:** `read_CIF()` parses species and coordinates but ignores `_atom_site_occupancy`; `write_CIF()` always writes occupancy `1.0`.
- **Why problematic:** CIFs frequently encode partial occupancy and disorder. Treating all sites as fully occupied corrupts composition, stoichiometry, and density-related calculations.
- **Example failure:** A CIF with a Na site at occupancy `0.5` is imported as a full Na atom and later written as occupancy `1.0`.
- **Recommended fix:** Parse occupancy into site properties, validate unsupported partial occupancy explicitly, or add a documented policy such as rejecting non-1.0 occupancy until the core model supports it. Add tests for partial and missing occupancy.

### 8. CIF reader does not expand symmetry operations from asymmetric units

- **Location:** `matsimpy/io/cif.py:94-180`, `matsimpy/io/cif.py:205-263`, `matsimpy/io/cif.py:303-305`
- **Severity:** HIGH
- **Issue:** The reader extracts only listed atom-site rows and ignores space group and symmetry operation loops. The writer also always emits P1, making the pipeline unable to preserve symmetry metadata.
- **Why problematic:** Many CIFs list only the asymmetric unit. Without applying symmetry operations, imported structures can contain too few atoms and wrong stoichiometry for the conventional/unit cell representation users expect.
- **Example failure:** A non-P1 CIF with one symmetry-unique atom that should generate multiple equivalent sites imports as a one-atom P1-like structure.
- **Recommended fix:** Either support symmetry expansion via a robust CIF backend/adapter or clearly reject non-P1 CIFs unless all equivalent sites are explicitly listed. Add tests with a known non-P1 CIF and expected expanded atom count.

### 9. CIF loop parsing is not quote-aware and can misalign columns

- **Location:** `matsimpy/io/cif.py:161-174`
- **Severity:** MEDIUM
- **Issue:** Loop data are flattened with `data_line.split()`, then sliced by column count. CIF values may be quoted strings containing whitespace or semicolon-delimited multiline values.
- **Why problematic:** Once one value tokenizes incorrectly, every following value in that loop can shift columns. This can corrupt atom species/coordinates or auxiliary metadata without an obvious parser error.
- **Example failure:** A loop row containing a quoted value like `'C atom'` before coordinate columns is split into two tokens, shifting subsequent numeric fields into the wrong headers.
- **Recommended fix:** Use a CIF-aware tokenizer/parser or at minimum `shlex`-style tokenization for quoted values plus validation that token count is an exact multiple of loop column count. Add tests for quoted loop values and malformed row widths.

### 10. VASP POSCAR negative scale factors are interpreted incorrectly

- **Location:** `matsimpy/io/vasp.py:46-66`
- **Severity:** MEDIUM
- **Issue:** The scale factor is always multiplied directly into the lattice vectors. In VASP POSCAR semantics, a negative scale factor denotes the target cell volume and requires rescaling vector lengths accordingly, not negating every vector.
- **Why problematic:** POSCAR files using negative volume scaling will import with an incorrectly scaled/inverted lattice.
- **Example failure:** A POSCAR with scale factor `-27.0` and unit lattice vectors should produce a 27 Å³ cell, but the current code applies `-27` to each vector.
- **Recommended fix:** Implement VASP scale handling: positive scalar multiplies vectors, negative scalar rescales vectors to the requested volume. Add tests for negative scale factor semantics.

### 11. XYZ multi-frame reader is much more permissive than single-frame XYZ

- **Location:** `matsimpy/io/xyz.py:149-183`
- **Severity:** MEDIUM
- **Issue:** `read_XYZ_multiframe()` scans forward past non-integer count lines, breaks silently on incomplete frames, does not reject non-positive atom counts, and may return only valid-looking frames from a corrupted file.
- **Why problematic:** Batch trajectory imports can silently lose frames, masking data corruption and creating length mismatches between coordinates and associated times/energies in downstream workflows.
- **Example failure:** A multi-frame XYZ with a corrupted middle frame may return the earlier frames without raising, leaving the caller unaware that the trajectory was truncated.
- **Recommended fix:** Mirror `read_XYZ()` strict validation by default, with an optional tolerant mode if desired. Validate positive atom counts, complete frame lengths, and coordinate parse errors. Add tests for incomplete and malformed middle frames.

### 12. LaTeX export does not escape user-provided text or formatter output

- **Location:** `matsimpy/io/latex.py:72-79`, `matsimpy/io/latex.py:96-97`, `matsimpy/io/latex.py:167-174`, `matsimpy/io/latex.py:191-192`, `matsimpy/io/latex.py:373-392`
- **Severity:** LOW
- **Issue:** Captions, labels, column names, and custom formatter outputs are interpolated directly into LaTeX.
- **Why problematic:** Values containing `&`, `%`, `_`, `#`, braces, or backslashes can produce invalid LaTeX or alter table structure.
- **Example failure:** A caption like `Energy & Formation` creates an unintended column separator and compilation error.
- **Recommended fix:** Escape normal text fields by default, document formatter responsibility for raw LaTeX, and add tests for special characters in captions/labels/custom cells.

### 13. Format normalization is duplicated between registry and high-level API

- **Location:** `matsimpy/io/utils.py:10-23`, `matsimpy/io/core.py:67-85`, `matsimpy/io/core.py:186-204`
- **Severity:** LOW
- **Issue:** Format aliases and compatibility live partly in `FORMAT_REGISTRY`, partly in `detect_format()`, and partly in duplicated `format_map` dictionaries in `read()` and `write()`.
- **Why problematic:** Adding or changing a format can easily update one path but not another, causing reader/writer drift and inconsistent explicit-vs-extension behavior.
- **Example failure:** A new extension added to `FORMAT_REGISTRY` might auto-detect correctly but fail when passed as `format="..."`, or vice versa.
- **Recommended fix:** Centralize aliases and compatibility metadata in one registry object and have `read()`/`write()` call shared normalization helpers. Add tests that every registered alias works for both explicit and extension-driven paths.

---

## Test Coverage Gaps

Current IO tests are useful for basic success/error behavior, but the following gaps should be closed:

1. High-level round-trip tests for every format advertised as readable and writable, including `.ase` molecule behavior and `.pdb` crystal behavior with explicit `as_crystal=True`.
2. Parser strictness tests where a declared atom count is larger than valid coordinate/atom records for ASE, MOL, PDB, XYZ multi-frame, and XSF.
3. CIF tests for common real-world features: partial occupancy, non-P1 symmetry/asymmetric units, quoted loop values, and malformed loop row widths.
4. VASP negative scale factor tests and legacy/variant POSCAR tests if those formats are intended to be supported.
5. PDB element inference tests for two-letter symbols without element columns.
6. LaTeX escaping tests for captions, labels, and custom formatter output.

## Architectural Concerns

- **Strict vs tolerant parsing is not defined.** Some readers raise on malformed records (`read_XYZ`, `read_XSF`), while others skip or truncate (`read_ASE`, `read_MOL`, `read_PDB`, `read_XYZ_multiframe`). A package-level policy would improve predictability.
- **Dual-format support is underspecified.** `.json` is truly dual-format, while `.ase` is currently writable for molecules but not readable for molecules. `.pdb` can represent both, but default read behavior depends on kwargs rather than saved object type.
- **CIF support is structurally limited.** The current implementation is suitable for simple P1/full-site CIFs but presents itself as CIF 1.1 support. Consider narrowing documentation or delegating to a specialized CIF parser for production-grade crystallographic imports.

## Recommended Prioritization

1. Fix silent data-loss paths first: ASE count validation, MOL count validation, PDB malformed atom handling.
2. Resolve `.ase` dual-format contract: either make molecule read/write round-trip or mark `.ase` as crystal-only.
3. Harden PDB crystal-mode behavior and two-letter element inference.
4. Decide CIF policy: support symmetry/occupancy or reject unsupported cases with explicit errors.
5. Consolidate format registry/alias metadata and add full advertised-format round-trip tests.
