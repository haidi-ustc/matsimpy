# VASP Ownership and Native Reuse Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put VASP helpers and models in their correct MatSimPy layers, reuse native APIs consistently, and repair the concrete formatting, parsing, and fallback defects found by the audit.

**Architecture:** Core owns element normalization; `electronic_structure` owns magnetic moments; shared calculator utilities own generic text scanning and formatting; VASP retains only VASP-specific records and resource policy. Each migration is protected by failure-first tests and integrated into VASP only after its lower-level contract is green.

**Tech Stack:** Python 3.12, NumPy, Monty MSON/serialization, pytest, Ruff, conda environment `pmg`.

**Spec:** `docs/superpowers/specs/2026-08-18-vasp-ownership-cleanup-design.md`

## Global Constraints

- Run every Python command through `conda run -n pmg /opt/miniconda3/envs/pmg/bin/python` so pyenv shims cannot replace the `pmg` interpreter.
- Production `matsimpy/calculator/vasp` code must not import or require pymatgen.
- Pymatgen may be used only as an optional validation oracle in tests.
- Backward compatibility with temporary migration helpers is not required.
- Add no dependencies.
- Unsupported scientific behavior must fail explicitly; do not fabricate results or silently substitute empty data.
- Preserve the user-owned deletion of the duplicate `from __future__ import annotations` line in `matsimpy/calculator/vasp/inputs.py`.
- Use `apply_patch` for source and test edits.
- Every commit follows the repository Lore commit protocol.

---

### Task 1: Make Element Resolution a Core API

**Files:**
- Modify: `matsimpy/core/periodic_table.py`
- Modify: `matsimpy/core/__init__.py`
- Modify: `tests/core/test_periodic_table_comprehensive.py`

**Interfaces:**
- Consumes: `Element.get_element(symbol: str) -> Element`, `Element.from_Z(Z: int) -> Element`
- Produces: `get_el_sp(value: Element | str | Integral) -> Element`

- [ ] **Step 1: Write failing core resolver tests**

Add tests equivalent to:

```python
def test_get_el_sp_normalizes_supported_inputs():
    from matsimpy.core import Element, get_el_sp

    fe = Element.get_element("Fe")
    assert get_el_sp(fe) is fe
    assert get_el_sp("fe") is fe
    assert get_el_sp(26) is fe


@pytest.mark.parametrize("value", [True, None, object()])
def test_get_el_sp_rejects_unsupported_inputs(value):
    from matsimpy.core import get_el_sp

    with pytest.raises((TypeError, ValueError)):
        get_el_sp(value)
```

- [ ] **Step 2: Verify RED**

Run:

```bash
conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest \
  tests/core/test_periodic_table_comprehensive.py -q
```

Expected: import failure because `matsimpy.core.get_el_sp` does not exist.

- [ ] **Step 3: Implement the core resolver**

Add a typed function to `periodic_table.py`:

```python
def get_el_sp(value: Element | str | Integral) -> Element:
    if isinstance(value, Element):
        return value
    if isinstance(value, bool):
        raise TypeError("Element values cannot be booleans")
    if isinstance(value, Integral):
        return Element.from_Z(int(value))
    if isinstance(value, str):
        return Element.get_element(value)
    raise TypeError("Element values must be Element, string, or atomic number")
```

Export it from `matsimpy.core.__init__` and `__all__`.

- [ ] **Step 4: Verify GREEN and core regressions**

Run the Task 1 test plus `tests/core/test_core_edge_cases.py`.

- [ ] **Step 5: Commit**

Commit only Task 1 files with intent `Centralize element resolution in the core domain` and Lore trailers covering the VASP reuse constraint and tested commands.

---

### Task 2: Complete the Canonical Magmom Value Object

**Files:**
- Modify: `matsimpy/electronic_structure/core.py`
- Modify: `tests/electronic_structure/test_core.py`

