# Fix P1 Architecture and Correctness Issues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all P1 findings from the broader MatSimPy architecture review without mixing in unrelated P2/P3 cleanup.

**Architecture:** Treat each P1 as a contract repair: first add a failing regression test that reproduces the report evidence, then make the smallest implementation change that restores the contract, then run the module-level targeted tests. Keep fixes split by subsystem so Core, calculator, AI, storage, transformation, and builders can be reviewed independently.

**Tech Stack:** Python 3.12, pytest, MatSimPy core models, MatSimPy calculator/input-output adapters, AI runtime/skill framework, storage facade, transformation and builder registries.

---

## File Structure

Expected test additions and source edits:

- Modify: `matsimpy/core/structure.py`
- Modify: `matsimpy/core/crystal.py`
- Modify: `matsimpy/core/molecule.py`
- Test: `tests/core/test_core_p1_regressions.py`

- Modify: `matsimpy/calculator/vasp/calculator.py`
- Test: `tests/calculator/test_vasp_calculator.py`

- Modify: `matsimpy/calculator/lammps/calculator.py`
- Test: `tests/calculator/test_lammps_calculator_p1.py`

- Modify: `matsimpy/ai/executor.py`
- Modify: `matsimpy/ai/runtime.py`
- Test: `tests/ai/test_executor.py`
- Test: `tests/ai/test_runtime.py`

- Modify: `matsimpy/ai/skills/storage.py`
- Test: `tests/ai/test_storage_skill_isolation.py`

- Modify: `matsimpy/storage/facade.py`
- Test: `tests/storage/test_storage_contract_no_maggma.py`

- Modify: `matsimpy/transformation/_register.py`
- Test: `tests/contracts/test_transformation_contract.py`
- Test: `tests/transformation/test_transformation_regressions.py`

- Modify: `matsimpy/builders/_register.py`
- Test: `tests/contracts/test_builder_contract.py`
- Test: `tests/builders/test_builders_bulk.py`

Do not modify the broader-review report in this plan. If a fix reveals that a P1 finding has a different root cause, update this plan in a separate commit before changing implementation scope.

---

### Task 1: Core Construction Invariants

**Files:**
- Modify: `matsimpy/core/structure.py`
- Modify: `matsimpy/core/crystal.py`
- Modify: `matsimpy/core/molecule.py`
- Test: `tests/core/test_core_p1_regressions.py`

- [ ] **Step 1: Add failing tests for mutation and `_construct` invariant bypasses**

Create `tests/core/test_core_p1_regressions.py` with:

```python
"""P1 regression tests for core structure invariants."""

import numpy as np
import pytest

from matsimpy import Crystal, Lattice, Molecule


def test_molecule_add_atom_rejects_nan_position():
    molecule = Molecule(["He"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="NaN"):
        molecule.add_atom("Ne", [float("nan"), 0, 0])


def test_crystal_add_atom_rejects_nan_position():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))

    with pytest.raises(ValueError, match="NaN"):
        crystal.add_atom("Ne", [float("nan"), 0, 0])


def test_structure_construct_rejects_species_position_length_mismatch():
    with pytest.raises(ValueError, match="Number of positions"):
        Molecule._construct(("H", "O"), np.zeros((1, 3)))


def test_crystal_construct_rejects_infinite_position():
    with pytest.raises(ValueError, match="infinite"):
        Crystal._construct(
            ("He",),
            np.array([[float("inf"), 0, 0]]),
            Lattice.cubic(3),
            (True, True, True),
        )
```

- [ ] **Step 2: Run the new core tests and verify they fail**

Run:

```bash
python -m pytest tests/core/test_core_p1_regressions.py -q
```

Expected: FAIL. At least the NaN/Inf and length mismatch tests must fail because the current mutation and `_construct` paths accept invalid data.

- [ ] **Step 3: Add a shared lightweight constructor validator**

In `matsimpy/core/structure.py`, add this helper as a `@staticmethod` near `_validate_positions`:

```python
    @staticmethod
    def _validate_constructed_state(species, positions) -> tuple[tuple[str, ...], np.ndarray]:
        """Normalize species and validate positions for lightweight constructors."""
        normalized_species = tuple(normalize_species(s) for s in species)
        positions_array = Structure._validate_positions(positions)
        if len(positions_array) != len(normalized_species):
            raise ValueError(
                f"Number of positions ({len(positions_array)}) must match "
                f"number of species ({len(normalized_species)})"
            )
        positions_array.flags.writeable = False
        return normalized_species, positions_array
```

