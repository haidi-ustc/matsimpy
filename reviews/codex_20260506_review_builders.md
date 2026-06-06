# Deep Review: `matsimpy/builders`

Scope reviewed: `matsimpy/builders/{bulk,alloy,surface,defects,nanostructure,molecule}` plus the corresponding builder tests.

Validation evidence:
- Ran targeted builder suite: `pytest tests/test_builders_bulk.py tests/test_builders_surface.py tests/test_builders_alloy.py tests/test_builders_defects.py tests/test_builders_molecule.py tests/test_builders_nanostructure.py tests/test_builders_bulk_symmetry.py` -> `113 passed`.
- Ran targeted probes for Miller-index slab identity, adsorbate coordinate placement, unsupported intermetallic fallback, nanotube PBC, integer twist-angle handling, and multilayer coordinate drift.

## Severity Ranking

| Rank | Severity | Area | Issue |
| --- | --- | --- | --- |
| 1 | High | Surface | `generate_slab()` does not actually orient slabs by Miller index. |
| 2 | High | Nanostructure | `build_twisted_multilayer()` mixes fractional and Cartesian coordinates, producing invalid cells/positions. |
| 3 | High | Nanostructure | `build_nanotube()` drops out-of-plane 2D material geometry and deduplicates atoms that differ only in layer height. |
| 4 | High | Bulk symmetry | `from_space_group()` can silently return the asymmetric input instead of the requested space-group expansion. |
| 5 | Medium | Alloy | Unsupported intermetallic structure types silently return an unrelated one-atom FCC prototype. |
| 6 | Medium | Surface | `add_adsorbate()` interprets fractional `(x, y)` incorrectly for non-orthogonal slabs. |
| 7 | Medium | Nanostructure | Nanotube periodicity flags are wrong for tube geometry. |
| 8 | Medium | Molecule | Geometry builders lack input validation and leak low-level errors/NaNs. |
| 9 | Medium | Alloy | Random alloy generation mutates NumPy global RNG state and can over/under-fill requested composition by rounding. |
| 10 | Low | API/export | Public exports are inconsistent with implemented functions. |

## Correctness Issues

### High: `generate_slab()` ignores the requested Miller surface

Evidence: `matsimpy/builders/surface/slab.py:49-61` computes a normal and approximate `d_spacing`, but `matsimpy/builders/surface/slab.py:69-104` always repeats along the original third lattice vector. The in-code comment at `matsimpy/builders/surface/slab.py:69-73` says the Miller index only affects layer-count estimation.

Probe result: for diamond Si, `(1, 0, 0)` and `(1, 1, 1)` with fixed `layers=3` produced identical lattice vectors and fractional positions.

Risk: Users receive a slab labeled as `(111)` or `(110)` while the atomic geometry is still the original `c`-axis cut. Surface energies, adsorption sites, terminations, and downstream DFT inputs become scientifically wrong.

Fix: Either integrate a real slab algorithm that transforms the lattice to the Miller plane, or rename this function to a `c_axis_slab`/`repeat_with_vacuum` helper and reject non-`(0, 0, l)` indices until proper crystallographic slab generation exists.

### High: `build_twisted_multilayer()` corrupts coordinates

Evidence: `matsimpy/builders/nanostructure/twisted.py:311-337` calls `translate()`, which returns a `Crystal` with Cartesian displacement converted back to fractional coordinates, then stacks `result.positions` and `new_layer.positions` as if they are compatible physical coordinates. It also computes `max_z` from fractional values and uses that as an Angstrom lattice length at `matsimpy/builders/nanostructure/twisted.py:321-323`.

Probe result: a 3-layer test with `layer_spacing=3.0` produced fractional z values `[230., 230., 299., 299., 16., 16.]` and Cartesian z range `4944.0` to `92391.0` Angstrom.

Risk: Multilayer outputs can be unusable while still constructing successfully.

Fix: Perform all layer rotations/translations in Cartesian coordinates, concatenate Cartesian positions, compute the new lattice in Angstroms, then construct once with `coords_are_cartesian=True`.

### High: `build_nanotube()` loses layered 2D geometry

Evidence: `matsimpy/builders/nanostructure/nanotube.py:140-147` only uses fractional x/y and ignores `frac_pos[2]`. Deduplication at `matsimpy/builders/nanostructure/nanotube.py:153-157` keys only by `(u, v)`, so two atoms with the same in-plane position but different out-of-plane heights collapse into one atom. The docstring explicitly claims support for transition metal dichalcogenides at `matsimpy/builders/nanostructure/nanotube.py:4-7`.

