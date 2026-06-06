# Transformation Robustness Review

Date: 2026-06-06

The transformation tests currently pass, but the reviewed modules contain concrete robustness, metadata-preservation, and large-dataset performance issues that can break real transformation pipelines or silently drop data. These should be addressed before treating the transformation layer as production-ready.

## Findings

### P2: Preserve metadata during cell standardization

File: `matsimpy/transformation/lattice/transform.py:203`

`standardize_cell()` always constructs the returned `Crystal` with `site_properties=None`, so per-site data such as charges, magnetic moments, tags, or provenance are silently lost.

This is problematic because transformation pipelines otherwise try to preserve site metadata, so this creates an inconsistent data-integrity break. For example, standardizing a magnetic structure before a simulation drops every `magmom` label even when the atom count is unchanged.

Recommended fix: preserve properties when spglib returns an unchanged or reordered cell, or use an explicit atom-mapping strategy/option before dropping metadata.

Severity: Medium.

### P2: Stream parameter sweeps instead of materializing all cases

File: `matsimpy/transformation/composite/sweep.py:112`

The sweep constructor precomputes all combinations into `self._combinations`, so Cartesian sweeps allocate the full product before the caller can iterate.

This is problematic because large datasets can exhaust memory or hang during object construction. For example, six parameters with 100 values each attempts to build 10^12 combination dictionaries before yielding the first structure.

Recommended fix: store a lazy iterator/generator or a lightweight combination descriptor, and make `len()` optional/capped when the product is too large.

Severity: High for large sweeps.

### P2: Keep parallel `process_stream` from loading all inputs

File: `matsimpy/transformation/composite/batch.py:304`

The parallel `process_stream()` path converts the entire input iterable to a list before processing.

This is problematic because it contradicts the lazy API and can load all structures into memory at once. For example, streaming millions of generated structures through a processor with `n_workers > 1` materializes every structure before yielding any result.

Recommended fix: feed `enumerate(structures)` directly to pool `imap`/`imap_unordered` with chunking, or document and enforce that parallel mode is not streaming.

Severity: Medium.

### P2: Avoid rerunning failed parallel batches in raise mode

File: `matsimpy/transformation/composite/batch.py:265`

`_process_parallel()` catches all exceptions, including the intentional `RuntimeError` raised for a failed transformation when `error_handling='raise'`, then falls back to sequential processing.

This is problematic because failed batches can be processed twice, duplicating expensive or side-effectful user transformations before the same error is raised again. For example, a transformation writes output files and one item fails in parallel; the fallback reruns earlier items and overwrites or duplicates outputs.

Recommended fix: only fall back for pool setup/pickling infrastructure failures, and propagate transformation failures immediately in raise mode.

Severity: Medium.

### P2: Validate lattice scale inputs explicitly

File: `matsimpy/transformation/lattice/scale.py:37`

Non-scalar scale factors are passed directly to `np.diag()` without checking shape, finiteness, or positivity.

This is problematic because malformed inputs produce low-level shape/lattice errors, while negative or non-finite factors can create invalid transformations before the error is understandable. For example, `scale_lattice(crystal, [1, 1])` fails in matrix multiplication, and `set_volume(crystal, -100)` reaches scaling through an invalid target.

Recommended fix: require a finite positive scalar or exactly three finite positive factors, and validate `target_volume`/`target_density` before deriving the scale factor.

Severity: Medium.

### P3: Reject empty molecule alignment selections early

File: `matsimpy/transformation/structural/molecular.py:114`

`align_molecules()` only checks that the two selection lengths match, so empty selections pass validation and later produce NaN centers and a generic `Positions cannot contain NaN` failure.

This is problematic because pipelines receive an unclear downstream constructor error instead of a precise input-validation error. For example, a dynamic atom selector returns no matches for both molecules, and alignment emits NumPy warnings before failing.

Recommended fix: require at least one aligned atom pair, validate indices before slicing, and require enough non-degenerate points for any rotation-specific alignment mode.

Severity: Low.