Then change `Structure._construct()` so it uses the helper:

```python
        obj = cls.__new__(cls)
        obj._species, obj._positions = cls._validate_constructed_state(species, positions)
        obj.lattice = lattice
```

- [ ] **Step 4: Update `Crystal._construct()` and `Molecule._construct()` to use the same validator**

In `matsimpy/core/crystal.py`, replace the local species/positions setup inside `_construct()` with:

```python
        obj._species, obj._positions = cls._validate_constructed_state(species, positions)
```

Keep the existing `validate_lattice(lattice)` and `validate_pbc(pbc)` calls before assigning `obj.lattice` and `obj.pbc`.

In `matsimpy/core/molecule.py`, replace the local species/positions setup inside `_construct()` with:

```python
        obj._species, obj._positions = cls._validate_constructed_state(species, positions)
```

- [ ] **Step 5: Make `add_atom()` validate new positions through `_validate_positions()`**

In `matsimpy/core/molecule.py`, after `new_positions` is normalized and before duplicate-distance checks, add:

```python
        new_positions_array = self._validate_positions(new_positions)
```

Use `new_positions_array` for the duplicate and too-close distance checks instead of recreating `np.array(new_positions, dtype=np.float64)`.

In `matsimpy/core/crystal.py`, after `new_pos_array = np.array(new_positions, dtype=np.float64)` is created, replace that conversion with:

```python
            new_pos_array = self._validate_positions(new_positions)
```

Then keep the existing fractional/cartesian conversion logic.

- [ ] **Step 6: Run focused core regression tests**

Run:

```bash
python -m pytest tests/core/test_core_p1_regressions.py tests/core/test_immutability.py tests/core/test_core_design_fixes.py tests/core/test_structure_mutations.py tests/core/test_site_properties_validation.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
git add matsimpy/core/structure.py matsimpy/core/crystal.py matsimpy/core/molecule.py tests/core/test_core_p1_regressions.py
git commit -m "Enforce core mutation invariants" -m "Close P1 invariant gaps by routing lightweight construction and add_atom paths through finite position and cardinality validation." -m "Constraint: Keep behavior changes limited to invalid NaN/Inf and species-position mismatch states." -m "Confidence: high" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/core/test_core_p1_regressions.py tests/core/test_immutability.py tests/core/test_core_design_fixes.py tests/core/test_structure_mutations.py tests/core/test_site_properties_validation.py -q" -m "Not-tested: Full repository test suite."
```

---

### Task 2: Crystal PBC Equality And Structural Hash

**Files:**
- Modify: `matsimpy/core/structure.py`
- Modify: `matsimpy/core/crystal.py`
- Test: `tests/core/test_core_p1_regressions.py`

- [ ] **Step 1: Add failing tests for PBC-sensitive equality and structural hash**

Append to `tests/core/test_core_p1_regressions.py`:

```python
def test_crystal_equality_includes_pbc():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))
    non_periodic = crystal.set_pbc([False, False, False])

    assert crystal != non_periodic


def test_crystal_structural_hash_includes_pbc():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(3))
    non_periodic = crystal.set_pbc([False, False, False])

    assert crystal._structural_hash() != non_periodic._structural_hash()
```

- [ ] **Step 2: Run the new PBC tests and verify they fail**

Run:

```bash
python -m pytest tests/core/test_core_p1_regressions.py::test_crystal_equality_includes_pbc tests/core/test_core_p1_regressions.py::test_crystal_structural_hash_includes_pbc -q
```

Expected: FAIL. Current equality and structural hash ignore PBC.

- [ ] **Step 3: Include PBC in structural hash**

In `matsimpy/core/structure.py`, inside `_structural_hash()`, add PBC when present:

```python
        if hasattr(self, "pbc"):
            hash_dict["pbc"] = list(self.pbc)
```

Place it after the lattice block so hashes stay deterministic.

- [ ] **Step 4: Override equality for `Crystal`**

In `matsimpy/core/crystal.py`, add this method inside `Crystal`:

```python
    def __eq__(self, other) -> bool:
        if not super().__eq__(other):
            return False
        if isinstance(other, Crystal):
            return self.pbc == other.pbc
        return False
```

Do not change `Molecule` equality.

- [ ] **Step 5: Run core equality/hash tests**

Run:

```bash
python -m pytest tests/core/test_core_p1_regressions.py tests/core/test_hash_robustness.py tests/core/test_crystal_comprehensive.py -q
```

Expected: PASS. If an existing test intentionally expects PBC-insensitive equality, update that test to call a new explicit geometry comparison only after adding such API in a separate plan; do not weaken this P1 fix.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add matsimpy/core/structure.py matsimpy/core/crystal.py tests/core/test_core_p1_regressions.py
git commit -m "Include PBC in crystal identity" -m "Make Crystal equality and structural hashes distinguish periodic boundary semantics so calculator invalidation cannot reuse results across different PBC states." -m "Constraint: Molecule equality remains unchanged." -m "Confidence: high" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/core/test_core_p1_regressions.py tests/core/test_hash_robustness.py tests/core/test_crystal_comprehensive.py -q" -m "Not-tested: Full repository test suite."
```

---

### Task 3: VASP Forces And Stress Parsing

**Files:**
- Modify: `matsimpy/calculator/vasp/calculator.py`
- Test: `tests/calculator/test_vasp_calculator.py`

- [ ] **Step 1: Add failing fixture assertions for forces and stress**

In `tests/calculator/test_vasp_calculator.py`, update `test_read_results_with_real_vasprun` so it asserts:

```python
        assert "energy" in calc.results
        assert "forces" in calc.results
        assert calc.results["forces"].shape == (8, 3)
        assert "stress" in calc.results
        assert calc.results["stress"].shape == (3, 3)
```

Keep the existing energy assertions.

- [ ] **Step 2: Run the VASP calculator test and verify it fails**

Run:

```bash
python -m pytest tests/calculator/test_vasp_calculator.py::TestVaspCalculator::test_read_results_with_real_vasprun -q
```

Expected: FAIL because current `calc.results` contains energy only.

- [ ] **Step 3: Read forces and stress from the final ionic step**

In `matsimpy/calculator/vasp/calculator.py`, replace the `force_constants`-gated forces block with:

```python
            if len(vasprun.ionic_steps) > 0:
                final_step = vasprun.ionic_steps[-1]
                forces = final_step.get("forces")
                stress = final_step.get("stress")
```

Do not require `force_constants`.

- [ ] **Step 4: Run targeted VASP tests**

Run:

```bash
python -m pytest tests/calculator/test_vasp_calculator.py tests/calculator/test_vasp_outputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add matsimpy/calculator/vasp/calculator.py tests/calculator/test_vasp_calculator.py
git commit -m "Parse VASP forces and stress from vasprun" -m "Populate forces and stress from the final ionic step instead of gating normal force parsing behind phonon force constants." -m "Constraint: Preserve existing OUTCAR and OSZICAR fallback behavior." -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python -m pytest tests/calculator/test_vasp_calculator.py tests/calculator/test_vasp_outputs.py -q" -m "Not-tested: Real VASP execution."
```

---

### Task 4: LAMMPS Data File Generation

**Files:**
- Modify: `matsimpy/calculator/lammps/calculator.py`
- Test: `tests/calculator/test_lammps_calculator_p1.py`

- [ ] **Step 1: Add failing tests for multi-species and triclinic output**

Create `tests/calculator/test_lammps_calculator_p1.py` with:

```python
"""P1 regression tests for LAMMPS calculator input generation."""

from matsimpy import Crystal, Lattice
from matsimpy.calculator.lammps.calculator import LammpsCalculator


def test_lammps_data_file_preserves_multiple_atom_types(tmp_path):
    crystal = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
    calc = LammpsCalculator(directory=str(tmp_path), run=False)

    calc.write_input(crystal)

    text = (tmp_path / "data.lammps").read_text()
    assert "2 atom types" in text
    assert "Masses" in text
    assert "1 " in text
    assert "2 " in text


def test_lammps_data_file_preserves_triclinic_tilt(tmp_path):
    lattice = Lattice.from_parameters(3.0, 4.0, 5.0, 80, 75, 70)
    crystal = Crystal(["Si"], [[0, 0, 0]], lattice)
    calc = LammpsCalculator(directory=str(tmp_path), run=False)

    calc.write_input(crystal)

    text = (tmp_path / "data.lammps").read_text()
    assert "xy xz yz" in text
