# Task 7 report: native symmetry services

## Outcome

Implemented and exported `SpacegroupAnalyzer`, `StructureMatcher`, and
`HighSymmKpath`.  spglib remains optional and all operations that require it
raise a targeted installation error.  The implementation supports Python 3.9
syntax and retains MatSimPy's row-vector lattice/fractional-coordinate
conventions.

## RED / GREEN record

- RED: `pytest tests/symmetry/test_vasp_services.py -v` failed during collection
  with `ImportError: cannot import name 'HighSymmKpath' from
  'matsimpy.symmetry'`. This was the expected missing-API failure.
- First GREEN attempt exposed a real backend compatibility issue:
  `spglib.get_ir_reciprocal_mesh()` does not accept `angle_tolerance`.
  Removing that unsupported keyword made the focused suite pass.
- Review added tests for targeted missing-spglib errors, mismatch decisions,
  deterministic labels, every required Bravais key, and optional pymatgen
  standardization/mesh parity.
- Final focused result: 20 passed.
- Final complete symmetry result: 43 passed.
- Optional parity selection: 1 passed, 19 deselected (pymatgen 2025.6.14 is
  installed in the development environment).
- `git diff --check` and `python -m compileall -q matsimpy/symmetry` passed.

## Implementation details

- Standardization converts `Crystal` to spglib's `(lattice, positions,
  atomic_numbers)` tuple and maps returned atomic numbers back through
  `Element.from_Z`, preventing a site-order change from corrupting species.
- Irreducible reciprocal meshes use stable sorted representative indices and
  exact mapping multiplicities; shifted meshes include the half-grid offset.
- Matching checks exact compositions, lattice length/angle tolerances, then
  tries translations from the least-common species. Each species block uses a
  minimum-image Cartesian cost matrix and SciPy's Hungarian assignment. The
  final threshold is normalized by `(volume / atom_count) ** (1/3)`.
- K-path generation classifies the spglib international setting into all 14
  requested Bravais keys, uses standardized conventional reciprocal lattices,
  and interpolates each independent segment deterministically. Segment
  endpoints carry labels and interiors carry empty strings.

## Attribution and clean-room decisions

No pymatgen source, implementation, or path tables were copied. Pymatgen
2025.6.14 was used only as a black-box oracle in a parity test. The fixed
metric-independent special-point coordinates are attributed in the module to
Setyawan and Curtarolo, *Computational Materials Science* 49, 299 (2010).
For centered/metric-dependent families, this implementation deliberately uses
deterministic conservative conventional-cell paths instead of reproducing an
unattributed third-party conditional table.

## Concerns / limitations

- Full coordinate-and-label parity with pymatgen for every metric-dependent
  Bravais variant is not claimed. The checked-in parity test covers cubic
  standardization and irreducible-mesh weights, while the complete Bravais
  parameterization verifies table integrity. In particular tI, oF/oI/oC, and
  mC currently use deterministic fallback paths rather than the full
  metric-dependent Setyawan-Curtarolo branches. This is scientifically usable
  as a stable sampling path but is the main follow-up if exact pymatgen k-path
  parity is mandatory.
- Site properties are not reconstructed by spglib standardization because
  spglib can change site multiplicity; chemical species are preserved, but a
  policy for propagating arbitrary per-site metadata would need a separate API
  decision.