Probe result: a Mo/S/S layer with the two S atoms at the same x/y and different z generated equal Mo and S counts (`6` and `6`), instead of preserving two S sublayers per Mo.

Risk: TMD, buckled, Janus, and multilayer sheets are flattened into a single-radius tube with missing atoms.

Fix: Treat the original sheet normal coordinate as radial offset from the tube surface and include species plus radial/layer coordinate in duplicate detection.

### High: `from_space_group()` does not enforce requested space groups

Evidence: `matsimpy/builders/bulk/symmetry.py:80-95` presents `from_space_group()` as a generator. When spglib cannot validate or when `use_symmetry_data=False`, fallback paths at `matsimpy/builders/bulk/symmetry.py:447-450` and `matsimpy/builders/bulk/symmetry.py:512-513` return `Crystal(species, positions, lattice)` unchanged.

Probe result: requesting SG 225 with `use_symmetry_data=False` returned only the two supplied input sites, not the full Fm-3m conventional expansion.

Risk: The function name and docs imply symmetry expansion, but callers can receive a non-expanded seed structure with no warning.

Fix: Split "validate existing structure" from "generate full orbit"; if operations are unavailable, raise `NotImplementedError`/`RuntimeError` rather than silently returning the input.

## Hidden Bugs

### Medium: Unsupported intermetallics silently produce unrelated structures

Evidence: `matsimpy/builders/alloy/ordered.py:45-91` accepts `composition` and `structure_type`, but only special-cases `L1_2` and `B2`. The fallback at `matsimpy/builders/alloy/ordered.py:89-91` returns `from_prototype("fcc", elements[0], lattice_constant)`.

Probe result: `generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)` returned a one-atom Fe FCC primitive cell.

Risk: Misspelled or unsupported structures fail open and can contaminate workflows with plausible-looking but wrong crystals.

Fix: Replace the fallback with an explicit `ValueError` listing supported structure types. Use `composition` to validate stoichiometry.

### Medium: `add_adsorbate()` misplaces fractional `(x, y)` on skewed slabs

Evidence: `matsimpy/builders/surface/adsorbate.py:46-54` converts `position[0]` and `position[1]` by multiplying independent lattice-vector norms. This ignores vector coupling in non-orthogonal cells; a fractional surface point should be `u*a + v*b`.

Probe result: on a skewed cell with `a=[2,0,0]`, `b=[1,2,0]`, requested `(0.5,0.5)` produced cartesian `[1.0, 1.118, 6.0]`; the expected xy point is `[1.5, 1.0]`.

Fix: Build the target cartesian position from the lattice basis: `position[0] * a_vec + position[1] * b_vec`, then add height along a chosen surface normal.

### Medium: Nanotubes are marked periodic in all directions

Evidence: `matsimpy/builders/nanostructure/nanotube.py:173-190` builds a tube in a vacuum box but constructs `Crystal(...)` without `pbc`, so the default `(True, True, True)` applies.

Probe result: `build_carbon_nanotube(5, 5).pbc == (True, True, True)`.

Risk: Neighbor finding, graph construction, and simulation input writers can connect images across x/y vacuum even when only the tube axis should be periodic.

Fix: Set `pbc=[False, False, True]` when `periodic=True`, and `[False, False, False]` otherwise.

### Medium: Molecule builders leak low-level exceptions

Evidence: `build_linear()` normalizes `axis` without checking zero norm at `matsimpy/builders/molecule/geometry.py:34-35`; `build_bent()` indexes `bond_lengths[1]` and `angles[0]` without validating lengths at `matsimpy/builders/molecule/geometry.py:77-84`.

Probe results: zero axis emitted a NumPy runtime warning and later raised `ValueError: Positions cannot contain NaN values`; missing bent bond length raised `IndexError`.

Fix: Validate vector dimensionality/nonzero norm, bond-length counts, angle counts, and positive lengths at the builder boundary.

### Medium: Random alloy generation has non-local randomness and composition rounding issues

Evidence: `matsimpy/builders/alloy/random.py:46-48` calls `np.random.seed(seed)`, mutating global RNG state. Counts are rounded independently at `matsimpy/builders/alloy/random.py:71-75`.

Risk: Calling this builder can change unrelated random workflows. Independent rounding can also yield a composition different from requested, especially for small cells and multi-component alloys.

Fix: Use `rng = np.random.default_rng(seed)` and a deterministic apportionment strategy that preserves total substitutions and reports/controls rounding policy.

## Design Flaws

### Medium: Coordinate-system contracts are implicit and inconsistent

Evidence: surface and nanostructure builders switch between fractional and Cartesian positions manually (`slab.py:91-102`, `adsorbate.py:46-57`, `twisted.py:81-168`, `twisted.py:311-337`). The most severe multilayer bug comes from this boundary.