```

- [ ] **Step 2: Run the new LAMMPS tests and verify they fail**

Run:

```bash
python -m pytest tests/calculator/test_lammps_calculator_p1.py -q
```

Expected: FAIL because current writer hard-codes one atom type and orthogonal bounds.

- [ ] **Step 3: Prefer existing `LammpsData.from_structure()` when compatible**

In `matsimpy/calculator/lammps/calculator.py`, add a private method:

```python
    def _write_data_file(self, structure: Crystal | Molecule) -> None:
        if isinstance(structure, Crystal):
            try:
                from .data import LammpsData

                data = LammpsData.from_structure(structure, atom_style="atomic")
                data.write_file(str(self.directory / "data.lammps"))
                return
            except Exception:
                pass
        self._write_simple_data_file(structure)
```

Then move the current manual data file writer into `_write_simple_data_file()`. This preserves molecule fallback and avoids assuming the adapted `LammpsData` path works for every MatSimPy object.

- [ ] **Step 4: Make the simple fallback handle species types and triclinic boxes**

Inside `_write_simple_data_file()`, replace `"1 atom types"` with species mapping:

```python
        species_order = list(dict.fromkeys(structure.species))
        type_by_species = {symbol: index + 1 for index, symbol in enumerate(species_order)}
```

Write:

```python
            f"{len(species_order)} atom types",
```

For masses, use:

```python
        from matsimpy.core import Element

        data_lines.extend(["", "Masses", ""])
        for symbol, atom_type in type_by_species.items():
            data_lines.append(f"{atom_type} {Element(symbol).atomic_mass:.8f}")
```

For atom lines, use:

```python
        data_lines.extend(["", "Atoms", ""])
        for i, (species, pos) in enumerate(zip(structure.species, structure.positions), 1):
            data_lines.append(
                f"{i} {type_by_species[species]} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}"
            )
```

For non-orthogonal crystals, compute tilt factors from `lattice.matrix` or use `.data.lattice_2_lmpbox()` directly. If `LammpsData.from_structure()` succeeds for crystals, the fallback only needs molecule/simple orthogonal handling; keep the test green with the existing richer path.

- [ ] **Step 5: Wire `write_input()` through `_write_data_file()`**

In `write_input()`, replace manual data generation with:

```python
        self._write_data_file(structure)
```

Keep input script generation unchanged.

- [ ] **Step 6: Run LAMMPS and calculator tests**

Run:

```bash
python -m pytest tests/calculator/test_lammps_calculator_p1.py tests/calculator/test_calculator_base.py tests/calculator/test_vasp_imports.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

Run:

```bash
git add matsimpy/calculator/lammps/calculator.py tests/calculator/test_lammps_calculator_p1.py
git commit -m "Preserve LAMMPS atom types and boxes" -m "Route LAMMPS calculator data generation through richer structure conversion where possible and make the fallback preserve species types and masses." -m "Constraint: Do not require running a LAMMPS binary for input-generation tests." -m "Confidence: medium" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/calculator/test_lammps_calculator_p1.py tests/calculator/test_calculator_base.py tests/calculator/test_vasp_imports.py -q" -m "Not-tested: Real LAMMPS execution."
```

---

### Task 5: AI Executor Context Isolation

**Files:**
- Modify: `matsimpy/ai/executor.py`
- Modify: `matsimpy/ai/runtime.py`
- Test: `tests/ai/test_executor.py`
- Test: `tests/ai/test_runtime.py`

- [ ] **Step 1: Add failing test for active executor context isolation**

Append to `tests/ai/test_executor.py`:

```python
def test_active_executor_is_context_local(si_crystal, water):
    import contextvars
    from matsimpy.ai.executor import (
        FunctionExecutor,
        _set_active_executor,
        get_last_structure,
        set_last_structure,
    )
    from matsimpy.ai.skill import SkillManager

    crystal_executor = FunctionExecutor(SkillManager())
    molecule_executor = FunctionExecutor(SkillManager())

    crystal_context = contextvars.Context()
    molecule_context = contextvars.Context()

    crystal_context.run(_set_active_executor, crystal_executor)
    crystal_context.run(set_last_structure, si_crystal)

    molecule_context.run(_set_active_executor, molecule_executor)
    molecule_context.run(set_last_structure, water)

    assert crystal_context.run(get_last_structure) is si_crystal
    assert molecule_context.run(get_last_structure) is water
```

This fails with a process-global `_active_executor` because the second `_set_active_executor()` overwrites the first context.

- [ ] **Step 2: Run the isolation test and verify it fails**

Run:

```bash
python -m pytest tests/ai/test_executor.py::test_active_executor_is_context_local -q
```

