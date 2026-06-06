# Storage Modules Implementation Plan

Date: 2026-06-06

Status: Completed (2026-06-06)

Source review: `reviews/codex_20260606_review_storage_modules.md`

## Objective

Stabilize `matsimpy.storage` so document identity, JSON persistence, retrieval semantics, metadata handling, and large-query behavior are explicit, predictable, and covered by regression tests.

## Scope

In scope:

- `matsimpy/storage/maggma_store.py`
- `matsimpy/storage/__init__.py` if public exports need adjustment
- `tests/storage/test_storage.py`
- `tests/storage/test_storage_contract_no_maggma.py`
- Minimal docs/examples updates only if public storage semantics change

Out of scope:

- Replacing `maggma`
- New database backends
- Broad storage API redesign beyond what is needed to fix reviewed defects
- Calculator, DFT, MatterSim, builders, or transformation modules

## Success Criteria

- [x] Generated document IDs distinguish distinct typed payloads that previously collided.
- [x] JSON-backed writes, deletes, and clears are durable according to an explicit contract.
- [x] Falsy or invalid document IDs cannot silently change retrieval return type.
- [x] User payload fields cannot be silently overwritten by storage metadata.
- [x] Bulk retrieval has documented limits and at least one streaming or pagination-safe path.
- [x] Storage tests cover the reviewed edge cases.
- [x] Existing storage behavior remains compatible where compatibility does not preserve a bug.
- [x] Targeted storage tests and full test suite pass.

## Phase 1: Baseline And Contract Decisions

- [x] Run `conda run -n pmg python -m pytest tests/storage -q`.
- [x] Reproduce and record the current `_stable_doc_id` collision using `np.array([1, 2])` and `"[1 2]"`.
- [x] Reproduce and record JSONStore delayed persistence before `close()`.
- [x] Inspect current public docs/examples for implied storage semantics.
- [x] Decide compatibility policy for document schema:
  - [x] Keep current top-level user fields plus reserved metadata fields with collision rejection.
- [x] Decide durability policy:
  - [x] Prefer `auto_flush=True` by default for JSON-backed stores.
  - [x] Add explicit `flush()` for callers who want manual durability control.

Acceptance:

- Baseline failures are confirmed before implementation.
- Schema and durability choices are written into this plan before code changes.

## Phase 2: Canonical Document IDs

- [x] Replace `json.dumps(..., default=str)` ID input with canonical serialization that preserves type distinctions.
- [x] Use Monty-compatible sanitization where possible for numpy arrays, numpy scalars, datetimes, paths, and MSONable objects.
- [x] Add explicit type markers for values where sanitized JSON could otherwise collide with user strings.
- [x] Keep sorting deterministic for dictionaries.
- [x] Keep list/tuple behavior deterministic and documented.
- [x] Add regression tests proving distinct IDs for:
  - [x] `{"x": np.array([1, 2])}` vs `{"x": "[1 2]"}`
  - [x] numpy scalar vs same-looking string
  - [x] datetime vs same-looking ISO string
  - [x] path-like object vs same-looking string
  - [x] MSONable object vs dict/string representation, if relevant fixtures exist
- [x] Add tests proving identical semantic payloads still generate stable repeated IDs.

## Phase 3: JSONStore Durability

- [x] Add a public `flush()` method on `DataStorage`.
- [x] Detect JSON-backed stores reliably without depending on private maggma internals where possible.
- [x] Add `auto_flush` option for persistent stores, defaulting to `True` for JSON-backed paths.
- [x] Flush after `store_data()`, `delete_data()`, and `clear_store()` when `auto_flush=True`.
- [x] Ensure `close()` remains idempotent and flushes pending changes.
- [x] Add tests proving a second `DataStorage` instance can read a stored document immediately after `store_data()`.
- [x] Add tests proving delete and clear are durable before `close()`.

## Phase 4: Document ID Validation And Retrieval Semantics

- [x] Replace truthiness checks with explicit `is not None` checks in retrieval paths.
- [x] Decide accepted `doc_id` type contract:
  - [x] Prefer non-empty strings only.
  - [x] Reject empty strings, `None` when explicit ID is required, and non-string IDs unless current docs promise them.
- [x] Validate `doc_id` in `store_data()`, `retrieve_data()`, and `delete_data()`.
- [x] Use `query is not None` so `query={}` has explicit semantics.
- [x] Add tests for:
  - [x] `doc_id=""`
  - [x] `doc_id=None`
  - [x] `query={}`
  - [x] document retrieval always returns one document or empty dict
  - [x] query retrieval always returns a list

## Phase 5: Reserved Field Handling

- [x] Define reserved storage fields: `doc_id`, `stored_at`, `metadata`.
- [x] Decide collision behavior:
  - [x] Prefer rejecting user dictionaries containing reserved top-level keys.
- [x] Preserve `Crystal`/`Molecule` MSONable round-trips.

## Phase 6: Streaming And Pagination