**Interfaces:**
- Consumes: `monty.json.MSONable`
- Produces: canonical `Magmom(value)` with `components`, sequence access, scalar conversion, equality, representation, `as_dict`, and `from_dict`

- [ ] **Step 1: Write failing Magmom protocol tests**

Cover:

```python
def test_magmom_is_an_immutable_sequence_and_scalar():
    scalar = Magmom(2.5)
    vector = Magmom([1, 2, 3])
    assert tuple(vector) == (1.0, 2.0, 3.0)
    assert vector[1] == 2.0
    assert float(scalar) == 2.5
    with pytest.raises(TypeError):
        float(vector)


def test_magmom_mson_roundtrip():
    original = Magmom([1, 2, 3])
    restored = Magmom.from_dict(original.as_dict())
    assert restored == original
    assert repr(restored) == "Magmom([1.0, 2.0, 3.0])"


@pytest.mark.parametrize("value", [[], [1, 2], [1, 2, 3, 4]])
def test_magmom_rejects_invalid_component_counts(value):
    with pytest.raises(ValueError):
        Magmom(value)
```

- [ ] **Step 2: Verify RED**

Run `tests/electronic_structure/test_core.py`; expect missing sequence/serialization behavior.

- [ ] **Step 3: Implement the minimal immutable protocol**

Store a tuple of floats; accept only one or three components; implement `__len__`, `__iter__`, `__getitem__`, `__float__`, `__eq__`, `__repr__`, `as_dict`, and `from_dict`. Do not add VASP-specific formatting to this domain object.

- [ ] **Step 4: Verify GREEN**

Run electronic-structure core and DOS tests to confirm enum/MSON behavior remains intact.

- [ ] **Step 5: Commit**

Commit Task 2 files with intent `Make magnetic moments reusable across native electronic workflows` and Lore trailers.

---

### Task 3: Repair Shared Calculator Text Utilities

**Files:**
- Modify: `matsimpy/calculator/utils.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Create: `tests/calculator/test_calculator_utils.py`

**Interfaces:**
- Produces: `clean_lines(strings, remove_empty_lines=True, rstrip_only=False)`
- Produces: `str_delimited(rows, header=None, delimiter="\t") -> str`
- Produces: `micro_pyawk(filename, search, results=None, debug=None, postdebug=None)`
- Consumed by: VASP INCAR/POSCAR parsers and OUTCAR scanning methods

- [ ] **Step 1: Write failing utility contract tests**

Add exact tests:

```python
def test_clean_lines_removes_comments_and_respects_modes():
    lines = ["  A = 1 # comment  ", "   ", "  indented  "]
    assert list(clean_lines(lines)) == ["A = 1", "indented"]
    assert list(clean_lines(lines, remove_empty_lines=False, rstrip_only=True)) == [
        "  A = 1",
        "",
        "  indented",
    ]


def test_str_delimited_formats_rows_exactly():
    assert str_delimited([["ENCUT", 520], ["ISMEAR", 0]], delimiter=" = ") == (
        "ENCUT = 520\nISMEAR = 0"
    )


def test_micro_pyawk_executes_predicate_and_action(tmp_path):
    path = tmp_path / "sample.out"
    path.write_text("skip 1\nvalue 2\nvalue 3\n")
    result = {"values": []}
    micro_pyawk(
        path,
        [(r"value (\d+)", lambda state, line: "3" not in line,
          lambda state, match: state["values"].append(int(match[1])))],
        result,
    )
    assert result == {"values": [2]}