Expected: FAIL under the current module-global `_active_executor`.

- [ ] **Step 3: Replace module-global `_active_executor` with a `ContextVar`**

In `matsimpy/ai/executor.py`, import `ContextVar`:

```python
from contextvars import ContextVar
```

Replace:

```python
_active_executor: FunctionExecutor | None = None
```

with:

```python
_active_executor: ContextVar[FunctionExecutor | None] = ContextVar(
    "matsimpy_active_executor",
    default=None,
)
```

Change `get_last_structure()` to:

```python
def get_last_structure():
    """Return the most recently serialized structure from the active executor."""
    executor = _active_executor.get()
    if executor is not None and executor._registry:
        max_id = max(executor._registry.keys())
        return executor._registry[max_id]
    return None
```

Change `set_last_structure()` to:

```python
def set_last_structure(s):
    """Store a structure in the active executor's registry."""
    executor = _active_executor.get()
    if executor is not None:
        ref = executor._next_id
        executor._next_id += 1
        executor._registry[ref] = s
```

Change `_set_active_executor()` to:

```python
def _set_active_executor(exe: FunctionExecutor) -> None:
    """Register the active executor for the current execution context."""
    _active_executor.set(exe)
```

- [ ] **Step 4: Keep runtime setting active executor at run boundaries**

In `matsimpy/ai/runtime.py`, keep `_set_active_executor(self.executor)` in `__init__()` and `run()`. Do not add new process-global state.

- [ ] **Step 5: Run AI executor/runtime tests**

Run:

```bash
python -m pytest tests/ai/test_executor.py tests/ai/test_runtime.py tests/ai/test_io_skill_paths.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

Run:

```bash
git add matsimpy/ai/executor.py matsimpy/ai/runtime.py tests/ai/test_executor.py
git commit -m "Isolate AI executor context" -m "Replace process-global active executor state with context-local executor access so concurrent runtime contexts do not leak last-structure state." -m "Constraint: Preserve existing skill helper APIs get_last_structure and set_last_structure." -m "Confidence: medium" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/ai/test_executor.py tests/ai/test_runtime.py tests/ai/test_io_skill_paths.py -q" -m "Not-tested: Real provider network calls."
```

---

### Task 6: AI Storage Skill Session Isolation

**Files:**
- Modify: `matsimpy/ai/executor.py`
- Modify: `matsimpy/ai/skills/storage.py`
- Test: `tests/ai/test_storage_skill_isolation.py`

- [ ] **Step 1: Add failing tests for per-executor storage**

Create `tests/ai/test_storage_skill_isolation.py` with:

```python
"""P1 regression tests for AI storage skill isolation."""

from matsimpy import Molecule
from matsimpy.ai.executor import FunctionExecutor, _set_active_executor
from matsimpy.ai.skill import SkillManager
from matsimpy.ai.skills import storage


def test_storage_skill_uses_active_executor_store(tmp_path, monkeypatch):
    first = FunctionExecutor(SkillManager())
    second = FunctionExecutor(SkillManager())
    helium = tmp_path / "helium.xyz"
    neon = tmp_path / "neon.xyz"
    helium.write_text("1\nhelium\nHe 0 0 0\n")
    neon.write_text("1\nneon\nNe 0 0 0\n")
    monkeypatch.chdir(tmp_path)

    _set_active_executor(first)
    first_id = storage._store_structure("helium.xyz", {"owner": "first"})["doc_id"]

    _set_active_executor(second)
    second_id = storage._store_structure("neon.xyz", {"owner": "second"})["doc_id"]

    assert storage._retrieve_structure(second_id)["formula"] == Molecule(["Ne"], [[0, 0, 0]]).formula

    _set_active_executor(first)
    assert storage._retrieve_structure(first_id)["formula"] == Molecule(["He"], [[0, 0, 0]]).formula
    assert storage._query_structures("owner", "second")["count"] == 0
```

- [ ] **Step 2: Run the storage isolation test and verify it fails**

Run:

```bash
python -m pytest tests/ai/test_storage_skill_isolation.py -q
```

Expected: FAIL or show shared-store leakage under the current module-level `_store`.

- [ ] **Step 3: Add executor-owned skill state**

In `matsimpy/ai/executor.py`, initialize a dict on `FunctionExecutor`:

```python
        self.skill_state: dict[str, object] = {}
```

Add:

```python
def get_active_executor() -> FunctionExecutor | None:
    """Return the active executor for the current execution context."""
    return _active_executor.get()