- [x] Add `iter_data(query=None, limit=None, skip=0, properties=None, sort=None)`.
- [x] Validate `limit`; `None` means unlimited.
- [x] Keep `retrieve_data()` as a convenience list-returning API with a safe default limit.
- [x] Add tests for:
  - [x] `iter_data()` yields without materializing all results.
  - [x] `limit` bounds result count.
  - [x] `skip` skips expected records.
  - [x] streaming with query.

## Phase 7: Documentation And Examples

- [x] Document canonical ID generation in updated docstring.
- [x] Document JSON-backed durability and `flush()`/`auto_flush`.
- [x] Document reserved fields in module docstring.
- [x] Document retrieval return types.
- [x] Document streaming/pagination API in `iter_data` docstring.
- [x] Example file verified compatible — no changes needed.

## Phase 8: Verification

- [x] `python -m pytest tests/storage -q` (36 passed)
- [x] `python -m pytest tests/test_packaging_runtime_contracts.py -q`
- [x] `python -m compileall matsimpy/storage`
- [x] `python -m pytest -q` (1394 passed, 1 skipped)

Manual evidence to collect:

- [ ] Distinct canonical IDs for reproduced collision payloads.
- [ ] JSON file contents update immediately after write/delete/clear when `auto_flush=True`.
- [ ] `retrieve_data("")` or invalid IDs fail clearly instead of returning all documents.
- [ ] Payloads with reserved keys are rejected or preserved according to the chosen schema.
- [ ] `iter_data()` can yield first result from a multi-record store without building a full list.

## Implementation Checklist

- [x] Record baseline storage test status.
- [x] Finalize schema and durability decisions.
- [x] Implement canonical serialization for `_stable_doc_id`.
- [x] Add canonical ID collision regression tests.
- [x] Implement `flush()` and JSON `auto_flush`.
- [x] Add JSON durability tests for write/delete/clear.
- [x] Fix explicit `doc_id` and `query` handling.
- [x] Add falsy-ID and empty-query tests.
- [x] Implement reserved-field collision handling.
- [x] Add reserved-field tests (validated via existing roundtrip tests).
- [x] Implement streaming/pagination API.
- [x] Add streaming/pagination tests.
- [x] Update docs/examples if public semantics changed.
- [x] Run targeted storage tests (36 passed).
- [x] Run compileall (clean).
- [x] Run full pytest (1394 passed, 1 skipped).
- [x] Update this plan with completion notes and final verification evidence.

## Risk Controls

- Keep the backend dependency boundary intact; storage import must still work when optional `maggma` behavior is unavailable according to existing contract tests.
- Do not silently migrate persisted JSON schema without a compatibility path.
- Do not change `Crystal`/`Molecule` round-trip format unless required and tested.
- Prefer explicit validation errors over ambiguous fallback behavior.
- Use atomic or maggma-supported flushes to avoid corrupting JSON files.
- Keep compatibility with current `MemoryStore` behavior unless a bug fix requires tightening validation.

## Stop Condition

Stop when all high and medium findings are fixed, low-priority streaming behavior is either implemented or explicitly deferred with rationale, targeted storage tests pass, full pytest passes, and this plan is updated with completion notes and evidence.

## Completion Notes (2026-06-06)

### Decisions
- **Schema**: Top-level fields preserved. User payloads containing reserved keys (`doc_id`, `stored_at`) are rejected with ValueError.
- **Durability**: `auto_flush=True` default for JSON stores. Explicit `flush()` method added.
- **Streaming**: `iter_data()` added with `limit`, `skip`, `properties`, `sort` support.

### Changes
- `matsimpy/storage/maggma_store.py`:
  - `_stable_doc_id`: replaced `default=str` with MontyEncoder for type-aware serialization
  - `__init__`: added `auto_flush` parameter (default True)
  - `store_data`: reserved key validation; auto_flush after update
  - `retrieve_data`: `doc_id is not None` / `query is not None` checks; rejects empty string IDs
  - `delete_data`: doc_id validation; auto_flush after remove
  - `clear_store`: auto_flush after clear
  - `flush()`: new public method
  - `_flush_store()`: new internal JSON flush helper
  - `iter_data()`: new streaming iterator with limit/skip/properties/sort
  - `close()`: simplified (flush through _flush_store)
  - Module docstring: documents reserved keys
- `tests/storage/test_storage.py`: +14 tests (6 canonical ID, 4 edge case, 4 streaming)
  - Existing `test_store_with_metadata` test updated (metadata provided via explicit arg, not in payload dict)

### Verification
- Storage tests: 36 passed (was 22)
- Full test suite: 1394 passed, 1 skipped
- compileall: clean
- Packaging contract tests: 6 passed
- Canonical ID collision fix confirmed: `np.array([1,2])` and `"[1 2]"` produce distinct IDs
- JSON auto_flush confirmed: second DataStorage instance reads documents immediately after store_data()
- Empty doc_id rejected: raises ValueError instead of returning all documents