```

- [ ] **Step 2: Verify RED**

Run the new utility test file. Expect failures from comment handling, row formatting, and missing shared `micro_pyawk`.

- [ ] **Step 3: Implement utility contracts**

Use iterator semantics for `clean_lines`, two-dimensional joining for `str_delimited`, and compiled `(regex, predicate, action)` records for `micro_pyawk`. Export `micro_pyawk` through `calculator.utils.__all__`.

- [ ] **Step 4: Remove the local OUTCAR helper**

Import `micro_pyawk` in `vasp.outputs` and delete its local implementation, including embedded `pdb.set_trace()` behavior.

- [ ] **Step 5: Verify GREEN and VASP integration**

Run:

```bash
conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest \
  tests/calculator/test_calculator_utils.py \
  tests/calculator/test_vasp_inputs.py \
  tests/calculator/test_vasp_outputs.py -q
```

- [ ] **Step 6: Commit**

Commit Task 3 files with intent `Make calculator text helpers honor their parser contracts` and Lore trailers.

---

### Task 4: Cut VASP Inputs Over to Canonical Types

**Files:**
- Modify: `matsimpy/calculator/vasp/inputs.py`
- Modify: `matsimpy/calculator/vasp/sets.py`
- Modify: `tests/calculator/test_vasp_inputs.py`
- Modify: `tests/calculator/test_vasp_sets.py`

**Interfaces:**
- Consumes: `matsimpy.core.get_el_sp`, `matsimpy.electronic_structure.Magmom`
- Produces: `PotcarOrbital`, `PotcarOrbitalDescription`, `VaspPspDirError`

- [ ] **Step 1: Preserve the user-owned edit and write failing identity/format tests**

Confirm the duplicate future import remains removed. Add tests that assert:

```python
def test_vasp_inputs_use_canonical_magmom():
    from matsimpy.calculator.vasp import inputs
    from matsimpy.electronic_structure import Magmom
    assert inputs.Magmom is Magmom


def test_incar_formats_scalar_and_vector_magmoms_exactly():
    scalar = Incar({"MAGMOM": [1.0, 1.0, -2.0]})
    assert scalar.get_str() == "MAGMOM = 2*1.0 1*-2.0\n"
    vector = Incar({"LSORBIT": True, "MAGMOM": [Magmom([1, 2, 3])]})
    assert "MAGMOM = 1.0 2.0 3.0\n" in vector.get_str()
```

Also assert that `PotcarOrbital`, `PotcarOrbitalDescription`, and `VaspPspDirError` exist while the migration-only names do not.

- [ ] **Step 2: Verify RED**

Run the two VASP input/set test files. Expect canonical identity, exact formatting, and renamed-record failures.

- [ ] **Step 3: Replace local helpers and names**

In `inputs.py`:

- import `get_el_sp` from core and `Magmom` from electronic structure;
- delete local `_is_valid_symbol`, `get_el_sp`, and `Magmom` definitions;
- replace lazy validation with an eager loop or comprehension;
- replace symbol validation with `get_el_sp` while retaining the intentional VASP4 false-name fallback;
- rename POTCAR tuple records and the PSP-directory error;
- update record creation, `isinstance` checks, and error messages.

In `sets.py`, update imports and catches for `VaspPspDirError`.

- [ ] **Step 4: Verify GREEN**

Run VASP input, set, import, and electronic core tests.

- [ ] **Step 5: Commit**

Commit Task 4 files, including the preserved duplicate-future-import deletion, with intent `Use canonical native types throughout VASP inputs` and trailers that explicitly record preservation of the user edit.

---

### Task 5: Reuse Element Resolution Across VASP Call Sites

**Files:**
- Modify: `matsimpy/calculator/vasp/inputs.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Modify: `matsimpy/calculator/vasp/sets.py`
- Modify: `tests/calculator/test_vasp_inputs.py`
- Modify: `tests/calculator/test_vasp_sets.py`

**Interfaces:**
- Consumes: `get_el_sp`
- Preserves: VASP-specific fallback for incorrect `VRHFIN = X` meaning xenon

- [ ] **Step 1: Write failing reuse regressions**

Add a hydrogen MD regression using the set that owns the current `Element("H") in structure.species` branch. Assert a hydrogen structure gets `POTIM == 0.5` and `NSW == nsteps * 4`, while a non-hydrogen structure retains `POTIM == 2.0`.