```

Export it in `__all__`.

- [ ] **Step 4: Replace module-level storage with active executor state**

In `matsimpy/ai/skills/storage.py`, remove module-level `_store`. Add:

```python
from matsimpy.ai.executor import get_active_executor


def _get_store():
    executor = get_active_executor()
    if executor is None:
        raise RuntimeError("No active AI executor for storage skill")
    store = executor.skill_state.get("storage")
    if store is None:
        store = DataStorage(backend=MemoryBackend())
        executor.skill_state["storage"] = store
    return store
```

Then update `_store_structure()`, `_retrieve_structure()`, and `_query_structures()` to call:

```python
    store = _get_store()
```

and use `store` instead of `_store`.

- [ ] **Step 5: Run AI storage/runtime tests**

Run:

```bash
python -m pytest tests/ai/test_storage_skill_isolation.py tests/ai/test_runtime.py tests/ai/test_skill_loader.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

Run:

```bash
git add matsimpy/ai/executor.py matsimpy/ai/skills/storage.py tests/ai/test_storage_skill_isolation.py
git commit -m "Scope AI storage skill to executor sessions" -m "Move AI storage skill state from a module-level MemoryBackend into active executor skill state so stored structures do not leak across sessions." -m "Constraint: Keep public storage skill function signatures unchanged." -m "Confidence: medium" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/ai/test_storage_skill_isolation.py tests/ai/test_runtime.py tests/ai/test_skill_loader.py -q" -m "Not-tested: Persistent storage backends through AI skills."
```

---

### Task 7: Raw Dict Storage Metadata Enforcement

**Files:**
- Modify: `matsimpy/storage/facade.py`
- Test: `tests/storage/test_storage_contract_no_maggma.py`

- [ ] **Step 1: Add failing test for raw dict reserved metadata**

Append to `tests/storage/test_storage_contract_no_maggma.py`:

```python
def test_raw_dict_storage_rejects_reserved_metadata_keys():
    from matsimpy.storage import DataStorage, MemoryBackend

    storage = DataStorage(backend=MemoryBackend())

    with pytest.raises(ValueError, match="reserved"):
        storage.store_data({"x": 1}, metadata={"doc_id": "shadow"})
```

If the file does not already import `pytest`, add:

```python
import pytest
```

- [ ] **Step 2: Run the storage test and verify it fails**

Run:

```bash
python -m pytest tests/storage/test_storage_contract_no_maggma.py::test_raw_dict_storage_rejects_reserved_metadata_keys -q
```

Expected: FAIL because raw dict storage currently accepts reserved metadata.

- [ ] **Step 3: Validate metadata in the raw dict branch**

In `matsimpy/storage/facade.py`, in `DataStorage.store_data()`, change the dict branch to:

```python
        elif isinstance(data, dict):
            metadata = metadata or {}
            DocumentEnvelope.validate_metadata(metadata)
            if doc_id is None:
                doc_id = DocumentEnvelope.generate_id(data, metadata)
            envelope = DocumentEnvelope(
                doc_id=doc_id,
                payload=data,
                metadata=metadata,
            )
```

Use the existing `DocumentEnvelope` import.

- [ ] **Step 4: Run storage tests**

Run:

```bash
python -m pytest tests/storage/test_storage_contract_no_maggma.py tests/storage/test_storage.py tests/contracts/test_storage_backend_contract.py -q
```

Expected: PASS or skip maggma-dependent tests according to the local environment.

- [ ] **Step 5: Commit Task 7**

Run:

```bash
git add matsimpy/storage/facade.py tests/storage/test_storage_contract_no_maggma.py
git commit -m "Validate raw storage metadata" -m "Apply reserved metadata key checks to raw dict storage so storage facade behavior matches the MSONable codec path." -m "Constraint: Preserve content-addressed ID generation for valid raw dict payloads." -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python -m pytest tests/storage/test_storage_contract_no_maggma.py tests/storage/test_storage.py tests/contracts/test_storage_backend_contract.py -q" -m "Not-tested: Real MaggmaBackend persistence."
```

---

### Task 8: Transformation Registry Spec/Callable Alignment

**Files:**
- Modify: `matsimpy/transformation/_register.py`
- Test: `tests/transformation/test_transformation_regressions.py`
- Test: `tests/contracts/test_transformation_contract.py`

- [ ] **Step 1: Add failing registry execution tests**

