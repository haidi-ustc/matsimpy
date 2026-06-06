# Storage Modules Review

Date: 2026-06-06
Scope reviewed:
- `matsimpy/storage/__init__.py`
- `matsimpy/storage/maggma_store.py`
- `tests/storage/test_storage.py`
- `tests/storage/test_storage_contract_no_maggma.py`
- `docs/user_guide/storage.rst`, `docs/api_reference/storage.rst`
- `examples/storage_basic.py`

Validation evidence:
- Ran `pytest -q tests/storage -q`: **22 passed**.
- Inspected live `maggma` signatures for `MemoryStore`, `JSONStore`, `query`, `count`, and `update_json_file`.
- Reproduced JSONStore deferred persistence: after `store_data()`, the JSON file remained `[]` and a second `DataStorage` instance could not retrieve the new document until the first instance was closed.
- Reproduced stable ID collision: `_stable_doc_id({'x': np.array([1, 2])}) == _stable_doc_id({'x': '[1 2]'})`.

## Executive Summary

The storage surface is small and the existing tests cover the basic memory/JSON store lifecycle, metadata queries, deletion, counting, and MSONable round-tripping. The main correctness risks are around data identity and persistence semantics rather than the basic CRUD paths. Generated document IDs are based on `json.dumps(..., default=str)`, which can map distinct typed payloads to the same hash. JSON-backed writes are not durable until `close()`, so successful `store_data()` calls can still be lost or invisible to other readers. Several API branches also rely on truthiness instead of explicit `None` checks, and storage-reserved fields can overwrite user payload fields without warning.

## Findings

### 1. Non-canonical type conversion can generate identical IDs for distinct data

- **Location:** `matsimpy/storage/maggma_store.py:339-347` (`_stable_doc_id`)
- **Severity:** **HIGH**
- **Issue description:** The generated `doc_id` hashes `json.dumps(stable_document, sort_keys=True, default=str)`. Values that are not directly JSON serializable are converted with `str()`, which can collide with real strings or with other objects that share the same string representation.
- **Why it is problematic:** `doc_id` is the primary key for both `MemoryStore` and `JSONStore`. If two distinct payloads produce the same hash, `store.update()` overwrites the previous document or de-duplicates it as if it were identical. This is a data integrity risk, especially because scientific payloads commonly contain numpy arrays, numpy scalars, paths, datetimes, and domain objects.
- **Example scenario where it could fail:** `{'x': np.array([1, 2])}` and `{'x': '[1 2]'}` both produce `c9dc5e230ae3aac9c4aa7c01d0053604` with the current `_stable_doc_id`. Storing both without explicit `doc_id`s causes the second write to replace or mask the first even though the persisted JSON values are semantically different (`[1, 2]` vs `"[1 2]"`).
- **Recommended fix:** Generate IDs from a canonical sanitized representation that preserves type distinctions. Prefer a Monty/maggma-compatible serialization pass (for example `monty.json.jsanitize` or `MontyEncoder` followed by canonical JSON) and include explicit type tags where needed. Add regression tests for numpy arrays vs strings, numpy scalars vs Python scalars if intentional, datetimes, and MSONable objects.

### 2. JSON-backed writes are acknowledged before they are durable

- **Location:** `matsimpy/storage/maggma_store.py:185-189`, `matsimpy/storage/maggma_store.py:297-305`
- **Severity:** **HIGH**
- **Issue description:** `store_data()` returns success after `self.store.update(data_dict)`, but for `JSONStore` the file is only flushed in `close()` via `update_json_file()`.
- **Why it is problematic:** A caller can receive a valid `doc_id` and believe data is persisted, while the on-disk JSON file still contains the old content. If the process crashes, is interrupted, forgets to close, or another process opens the same store before close, the data is lost or invisible. This violates the expectation of persistent storage.
- **Example scenario where it could fail:** With a JSON store, calling `store_data({'a': 1})` leaves the file as `[]`. A second `DataStorage(store_path=same_path)` cannot retrieve the returned `doc_id` until the first storage object is closed. If the process exits abnormally before `close()`, the successful write is never persisted.
- **Recommended fix:** Flush JSON stores after each write/delete/clear operation, or add an explicit `flush()` method plus an `auto_flush=True` default for JSONStore. At minimum, document the delayed durability contract prominently and add tests proving the intended behavior. Consider atomic write semantics to avoid partially written JSON files during flush.

### 3. Falsy document IDs change retrieval semantics and return type