Add tests that VASP element resolution accepts an `Element`, lowercase symbol, and atomic number through the core helper without defining a second resolver.

- [ ] **Step 2: Verify RED**

Run the focused set/input tests. The hydrogen test must fail with the current object-vs-string comparison.

- [ ] **Step 3: Replace repeated element construction**

Use `get_el_sp` for VASP call sites that need element data: atomic masses, atomic numbers, metallic classification, NMR quadrupole lookup, POTCAR symbol normalization, and output symbol normalization. Where only membership is needed, compare normalized symbols directly:

```python
if "H" in self.structure.species:
    ...
```

Do not force VASP's documented xenon/potential-name correction through a generic resolver before its special case is applied.

- [ ] **Step 4: Remove `Structure = Crystal` aliases in touched VASP modules**

Replace annotations and `isinstance` checks with `Crystal`; update misleading pymatgen structure docstrings. Do not alter the core abstract `Structure` class elsewhere in the repository.

- [ ] **Step 5: Verify GREEN and scan for bypasses**

Run focused tests, then:

```bash
rg -n 'Structure = Crystal|Element\(' matsimpy/calculator/vasp --glob '*.py'
```

Review every remaining `Element(` occurrence; retain only calls with a documented reason.

- [ ] **Step 6: Commit**

Commit with intent `Resolve VASP species through the native core API` and Lore trailers.

---

### Task 6: Replace Masking Resource Loaders

**Files:**
- Create: `matsimpy/calculator/vasp/_resources.py`
- Modify: `matsimpy/calculator/vasp/inputs.py`
- Modify: `matsimpy/calculator/vasp/sets.py`
- Create: `tests/calculator/test_vasp_resources.py`
- Modify: `tests/test_packaging_runtime_contracts.py`

**Interfaces:**
- Produces: `load_vasp_resource(path, *, required=True) -> Mapping`
- Consumes: `monty.serialization.loadfn`, `matsimpy.exceptions.FormatError`

- [ ] **Step 1: Write failing resource tests**

Cover valid JSON/YAML loading, missing required files, malformed required files, and explicitly optional missing files:

```python
def test_required_resource_failure_has_context(tmp_path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FormatError, match="missing.yaml") as exc:
        load_vasp_resource(missing)
    assert isinstance(exc.value.__cause__, FileNotFoundError)


def test_optional_resource_allows_only_absence(tmp_path):
    assert load_vasp_resource(tmp_path / "missing.json", required=False) == {}
    malformed = tmp_path / "bad.json"
    malformed.write_text("{")
    with pytest.raises(FormatError):
        load_vasp_resource(malformed, required=False)
```

- [ ] **Step 2: Verify RED**

Run the new resource tests; expect module import failure.

- [ ] **Step 3: Implement the focused loader**

Catch `FileNotFoundError` separately for `required=False`. Wrap every other loading failure in `FormatError` with path context and exception chaining. Validate that a mapping is returned where callers require one.

- [ ] **Step 4: Replace both `_safe_loadfn` definitions**

Required packaged YAML/JSON/hash/stat files use the strict default. The user-supplied append file in `_gen_potcar_summary_stats` may use `required=False` only when absence is an explicitly supported starting state.

- [ ] **Step 5: Verify installed resources and imports**

Run resource tests, VASP input/set tests, and the installed-copy packaging contract.

- [ ] **Step 6: Commit**

Commit with intent `Expose VASP resource failures at their source` and Lore trailers.

---

### Task 7: Remove Migration-Only Wrappers and Silent Write Failures