Append to `tests/transformation/test_transformation_regressions.py`:

```python
def test_registry_apply_strain_executes_registered_schema():
    from matsimpy import Crystal, Lattice
    from matsimpy.transformation import registry

    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    strained = registry.apply(
        "apply_strain",
        crystal,
        strain_matrix=[[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
    )

    assert strained.lattice.a > crystal.lattice.a


def test_registry_swap_atoms_executes_registered_schema():
    from matsimpy import Molecule
    from matsimpy.transformation import registry

    molecule = Molecule(["H", "O"], [[0, 0, 0], [1, 0, 0]])
    swapped = registry.apply("swap_atoms", molecule, index1=0, index2=1)

    assert swapped.species == ("H", "O")
    assert swapped.positions[0].tolist() == [1.0, 0.0, 0.0]
```

- [ ] **Step 2: Run the new transformation tests and verify they fail before schema updates**

Run:

```bash
python -m pytest tests/transformation/test_transformation_regressions.py::test_registry_apply_strain_executes_registered_schema tests/transformation/test_transformation_regressions.py::test_registry_swap_atoms_executes_registered_schema -q
```

Expected: FAIL because the current schema uses `strain` and `i/j`.

- [ ] **Step 3: Align schema names in `_register.py`**

In `matsimpy/transformation/_register.py`, change the `apply_strain` spec:

```python
            "properties": {"strain_matrix": _M3},
            "required": ["strain_matrix"],
```

Change the `apply_deformation` spec if the callable expects `deformation_gradient`:

```python
            "properties": {"deformation_gradient": _M3},
            "required": ["deformation_gradient"],
```

Confirm against `matsimpy/transformation/lattice/strain.py` before editing.

Change `swap_atoms` and `merge_atoms` specs to:

```python
                "index1": {"type": "integer"},
                "index2": {"type": "integer"},
```

with:

```python
            "required": ["index1", "index2"],
```

Change `fragment_molecule` spec from `indices` to:

```python
                    "break_indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
```

with:

```python
                "required": ["break_indices"],
```

- [ ] **Step 4: Add a contract guard against unexpected-keyword skips**

In `tests/contracts/test_transformation_contract.py`, where registry application currently skips broad `TypeError`, add logic that fails messages containing `"unexpected keyword argument"` or `"missing" ... "required positional argument"`:

```python
        except TypeError as exc:
            message = str(exc)
            if "unexpected keyword argument" in message or "required positional argument" in message:
                raise
            pytest.skip(f"Requires more specific kwargs: {exc}")
```

Keep skip behavior for semantic errors that the generated minimal kwargs cannot satisfy.

- [ ] **Step 5: Run transformation registry tests**

Run:

```bash
python -m pytest tests/transformation/test_transformation_regressions.py tests/contracts/test_transformation_contract.py -q
```

Expected: PASS with no unexpected-keyword or missing-required-positional registry failures.

- [ ] **Step 6: Commit Task 8**

Run:

```bash
git add matsimpy/transformation/_register.py tests/transformation/test_transformation_regressions.py tests/contracts/test_transformation_contract.py
git commit -m "Align transformation registry schemas" -m "Make registered transformation parameter schemas executable by matching callable signatures and failing contract tests on schema-callable mismatches." -m "Constraint: Keep public functional transformation call signatures unchanged." -m "Confidence: high" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/transformation/test_transformation_regressions.py tests/contracts/test_transformation_contract.py -q" -m "Not-tested: Full transformation suite."
```

---

### Task 9: Random Crystal Builder Registry Contract

**Files:**
- Modify: `matsimpy/builders/_register.py`
- Test: `tests/builders/test_builders_bulk.py`
- Test: `tests/contracts/test_builder_contract.py`

- [ ] **Step 1: Add failing registry test for `random_crystal` argument mapping**

Append to `tests/builders/test_builders_bulk.py`:

```python
def test_random_crystal_registry_maps_public_schema_to_callable(monkeypatch):
    import matsimpy.builders._register as register_module
    from matsimpy import Crystal, Lattice
    from matsimpy.builders.registry import BuilderRegistry

    def fake_random_crystal(dim, group, species, num_ions, **kwargs):
        assert dim == 3
        assert group == 225
        assert species == ["Si"]
        assert num_ions == [1]
        assert kwargs["factor"] == 1.0
        return Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))

    registry = BuilderRegistry()
    monkeypatch.setattr(register_module, "registry", registry)
    monkeypatch.setattr(
        "matsimpy.builders.bulk.random.random_crystal",
        fake_random_crystal,
        raising=False,
    )

    register_module.register_all()
    result = registry.build("random_crystal", sg=225, species=["Si"], numIons=[1])

    assert result.formula == "Si"
```