- **Location:** `matsimpy/storage/maggma_store.py:220-241`
- **Severity:** **MEDIUM**
- **Issue description:** `retrieve_data()` checks `if doc_id:` and `elif query:` instead of checking `doc_id is not None` and `query is not None`.
- **Why it is problematic:** Empty-string document IDs are accepted by `store_data(doc_id='')` and can be deleted by `delete_data('')`, but `retrieve_data('')` does not retrieve that document. It falls through to the “return all documents” branch and returns a list, breaking the documented contract that `doc_id` retrieval returns a single dictionary. Empty query dictionaries are likewise indistinguishable from no query.
- **Example scenario where it could fail:** A caller uses an external ID that can be an empty string, stores a document successfully, and then calls `retrieve_data('')`. Instead of one dict, the caller receives a list of all documents, which can cause downstream `Crystal.from_dict(...)` or result-processing code to fail with type errors or process the wrong records.
- **Recommended fix:** Validate `doc_id` at storage time and reject empty strings, or use `if doc_id is not None:` and preserve the single-document retrieval contract. Similarly use `query is not None` for query handling. Add tests for empty `doc_id`, `doc_id=0` if non-string IDs are intentionally unsupported, and `query={}`.

### 4. User payload fields can be silently overwritten by storage metadata

- **Location:** `matsimpy/storage/maggma_store.py:172-183`
- **Severity:** **MEDIUM**
- **Issue description:** `store_data()` writes `data_dict["metadata"]`, `data_dict["doc_id"]`, and `data_dict["stored_at"]` into the top-level payload. If the input dictionary already contains those keys, they are overwritten without warning.
- **Why it is problematic:** The storage layer mixes user data and storage-control fields in the same namespace. For arbitrary dictionaries, `metadata`, `doc_id`, or `stored_at` may be meaningful domain fields. Silent overwrites corrupt the stored payload and make round-trips inaccurate.
- **Example scenario where it could fail:** A calculation result dictionary includes its own `metadata` key from an upstream workflow. Passing `metadata={'calculator': 'DFT'}` replaces the original metadata entirely. A payload containing an experimental `stored_at` timestamp is replaced with the storage timestamp, losing provenance.
- **Recommended fix:** Reserve storage fields explicitly and either reject input dictionaries containing reserved keys unless they match the intended values, or wrap user content under a stable namespace such as `payload` with storage fields kept separately. If backward compatibility requires top-level fields, document the reserved names and add collision tests.

### 5. Bulk retrieval materializes result sets and has limited pagination controls

- **Location:** `matsimpy/storage/maggma_store.py:195-241`
- **Severity:** **LOW**
- **Issue description:** Query and “retrieve all” paths convert the maggma cursor to a list immediately and expose only `limit`, with no `skip`, projection/properties, sort, streaming iterator, or batching API.
- **Why it is problematic:** The current default limit of 100 avoids accidental full scans, but callers can pass `limit=0` to maggma for unlimited results or request a large limit. Materializing all documents can create high memory pressure for large structure/result datasets and prevents efficient incremental processing.
- **Example scenario where it could fail:** A user stores tens of thousands of structures with large force arrays and calls `retrieve_data(query={'metadata.calculator': 'DFT'}, limit=0)`. The method builds a full Python list before returning, potentially exhausting memory even though maggma could stream results.
- **Recommended fix:** Add a streaming/batched retrieval API such as `iter_data(query=None, batch_size=...)`, and expose maggma query options (`skip`, `properties`, `sort`) where appropriate. Validate `limit` and document that `limit=0` means unlimited if that behavior is retained.

## Test Coverage Gaps

- No test covers canonical ID generation across non-JSON-native types such as numpy arrays, numpy scalars, datetimes, paths, and strings with matching `str()` output.
- No test asserts JSONStore durability immediately after `store_data()`, `delete_data()`, or `clear_store()` before `close()`.
- No test covers empty or falsy `doc_id` values and the resulting return-type mismatch in `retrieve_data()`.
- No test covers collisions with reserved top-level payload fields: `metadata`, `doc_id`, and `stored_at`.
- No test covers large result sets, `limit=0`, pagination/streaming behavior, or memory characteristics.
- No test covers exception behavior when JSON flush fails, store files are malformed, store paths point to existing non-JSON content, or concurrent storage instances share one JSON file.

## Architectural Concerns

- `DataStorage` currently combines content-addressed identity, persistence lifecycle, serialization, and query API concerns in one class. A small separation between serialization/canonicalization, document envelope creation, and backend flushing would make the data mapping contract easier to test and evolve.
- The top-level document schema is implicit. Defining an explicit envelope such as `{doc_id, stored_at, metadata, payload}` would reduce reserved-field collisions and make downstream transformation/storage pipelines more consistent.
- Durability semantics are backend-dependent and implicit. MemoryStore is naturally volatile; JSONStore appears persistent but is only durable on close. The API should make this distinction explicit.

## Recommended Priority Order

1. Fix canonical ID generation and add collision regression tests (**HIGH**).
2. Decide and enforce JSONStore durability semantics, preferably with auto-flush or explicit flush plus tests (**HIGH**).
3. Validate or explicitly handle falsy document IDs and empty queries (**MEDIUM**).
4. Introduce/document reserved field handling or a payload envelope (**MEDIUM**).
5. Add streaming/pagination support for large datasets (**LOW/MEDIUM depending on expected dataset sizes**).