**Files:**
- Modify: `matsimpy/calculator/vasp/inputs.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Modify: `matsimpy/calculator/vasp/sets.py`
- Modify: `tests/calculator/test_vasp_inputs.py`
- Modify: `tests/calculator/test_vasp_outputs.py`
- Modify: `tests/calculator/test_vasp_sets.py`

**Interfaces:**
- Canonical APIs: `Poscar.get_str`, `VaspInputSet.get_input_set`, `projected_magnetization`
- Explicit branch API: `get_band_structure_from_vasp_multiple_branches`

- [ ] **Step 1: Write failing canonical-surface tests**

Assert migration-only forwarding attributes are absent and internal callers use canonical methods. Add a no-`branch_0` regression asserting `get_band_structure_from_vasp_multiple_branches` fails clearly instead of falling back to a single `vasprun.xml`.

Add a write/archive regression that injects a `ZipFile.write` or removal failure and asserts the original failure propagates rather than being swallowed.

- [ ] **Step 2: Verify RED**

Run the focused VASP tests. Expect wrapper presence, legacy branch fallback, or swallowed archive failure to violate the new contracts.

- [ ] **Step 3: Remove pure wrappers and update internal consumers**

Remove:

- `Poscar.get_string`;
- `VaspInputSet.get_vasp_input`, after changing the `calculate_ng` consumer to `get_input_set`;
- both `projected_magnetisation` forwarding properties;
- the expired no-branch single-file fallback.

Replace broad `pass` blocks in the touched archive path with explicit propagation or contextual `OSError`. Keep permissive scientific parsers unchanged unless a test in this task proves a masking defect.

- [ ] **Step 4: Clean migration-only wording**

Replace generated comments and runtime errors that incorrectly tell users MatSimPy output was generated by pymatgen. Keep required attribution headers and historical hash provenance.

- [ ] **Step 5: Verify GREEN**

Run all VASP calculator tests and the recursive AST import boundary test.

- [ ] **Step 6: Commit**

Commit with intent `Keep only canonical and observable VASP execution paths` and Lore trailers.

---

### Task 8: Whole-Surface Verification and Review

**Files:**
- Modify only if a failure-first regression exposes a defect in Tasks 1-7.
- Record verification evidence in the implementation report or commit body; do not add generated logs to the package.

**Interfaces:**
- Validates the complete ownership migration.

- [ ] **Step 1: Run focused native/VASP tests**

```bash
conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest \
  tests/calculator/test_calculator_utils.py \
  tests/calculator/test_vasp_imports.py \
  tests/calculator/test_vasp_inputs.py \
  tests/calculator/test_vasp_outputs.py \
  tests/calculator/test_vasp_sets.py \
  tests/calculator/test_vasp_native_outputs.py \
  tests/calculator/test_vasp_resources.py \
  tests/core/test_periodic_table_comprehensive.py \
  tests/electronic_structure/test_core.py \
  tests/electronic_structure/test_dos.py \
  tests/test_packaging_runtime_contracts.py -q
```

- [ ] **Step 2: Run static and boundary checks**

```bash
conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m compileall -q matsimpy
conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m ruff check \
  matsimpy/core/periodic_table.py \
  matsimpy/electronic_structure/core.py \
  matsimpy/calculator/utils.py \
  matsimpy/calculator/vasp \
  tests/calculator/test_calculator_utils.py \
  tests/calculator/test_vasp_resources.py
git diff --check
```

Run the recursive AST boundary test and confirm zero production pymatgen imports.

- [ ] **Step 3: Run the full suite**

```bash
conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest -q
```

Expected on the main checkout: all tests pass. If fixture availability differs in an isolated worktree, compare failures precisely with the main-checkout baseline and do not fabricate missing fixtures.

- [ ] **Step 4: Run independent whole-diff review**

Review ownership, error semantics, scientific boundaries, serialization, and user-owned-change preservation. Resolve every Critical or Important finding through a new failure-first regression.

- [ ] **Step 5: Commit any verified final corrections**

If no corrections are required, do not create an empty commit. Otherwise use a Lore commit whose intent describes the verified boundary correction and lists every validation command.