If monkeypatching the imported function path does not intercept due import timing, define the adapter in `_register.py` first in Step 3 and adjust this test to call the adapter directly.

- [ ] **Step 2: Run the random crystal registry test and verify it fails**

Run:

```bash
python -m pytest tests/builders/test_builders_bulk.py::test_random_crystal_registry_maps_public_schema_to_callable -q
```

Expected: FAIL because schema names `sg` and `numIons` are passed directly to `random_crystal()`.

- [ ] **Step 3: Add a registry adapter for public PyXtal-style names**

In `matsimpy/builders/_register.py`, inside the `try:` block before registering `random_crystal`, add:

```python
        def _random_crystal_from_registry(
            sg,
            species,
            numIons,
            dim=3,
            factor=1.0,
            **kwargs,
        ):
            return random_crystal(
                dim=dim,
                group=sg,
                species=species,
                num_ions=numIons,
                factor=factor,
                **kwargs,
            )
```

Register `callable=_random_crystal_from_registry` instead of `callable=random_crystal`.

- [ ] **Step 4: Add a builder contract guard against callable signature mismatch**

In `tests/contracts/test_builder_contract.py`, where broad `TypeError` is skipped, fail messages containing `"unexpected keyword argument"` or `"required positional argument"`:

```python
        except TypeError as exc:
            message = str(exc)
            if "unexpected keyword argument" in message or "required positional argument" in message:
                raise
            pytest.skip(f"Requires more specific kwargs: {exc}")
```

- [ ] **Step 5: Run builder tests**

Run:

```bash
python -m pytest tests/builders/test_builders_bulk.py tests/contracts/test_builder_contract.py -q
```

Expected: PASS or skip optional-dependency cases according to the local environment; `random_crystal` must not fail with missing `dim`, `group`, or `num_ions`.

- [ ] **Step 6: Commit Task 9**

Run:

```bash
git add matsimpy/builders/_register.py tests/builders/test_builders_bulk.py tests/contracts/test_builder_contract.py
git commit -m "Adapt random crystal registry arguments" -m "Map the public random_crystal builder schema to the callable signature and make builder contract tests fail on schema-callable mismatch." -m "Constraint: Preserve existing public schema names sg and numIons for registry callers." -m "Confidence: medium" -m "Scope-risk: moderate" -m "Tested: python -m pytest tests/builders/test_builders_bulk.py tests/contracts/test_builder_contract.py -q" -m "Not-tested: Real pyxtal random crystal generation when pyxtal is absent."
```

---

### Task 10: Integrated Verification

**Files:**
- No source edits.

- [ ] **Step 1: Run P1-targeted integrated tests**

Run:

```bash
python -m pytest tests/core/test_core_p1_regressions.py tests/calculator/test_vasp_calculator.py tests/calculator/test_lammps_calculator_p1.py tests/ai/test_executor.py tests/ai/test_runtime.py tests/ai/test_storage_skill_isolation.py tests/storage/test_storage_contract_no_maggma.py tests/transformation/test_transformation_regressions.py tests/contracts/test_transformation_contract.py tests/builders/test_builders_bulk.py tests/contracts/test_builder_contract.py -q
```

Expected: PASS, with only optional-dependency skips that are already documented by the relevant test files.

- [ ] **Step 2: Run broader affected suites**

Run:

```bash
python -m pytest tests/core tests/calculator tests/ai tests/storage tests/transformation tests/builders tests/contracts -q
```

Expected: PASS or documented optional-dependency skips. Investigate every failure before finalizing.

- [ ] **Step 3: Confirm no unrelated files changed**

Run:

```bash
git status --short
git log --oneline -10
```

Expected: only intentional commits from Tasks 1-9 are present; no uncommitted changes remain.

- [ ] **Step 4: Write a completion summary**

Create a short summary in the final response listing:

```text
- P1 issues fixed: 9/9
- Commits created: list each Task 1-9 commit hash and subject from `git log --oneline -9`
- Verification: targeted integrated command result; broader affected suite result
- Remaining risk: full repository suite and external binaries if not run
```

Expected: The implementation phase ends with evidence, not assumptions.