Risk: Future builders will repeat the same class of error, especially for non-orthogonal lattices and slab/nanotube geometries.

Refactor suggestion: Add small internal helpers such as `as_cartesian(crystal)`, `fractional_surface_point(crystal, uv)`, and `crystal_from_cartesian(species, cart_positions, lattice, pbc)`. Require each builder to pick one working coordinate system and convert exactly once at the boundary.

### Medium: Builder APIs claim general crystallography but implement narrow approximations

Evidence: `generate_slab()` advertises arbitrary Miller surfaces; `build_nanotube()` advertises any 2D crystal; `build_magic_angle_twisted()` uses simplified formulas at `matsimpy/builders/nanostructure/twisted.py:209-229`; `from_space_group()` advertises space-group generation but may return seeds.

Risk: The API names are stronger than the implementations. This makes bugs hard to catch because tests can pass while users trust incorrect scientific semantics.

Refactor suggestion: Introduce capability levels: exact, approximate, and placeholder. Approximate builders should either expose that in their names or require `approximate=True`.

### Low: Tests primarily assert construction, not physical invariants

Evidence: the current targeted suite passes (`113 passed`), but probes still found identical `(100)`/`(111)` slabs, corrupted multilayer coordinates, and unsupported intermetallic fallbacks.

Refactor suggestion: Add invariant tests:
- Miller slabs with different indices must differ in lattice orientation and surface normal.
- Adsorbate fractional uv placement should work on skewed cells.
- Multilayer z spacing should match requested Angstrom spacing.
- Nanotube PBC should match the requested periodicity.
- Unsupported structure types must fail closed.

## Extensibility Risks

### Medium: Hard-coded structural templates will not scale cleanly

Evidence: `CRYSTAL_PROTOTYPES` in `matsimpy/builders/bulk/prototype.py:18-79`, intermetallic templates in `matsimpy/builders/alloy/ordered.py:74-91`, and Heusler coordinates in `matsimpy/builders/alloy/heusler.py:65-215` encode structure data directly in code.

Risk: Adding more prototypes will increase duplicated coordinate logic and inconsistent conventional-vs-primitive behavior.

Refactor suggestion: Move prototype definitions into validated data records with fields for cell convention, Wyckoff labels, stoichiometry, required lattice parameters, and aliases.

### Medium: Optional dependency behavior is uneven

Evidence: RDKit and PyXtal paths fail with clear import errors (`smiles.py:31-37`, `bulk/random.py:35-41`), while spglib-related generation can silently degrade (`symmetry.py:447-450`, `symmetry.py:512-513`).

Risk: Users cannot tell whether a builder used a rigorous backend or a fallback approximation.

Refactor suggestion: Use consistent backend contracts: `backend="auto|spglib|data"` plus `strict=True` default for scientific builders.

### Low: Public API omits implemented functionality

Evidence: `build_inverse_heusler_quaternary()` is in `matsimpy/builders/alloy/heusler.py:218-279` and in that module's `__all__`, but `matsimpy/builders/alloy/__init__.py:34-49` does not import/export it.

Risk: Users discover functions inconsistently depending on import path.

Fix: Export it from `matsimpy.builders.alloy` or mark it private.

## Recommended Refactor Path

1. Fail closed first:
   - Reject unsupported intermetallic structure types.
   - Reject arbitrary Miller indices until a real slab builder exists.
   - Raise when requested space-group expansion cannot be performed.

2. Add regression tests for the reproduced bugs:
   - `(100)` vs `(111)` slab geometry must not be identical.
   - `build_twisted_multilayer(..., layer_spacing=3.0)` must produce Angstrom-scale z separation.
   - TMD-like nanotube input must preserve both chalcogen sublayers.
   - `add_adsorbate()` must place uv coordinates correctly on skewed cells.
   - `generate_intermetallic(..., "L1_0")` must either build L1_0 or raise.

3. Normalize coordinate handling:
   - Use Cartesian-only internals for geometry-building algorithms.
   - Convert to fractional only once when constructing `Crystal`.
   - Set `pbc` explicitly in every non-bulk builder.

4. Separate placeholder helpers from scientific builders:
   - Rename or gate approximate implementations.
   - Add docstrings that state exact limitations.
   - Prefer integration with established libraries for slab generation and symmetry expansion when exact behavior is expected.

Overall recommendation: request changes before treating `matsimpy/builders` as scientifically reliable. The package can construct many objects successfully, but several builders return plausible-looking structures with incorrect geometry or hidden fallback behavior.
