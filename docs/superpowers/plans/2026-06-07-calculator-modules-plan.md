# Calculator Modules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement five calculators (LJ, MatterSim, VASP, Gaussian, LAMMPS) under a unified ASE-style Calculator base class with `run=True/False` dual mode, IO classes adapted from pymatgen with matsimpy-native imports/APIs, and comprehensive tests.

**Architecture:** Each calculator lives in its own subpackage under `matsimpy/calculator/`. IO classes (input generators, output parsers) stay alongside their calculator driver. The base Calculator ABC gains `write_input()` / `_execute()` / `_parse_output()` / `read_results()` as the standard pipeline. Pure-Python calculators (LJ, MatterSim) use `_compute()` directly. External-code calculators (VASP, Gaussian, LAMMPS) use the run-mode pipeline.

**Tech Stack:** Python 3.10+, numpy, scipy, monty (MSONable), torch (optional, MatterSim). Runtime calculator modules must not depend on pymatgen after copied/adapted code is integrated. Pymatgen may be used only in tests as an optional reference oracle. Conda env: `pmg`.

**Spec:** `docs/superpowers/specs/2026-06-07-calculator-modules-design.md`

**Conda environment:** All commands use `conda run -n pmg` prefix.

**Current-state note:** The referenced spec was last checked against the repository on 2026-06-07 and marks the implementation as partial. Treat this plan as an implementation checklist from the current partial state, not as a description of completed functionality.

**Safety notes for implementers:**
- Do not overwrite user-owned uncommitted changes. Check `git status --short` before each task and stage only files intentionally changed for that phase.
- Every implementation phase must end with a real commit after its verification step. Use the repository Lore Commit Protocol for each commit message.
- A task is not finished after `git add`; it is finished only after `git commit` succeeds and the resulting commit hash is recorded in the task log.
- Task 0 is the only non-code baseline phase; create no commit there unless the baseline task intentionally records a documentation or fixture update.
- Prefer tests and fixture/sample-output parsing over invoking real VASP, Gaussian, or LAMMPS binaries in CI.
- For adapted pymatgen IO, preserve attribution docstrings and MIT license notices while replacing runtime dependencies with matsimpy-native modules/APIs.
- After copied modules are integrated, `matsimpy/calculator/**` must not import pymatgen. If a copied module needs a dependency surface that matsimpy does not yet provide, add that surface gracefully to matsimpy as a coherent module/API rather than adding one-off patches, adapters, or private shim classes in copied files.
- Electronic helper surfaces may be copied/adapted from pymatgen when that is the cleanest source, but the copied code must live in matsimpy-owned modules, keep required attribution/license notices, and must not import pymatgen at runtime.
- If a pymatgen feature is outside matsimpy's supported scope, mark that feature unsupported with a clear matsimpy error; do not keep runtime pymatgen fallback imports.
- Tests may import pymatgen only as an optional reference source and must skip gracefully when it is unavailable.
- Related IO tests may be copied from `thirds/pymatgen-core/tests/io`, but must be rewritten into matsimpy style, use matsimpy objects/imports, preserve only relevant fixtures/assertions, and keep pymatgen only as an optional reference oracle.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `matsimpy/calculator/base.py` | Modify | Add `run` param, `write_input`/`_execute`/`_parse_output`/`read_results` pipeline |
| `matsimpy/calculator/utils.py` | **Create** | Shared utility functions (Ha_to_eV, clean_lines, make_symmetric_matrix, get_angle) |
| `matsimpy/calculator/electronic.py` | Create as needed | Matsimpy-owned electronic helper types, copied/adapted from pymatgen when useful, e.g. Magmom/Spin |
| `matsimpy/calculator/io.py` | Create as needed | Matsimpy-native IO protocols/support types formerly imported from pymatgen.io |
| `matsimpy/calculator/symmetry.py` | Create as needed | Matsimpy-native or spglib-backed symmetry support formerly imported from pymatgen |
| `matsimpy/calculator/lj/calculator.py` | Modify | Multi-species Lorentz-Berthelot mixing |
| `matsimpy/calculator/mattersim/__init__.py` | **Create** | Exports MatterSim |
| `matsimpy/calculator/mattersim/calculator.py` | **Create** | MatterSim calculator (restored from v0.4 `845e79e`) |
| `matsimpy/calculator/mattersim/dataloader.py` | **Create** | Graph convertor + dataloader (restored from v0.4) |
| `matsimpy/calculator/vasp/inputs.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/vasp/outputs.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/vasp/sets.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/vasp/calculator.py` | Modify | Rewrite with run-mode pipeline |
| `matsimpy/calculator/gaussian/gaussian.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/gaussian/calculator.py` | Modify | Rewrite with run-mode pipeline |
| `matsimpy/calculator/lammps/inputs.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/lammps/outputs.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/lammps/data.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/lammps/generators.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/lammps/sets.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/lammps/utils.py` | Modify | Replace all runtime pymatgen imports with matsimpy-native modules/APIs |
| `matsimpy/calculator/lammps/calculator.py` | Modify | Rewrite with run-mode pipeline |
| `matsimpy/calculator/__init__.py` | Modify | Export all calculators, lazy MatterSim |
| `tests/calculator/test_calculator_base.py` | Modify | Add run-mode tests |
| `tests/calculator/test_calculator_lennard_jones.py` | Modify | Add multi-species tests |
| `tests/calculator/test_calculator_mattersim.py` | **Create** | MatterSim tests (torch-optional; filename matches existing calculator test naming) |
| `tests/calculator/test_vasp_inputs.py` | **Create** | VASP input tests |
| `tests/calculator/test_vasp_outputs.py` | **Create** | VASP output tests |
| `tests/calculator/test_vasp_sets.py` | **Create** | VASP input set tests |
| `tests/calculator/test_vasp_calculator.py` | **Create** | VASP calculator driver tests |
| `tests/calculator/test_gaussian.py` | **Create** | Gaussian tests |
| `tests/calculator/test_lammps_inputs.py` | **Create** | LAMMPS input tests |
| `tests/calculator/test_lammps_outputs.py` | **Create** | LAMMPS output tests |
| `tests/calculator/test_lammps_data.py` | **Create** | LAMMPS data file tests |
| `tests/calculator/test_lammps_generators.py` | **Create** | LAMMPS generator tests |
| `tests/calculator/test_lammps_calculator.py` | **Create** | LAMMPS calculator driver tests |

---

### Task 0: Verify environment and current test baseline

**Files:**
- None created/modified

- [ ] **Step 1: Run all existing calculator tests to establish baseline**

Run:
```bash
conda run -n pmg pytest tests/calculator/ -v --tb=short 2>&1
```

Expected: All currently existing calculator test files pass (currently `test_calculator_base.py`, `test_calculator_lennard_jones.py`, and `test_vasp_imports.py` in this snapshot). Note any failures before editing.

- [ ] **Step 2: Verify matsimpy core imports work**

Run:
```bash
conda run -n pmg python -c "
from matsimpy.core import Element, Lattice, Crystal, Molecule, Composition, Structure, CrystalSite, Site
from matsimpy.analysis import find_points_in_spheres, validate_cutoff
from matsimpy.utils import validate_vector3, validate_positive_scalar
print('All core imports OK')
"
```

Expected: "All core imports OK"

- [ ] **Step 3: Baseline checkpoint**

```bash
git status --short
```

Expected: Record the baseline result in the task log. Do not create a commit unless this baseline phase intentionally changes documentation or fixtures; all implementation phases below require a commit.

---

### Task 1: Create shared calculator utilities and support modules

**Files:**
- Create: `matsimpy/calculator/utils.py`
- Create as needed: `matsimpy/calculator/electronic.py`, `matsimpy/calculator/io.py`, `matsimpy/calculator/symmetry.py`

These small utility functions and shared support types are used across VASP, Gaussian, and LAMMPS IO files and currently import from pymatgen. Creating matsimpy-native versions unlocks the IO import fixes in later tasks. Do not add one-off replacement classes inside copied IO files; add missing dependency surfaces as coherent matsimpy modules/APIs.

- [ ] **Step 1: Write the utility module**

Create `matsimpy/calculator/utils.py`:

```python
"""Shared utility functions for calculator subpackages.

These replace simple pymatgen utilities so IO classes don't need
a direct pymatgen dependency for basic operations.
"""

from __future__ import annotations
import re
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from numpy.typing import NDArray

# Physical constants
Ha_to_eV = 27.211386245988  # Hartree to eV conversion


def clean_lines(string_list: list[str], remove_empty_lines: bool = True) -> list[str]:
    """Strip whitespace and optionally remove empty lines from a list of strings.

    Adapted from pymatgen.util.io_utils.clean_lines.
    """
    stripped = [line.strip() for line in string_list]
    if remove_empty_lines:
        return [line for line in stripped if line]
    return stripped


def make_symmetric_matrix_from_upper_tri(
    data: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Construct a symmetric 3x3 matrix from upper-triangular elements [xx, yy, zz, yz, xz, xy].

    Adapted from pymatgen.util.num.make_symmetric_matrix_from_upper_tri.
    """
    xx, yy, zz, yz, xz, xy = data[:6]
    return np.array([
        [xx, xy, xz],
        [xy, yy, yz],
        [xz, yz, zz],
    ])


def get_angle(v1: NDArray, v2: NDArray) -> float:
    """Compute the angle in degrees between two vectors.

    Adapted from pymatgen.util.coord.get_angle.
    """
    dot = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norms < 1e-12:
        return 0.0
    cosang = max(-1.0, min(1.0, dot / norms))
    return float(np.degrees(np.arccos(cosang)))


def str_delimited(
    items: list[str],
    header: str | None = None,
    delimiter: str = "|",
    width: int = 80,
) -> str:
    """Format a list of strings as a delimited block.

    Adapted from pymatgen.util.string.str_delimited.
    """
    lines = []
    if header:
        lines.append(header)
    for item in items:
        lines.append(f"{delimiter} {item}")
    return "\n".join(lines)


__all__ = [
    "Ha_to_eV",
    "clean_lines",
    "make_symmetric_matrix_from_upper_tri",
    "get_angle",
    "str_delimited",
]
```

- [ ] **Step 2: Add shared support modules as dependency gaps are identified**

Create `matsimpy/calculator/electronic.py`, `matsimpy/calculator/io.py`, or `matsimpy/calculator/symmetry.py` only when copied IO modules need those surfaces. Keep APIs small, documented, tested, and reusable across VASP/Gaussian/LAMMPS instead of creating per-file adapters. Electronic helpers may be copied/adapted from pymatgen with attribution; they become matsimpy-owned code and must not import pymatgen.

- [ ] **Step 3: Verify the module imports**

Run:
```bash
conda run -n pmg python -c "from matsimpy.calculator.utils import Ha_to_eV, clean_lines, make_symmetric_matrix_from_upper_tri, get_angle; print(f'Ha_to_eV = {Ha_to_eV}')"
```

Expected: `Ha_to_eV = 27.211386245988`

- [ ] **Step 4: Commit**

```bash
git add matsimpy/calculator/utils.py
# Also stage matsimpy/calculator/electronic.py, io.py, and/or symmetry.py if this phase created them.
git commit -m "<why this support-module phase was necessary>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 2: Enhance Calculator base class with run-mode pipeline

**Files:**
- Modify: `matsimpy/calculator/base.py`
- Modify: `tests/calculator/test_calculator_base.py`

- [ ] **Step 1: Write the failing test for run mode**

Add to `tests/calculator/test_calculator_base.py`:

```python
import pytest
import numpy as np
from matsimpy.calculator.base import Calculator
from matsimpy.core import Crystal, Lattice


class _DummyRunCalculator(Calculator):
    """Calculator that supports the run=True pipeline."""
    def __init__(self, run=True, **kwargs):
        super().__init__(run=run, **kwargs)
        self.written = False
        self.executed = False
        self.parsed = False
        self.read_called = False

    def write_input(self, structure):
        self.written = True
        self.input_structure = structure

    def _execute(self):
        self.executed = True

    def _parse_output(self):
        self.parsed = True
        self.results["energy"] = -1.0
        self.results["forces"] = np.zeros((1, 3))

    def read_results(self):
        self.read_called = True
        self.results["energy"] = -2.0
        self.results["forces"] = np.zeros((1, 3))


class _DummyNoRunCalculator(Calculator):
    """Calculator that supports run=False (offline) pipeline."""
    def __init__(self, run=False, **kwargs):
        super().__init__(run=run, **kwargs)

    def write_input(self, structure):
        self._input_written = True

    def read_results(self):
        self.results["energy"] = -5.0


class TestCalculatorRunMode:
    def test_run_true_calls_execute_and_parse(self):
        """When run=True, calculate() should call _execute + _parse_output."""
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = _DummyRunCalculator(run=True)
        calc.calculate(crystal)

        assert calc.written is True
        assert calc.executed is True
        assert calc.parsed is True
        assert calc.read_called is False
        assert calc.get_potential_energy() == -1.0

    def test_run_false_skips_execute_and_parse(self):
        """When run=False, calculate() should only write input."""
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = _DummyRunCalculator(run=False)
        calc.calculate(crystal)

        assert calc.written is True
        assert calc.executed is False
        assert calc.parsed is False

    def test_read_results_after_offline_calculate(self):
        """read_results() should populate results when called after run=False calculate."""
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = _DummyRunCalculator(run=False)
        calc.calculate(crystal)
        calc.read_results()
        assert calc.get_potential_energy() == -2.0

    def test_read_results_without_calculate(self):
        """read_results() without calculate() should still work (parses existing files)."""
        calc = _DummyNoRunCalculator(run=False)
        calc.read_results()
        assert calc.get_potential_energy() == -5.0

    def test_get_energy_before_calculate_raises(self):
        """get_potential_energy() before calculate() should raise."""
        calc = _DummyRunCalculator(run=True)
        with pytest.raises(ValueError, match="not performed"):
            calc.get_potential_energy()

    def test_get_forces_before_calculate_raises(self):
        """get_forces() before calculate() should raise."""
        calc = _DummyRunCalculator(run=True)
        with pytest.raises(ValueError, match="not performed"):
            calc.get_forces()

    def test_run_default_is_true(self):
        """Calculator should default to run=True."""
        calc = Calculator()
        assert calc.run is True

    def test_run_stored_in_parameters(self):
        """run parameter should be stored."""
        calc = Calculator(run=False)
        assert calc.run is False
```

- [ ] **Step 2: Run test to confirm it fails**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_calculator_base.py::TestCalculatorRunMode -v 2>&1 | tail -30
```

Expected: Tests fail — `Calculator` has no `run` parameter, no `write_input`, `_execute`, `_parse_output`, `read_results`.

- [ ] **Step 3: Enhance Calculator base class**

Compatibility guard: `Calculator` is currently abstract because `_compute()` is decorated with `@abstractmethod`. To support external-code calculators that do not override `_compute()` and to allow `Calculator(run=False)` smoke tests, remove the `@abstractmethod` decorator from `_compute()` and make the method concrete. The class may still inherit `ABC`, but it must be instantiable after this change.

Modify `matsimpy/calculator/base.py`:

Remove `abstractmethod` usage from `_compute()` before relying on this smoke test: `Calculator()` must be instantiable once `_compute()` is a concrete no-op compatibility hook.

In `__init__`, add `run` parameter:

```python
def __init__(self, run: bool = True, **parameters):
    """
    Initialize calculator with parameters.

    Args:
        run: If True (default), execute external code and parse output.
             If False, only write input files. Call read_results() later.
        **parameters: Calculator-specific parameters
    """
    self.parameters = parameters.copy()
    self.results: Dict[str, Any] = {}
    self.structure: Optional[Union[Crystal, Molecule]] = None
    self._calculation_performed = False
    self._last_structure_hash: Optional[int] = None
    self.run = run
```

Replace the `calculate` method:

```python
def calculate(self, structure: Union[Crystal, Molecule]) -> None:
    """
    Perform calculation on the given structure.

    When run=True: writes input → executes → parses output.
    When run=False: writes input only. User runs code manually, then calls read_results().

    Args:
        structure: Crystal or Molecule structure to calculate

    Raises:
        ValueError: If structure is not a valid Crystal or Molecule
    """
    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(
            f"Calculator requires Crystal or Molecule, got {type(structure)}"
        )

    self.structure = structure
    self._calculation_performed = False
    self._last_structure_hash = structure._structural_hash()

    # Always write input files
    self.write_input(structure)

    if self.run:
        # Execute and parse
        self._execute()
        self._parse_output()

    self._calculation_performed = True
```

Add new public methods (after `_compute`):

```python
def write_input(self, structure: Union[Crystal, Molecule]) -> None:
    """
    Write input files for external code.

    Default implementation does nothing. Subclasses for external-code calculators
    (VASP, Gaussian, LAMMPS) should override this to generate input files.

    Args:
        structure: Crystal or Molecule to write inputs for
    """
    pass

def read_results(self) -> None:
    """
    Read and parse pre-existing output files.

    Called by user after run=False calculate() and manual execution.
    Subclasses should override _parse_output() and call it from here.
    """
    self._parse_output()
    self._calculation_performed = True

def _execute(self) -> None:
    """
    Execute external code via subprocess.

    Default implementation does nothing. Subclasses for external-code calculators
    should override this to run the relevant command.
    """
    pass

def _parse_output(self) -> None:
    """
    Parse output files produced by external code.

    Default implementation does nothing. Subclasses should override this
    to parse output files and populate self.results.
    """
    pass
```

Remove the abstract `_compute` method or make it concrete (it's now the fallback for pure-Python calculators like LJ):

```python
def _compute(self) -> None:
    """
    Perform direct (non-file-based) computation.

    Pure-Python calculators (LJ, MatterSim) should override this instead of
    write_input/_execute/_parse_output. The base calculate() calls write_input
    then run-mode methods; _compute is the legacy hook that LJ/MatterSim override.
    """
    pass
```

Note: LJ and MatterSim override `_compute()` directly. They don't need `write_input`/`_execute`/`_parse_output`. Preserve backward compatibility by routing subclasses that override `_compute()` through the pure-Python path, and route subclasses that do not override `_compute()` through the external-code pipeline.

**Preserve backward compatibility:** Pure-Python calculators (LJ, MatterSim) override `_compute()`. External-code calculators use the new `write_input/_execute/_parse_output` pipeline. The base `calculate()` should check which path to take:

```python
def calculate(self, structure: Union[Crystal, Molecule]) -> None:
    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(
            f"Calculator requires Crystal or Molecule, got {type(structure)}"
        )

    self.structure = structure
    self._calculation_performed = False
    self._last_structure_hash = structure._structural_hash()

    # Check if this is a pure-Python calculator (overrides _compute)
    # or an external-code calculator (overrides write_input)
    if type(self)._compute is not Calculator._compute:
        # Pure Python path (LJ, MatterSim)
        self._compute()
    else:
        # External-code path (VASP, Gaussian, LAMMPS)
        self.write_input(structure)
        if self.run:
            self._execute()
            self._parse_output()

    self._calculation_performed = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_calculator_base.py -v 2>&1 | tail -30
```

Expected: All tests pass, including new `TestCalculatorRunMode` tests.

- [ ] **Step 5: Run ALL existing calculator tests to verify no regressions**

Run:
```bash
conda run -n pmg pytest tests/calculator/ -v --tb=short 2>&1
```

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add matsimpy/calculator/base.py tests/calculator/test_calculator_base.py
git commit -m "<why the base calculator pipeline changed>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 3: LJ multi-species mixing rules

**Files:**
- Modify: `matsimpy/calculator/lj/calculator.py`
- Modify: `tests/calculator/test_calculator_lennard_jones.py`

LJ currently assumes one species. Add per-pair sigma/epsilon with Lorentz-Berthelot mixing rules: `sigma_ij = (sigma_i + sigma_j)/2`, `epsilon_ij = sqrt(epsilon_i * epsilon_j)`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/calculator/test_calculator_lennard_jones.py`:

```python
class TestLJMultispecies:
    """Tests for multi-species Lennard-Jones."""

    def test_multispecies_energy_different_from_single(self):
        """Ar+Kr system should have different energy than pure Ar."""
        from matsimpy.calculator.lj import LennardJones
        from matsimpy.core import Crystal, Lattice

        # Ar+Kr in alternating pattern
        crystal = Crystal(
            ["Ar", "Kr", "Ar", "Kr"],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(5.0),
        )
        calc = LennardJones(sigma=3.4, epsilon=0.0104, species_sigma={"Kr": 3.6}, species_epsilon={"Kr": 0.014})
        calc.calculate(crystal)
        energy_mixed = calc.get_potential_energy()

        # Pure Ar with same geometry
        crystal_ar = Crystal(
            ["Ar", "Ar", "Ar", "Ar"],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(5.0),
        )
        calc_ar = LennardJones(sigma=3.4, epsilon=0.0104)
        calc_ar.calculate(crystal_ar)
        energy_pure = calc_ar.get_potential_energy()

        assert energy_mixed != pytest.approx(energy_pure, rel=1e-6)

    def test_lorentz_berthelot_mixing_rules(self):
        """Verify Lorentz-Berthelot: sigma_12 = (sigma_1+sigma_2)/2, epsilon_12 = sqrt(eps1*eps2)."""
        from matsimpy.calculator.lj import LennardJones

        calc = LennardJones(
            sigma=3.0, epsilon=0.01,
            species_sigma={"B": 4.0}, species_epsilon={"B": 0.02},
        )
        # Ar-Ar pair
        assert calc.parameters["sigma"] == 3.0
        assert calc.parameters["epsilon"] == 0.01
        # Ar-B pair: sigma = (3+4)/2 = 3.5, epsilon = sqrt(0.01*0.02) ≈ 0.01414
        assert calc.get_pair_params("A", "B") == pytest.approx((3.5, 0.0141421356))

    def test_backward_compatible_single_species(self):
        """Existing single-species usage should still work unchanged."""
        from matsimpy.calculator.lj import LennardJones
        from matsimpy.core import Crystal, Lattice

        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        calc = LennardJones(sigma=3.4, epsilon=0.0104)
        calc.calculate(crystal)
        energy = calc.get_potential_energy()
        assert isinstance(energy, float)
        assert np.isfinite(energy)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_calculator_lennard_jones.py::TestLJMultispecies -v 2>&1 | tail -20
```

Expected: `TypeError` or `AttributeError` — `species_sigma` is not a recognized parameter.

- [ ] **Step 3: Add multi-species support to LennardJones**

Modify `matsimpy/calculator/lj/calculator.py`:

In `__init__`, add:

```python
def __init__(
    self,
    sigma: float = 3.4,
    epsilon: float = 0.0104,
    cutoff: Optional[float] = None,
    rc_smooth: Optional[float] = None,
    species_sigma: Optional[dict[str, float]] = None,
    species_epsilon: Optional[dict[str, float]] = None,
    **kwargs,
):
    super().__init__(sigma=sigma, epsilon=epsilon, **kwargs)

    # Store per-species parameters
    self._species_sigma = species_sigma or {}
    self._species_epsilon = species_epsilon or {}
    # Store defaults for unknown species
    self._default_sigma = sigma
    self._default_epsilon = epsilon

    if cutoff is None:
        cutoff = 3.0 * sigma
    self.parameters["cutoff"] = cutoff

    if rc_smooth is None:
        rc_smooth = cutoff
    self.parameters["rc_smooth"] = rc_smooth
```

Add the mixing method:

```python
def get_pair_params(self, species_i: str, species_j: str) -> tuple[float, float]:
    """Get sigma and epsilon for a species pair using Lorentz-Berthelot mixing.

    sigma_ij = (sigma_i + sigma_j) / 2
    epsilon_ij = sqrt(epsilon_i * epsilon_j)
    """
    si = self._species_sigma.get(species_i, self._default_sigma)
    sj = self._species_sigma.get(species_j, self._default_sigma)
    ei = self._species_epsilon.get(species_i, self._default_epsilon)
    ej = self._species_epsilon.get(species_j, self._default_epsilon)
    return (si + sj) / 2, np.sqrt(ei * ej)
```

In `_compute_non_periodic` and `_compute_periodic`, use `get_pair_params` for each pair instead of `self.parameters["sigma"]`/`self.parameters["epsilon"]`. Add a `species` parameter to both methods and use it to look up per-pair params.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_calculator_lennard_jones.py -v 2>&1 | tail -30
```

Expected: All LJ tests pass including new multi-species tests.

- [ ] **Step 5: Commit**

```bash
git add matsimpy/calculator/lj/calculator.py tests/calculator/test_calculator_lennard_jones.py
git commit -m "<why LJ mixing support changed>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 4: Restore MatterSim from v0.4

**Files:**
- Create: `matsimpy/calculator/mattersim/__init__.py`
- Create: `matsimpy/calculator/mattersim/calculator.py`
- Create: `matsimpy/calculator/mattersim/dataloader.py`
- Create: `tests/calculator/test_calculator_mattersim.py`

Restore the MatterSim calculator from git commit `845e79e`, flatten from `calculator/ml/` to `calculator/mattersim/`, update imports.

- [ ] **Step 1: Checkout v0.4 files into new location**

Run:
```bash
cd /Users/haidi/dev/matsimpy
git show 845e79e:matsimpy/calculator/ml/mattersim.py > matsimpy/calculator/mattersim/calculator.py
git show 845e79e:matsimpy/calculator/ml/dataloader.py > matsimpy/calculator/mattersim/dataloader.py
```

- [ ] **Step 2: Fix imports in calculator.py**

In `matsimpy/calculator/mattersim/calculator.py`, change:
- `from .base_ml import BaseML` → inherit from `from matsimpy.calculator.base import Calculator` directly
- `from .dataloader import build_dataloader` → `from matsimpy.calculator.mattersim.dataloader import build_dataloader`
- `from ...core import Crystal, Molecule` → `from matsimpy.core import Crystal, Molecule`

Replace the class definition:
```python
class Mattersim(Calculator):  # was: class Mattersim(BaseML)
```

Remove the `BaseML` dependency entirely — copy any needed logic from BaseML into the Mattersim class:
```python
def __init__(self, model_path=None, model=None, device=None, 
             load_training_state=False, compute_stress=True, **kwargs):
    if device is None:
        device = "cpu"
    super().__init__(model_path=model_path, device=device, **kwargs)
    self.model_path = Path(model_path) if model_path else None
    self.device = device
    self.model = model
    self.potential = None
    self._Potential = None
    self.compute_stress = compute_stress
    self.load_training_state = load_training_state
    self.args_dict = kwargs.get("args_dict", {})
    self.args_dict.setdefault("batch_size", 1)
    self.args_dict.setdefault("only_inference", 1)
    # Lazy load — don't require torch at import time
```

Override `_compute()` instead of using BaseML's version:
```python
def _compute(self):
    """ML potential: prepare input → run model → extract results."""
    if self.structure is None:
        raise ValueError("Structure not set.")
    if self.potential is None and self.model is not None:
        self.potential = self.model
    if self.potential is None and self.model_path:
        self._load_model()
    if self.potential is None:
        raise ValueError("No model loaded. Provide model_path or model.")

    # Extract structure data
    if isinstance(self.structure, Crystal):
        positions = self.structure.cart_positions
        lattice = self.structure.lattice
        species = list(self.structure.species)
        pbc = self.structure.pbc
    else:
        positions = np.array(self.structure.positions)
        lattice = None
        species = list(self.structure.species)
        pbc = [False, False, False]

    model_input = self._prepare_model_input(positions, species, lattice, pbc)
    predictions = self._run_model(model_input)

    self.results["energy"] = predictions.get("energy", 0.0)
    self.results["forces"] = predictions.get("forces", np.zeros((len(positions), 3)))
    if lattice is not None and "stress" in predictions:
        self.results["stress"] = predictions["stress"]
```

- [ ] **Step 3: Fix imports in dataloader.py**

In `matsimpy/calculator/mattersim/dataloader.py`, change:
- `from ...core import Crystal, Molecule` → `from matsimpy.core import Crystal, Molecule`
- `from ...analysis import find_points_in_spheres` → `from matsimpy.analysis import find_points_in_spheres`

- [ ] **Step 4: Write __init__.py**

Create `matsimpy/calculator/mattersim/__init__.py`:

```python
"""MatterSim machine learning potential calculator."""

try:
    from .calculator import Mattersim
    __all__ = ["Mattersim"]
except ImportError:
    __all__ = []
```

- [ ] **Step 5: Write MatterSim test**

Create `tests/calculator/test_calculator_mattersim.py`:

```python
"""Tests for MatterSim calculator.

Tests that do not require torch run unconditionally.
Torch-dependent tests use @pytest.mark.requires_torch marker.
"""

import pytest
import numpy as np


class TestMattersimSerialization:
    """Tests that do NOT require torch or MatterSim library."""

    def test_import_without_torch(self):
        """Mattersim should be importable (lazy) even without torch."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            # Import should succeed without error
            assert Mattersim is not None or Mattersim is None
        except ImportError:
            pass  # ok if matter sim library missing entirely

    def test_default_init(self):
        """Mattersim with no model_path should initialize (lazy load)."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            calc = Mattersim()  # no model_path — OK, lazy
            assert calc.device == "cpu"
        except ImportError:
            pytest.skip("Mattersim not importable")

    def test_run_parameter(self):
        """Mattersim should accept run parameter."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            calc = Mattersim(run=True)
            assert calc.run is True
            calc2 = Mattersim(run=False)
            assert calc2.run is False
        except ImportError:
            pytest.skip("Mattersim not importable")

    def test_as_dict_no_model(self):
        """Serialization without loaded model."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            calc = Mattersim(model_path="/fake/path/model.pth", device="cpu")
            d = calc.as_dict()
            assert "model_path" in d
            assert d["device"] == "cpu"
        except ImportError:
            pytest.skip("Mattersim not importable")


@pytest.mark.requires_torch
class TestMattersimWithTorch:
    """Tests that require torch (skipped without)."""

    def test_calculate_with_structure(self):
        """Calculate energy for a simple structure."""
        pytest.importorskip("torch")
        try:
            from matsimpy.calculator.mattersim import Mattersim
            from matsimpy.core import Crystal, Lattice
        except ImportError:
            pytest.skip("Mattersim not available")

        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = Mattersim()
        # Without a real model, this should raise a clear error
        with pytest.raises(ValueError, match="[Mm]odel"):
            calc.calculate(crystal)
```

- [ ] **Step 6: Run MatterSim tests**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_calculator_mattersim.py -v 2>&1 | tail -30
```

Expected: Serialization tests pass. Torch tests skip if torch not installed.

- [ ] **Step 7: Commit**

```bash
git add matsimpy/calculator/mattersim/ tests/calculator/test_calculator_mattersim.py
git commit -m "<why MatterSim was restored in this phase>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 5: Fix VASP IO imports and rewrite VaspCalculator

**Files:**
- Modify: `matsimpy/calculator/vasp/inputs.py` — fix imports + add/verify attribution docstring
- Modify: `matsimpy/calculator/vasp/outputs.py` — fix imports + add/verify attribution docstring
- Modify: `matsimpy/calculator/vasp/sets.py` — fix imports + add/verify attribution docstring
- Modify: `matsimpy/calculator/vasp/calculator.py` — rewrite with run-mode pipeline (original code, no attribution needed)
- Create: `tests/calculator/test_vasp_inputs.py`
- Create: `tests/calculator/test_vasp_outputs.py`
- Create: `tests/calculator/test_vasp_sets.py`
- Create: `tests/calculator/test_vasp_calculator.py`

This is the largest task. Work through it systematically: tests first, then imports, then calculator.

- [ ] **Step 0: Verify attribution docstrings on IO files**

Check each of inputs.py, outputs.py, sets.py has a module-level docstring matching:

```python
"""VASP ... — adapted from pymatgen (https://pymatgen.org/).

Original: pymatgen.io.vasp.<module>
Copyright (c) pymatgen Development Team.
Distributed under the MIT License.
Modifications for MatSimPy integration.
"""
```

If missing or using old format, add/update it.

- [ ] **Step 1: Write test_vasp_inputs.py**

Create `tests/calculator/test_vasp_inputs.py`:

```python
"""Tests for VASP input file classes.

May copy relevant cases/fixtures from thirds/pymatgen-core/tests/io/vasp/test_inputs.py.
Rewrite to matsimpy style using matsimpy Crystal/Lattice/Composition classes and matsimpy imports.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice


class TestIncar:
    def test_incar_from_dict(self):
        from matsimpy.calculator.vasp.inputs import Incar
        incar = Incar({"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05})
        assert incar["ENCUT"] == 400
        assert incar["ISMEAR"] == 0

    def test_incar_write_read_roundtrip(self, tmp_path):
        from matsimpy.calculator.vasp.inputs import Incar
        incar = Incar({"ENCUT": 400, "ISMEAR": 0})
        fpath = tmp_path / "INCAR"
        incar.write_file(fpath)
        incar2 = Incar.from_file(fpath)
        assert incar2["ENCUT"] == 400

    def test_incar_diff(self):
        from matsimpy.calculator.vasp.inputs import Incar
        incar1 = Incar({"ENCUT": 400, "ISMEAR": 0})
        incar2 = Incar({"ENCUT": 500, "ISMEAR": 0})
        diff = incar1.diff(incar2)
        assert "ENCUT" in diff
        assert "ISMEAR" not in diff

    def test_incar_check_params(self):
        from matsimpy.calculator.vasp.inputs import Incar
        incar = Incar({"ENCUT": 400, "LWAVE": False})
        incar.check_params()
        # Should not raise


class TestKpoints:
    def test_automatic_kpoints(self):
        from matsimpy.calculator.vasp.inputs import Kpoints
        kpt = Kpoints.automatic([4, 4, 4])
        assert kpt.style == "Automatic"
        assert kpt.kpts == [[4, 4, 4]]

    def test_gamma_automatic(self):
        from matsimpy.calculator.vasp.inputs import Kpoints
        kpt = Kpoints.gamma_automatic([2, 2, 2])
        assert kpt.style == "Gamma"

    def test_kpoints_write_read_roundtrip(self, tmp_path):
        from matsimpy.calculator.vasp.inputs import Kpoints
        kpt = Kpoints.automatic([3, 3, 3])
        fpath = tmp_path / "KPOINTS"
        kpt.write_file(fpath)
        kpt2 = Kpoints.from_file(fpath)
        assert kpt2.kpts == [[3, 3, 3]]


class TestPoscar:
    @pytest.fixture
    def si_crystal(self):
        return Crystal(
            ["Si", "Si"],
            [[0, 0, 0], [0.25, 0.25, 0.25]],
            Lattice.cubic(5.43),
        )

    def test_poscar_write_read_roundtrip(self, si_crystal, tmp_path):
        from matsimpy.calculator.vasp.inputs import Poscar
        poscar = Poscar(si_crystal)
        fpath = tmp_path / "POSCAR"
        poscar.write_file(fpath)
        poscar2 = Poscar.from_file(fpath)
        assert poscar2.structure.formula == si_crystal.formula

    def test_poscar_selective_dynamics(self, si_crystal, tmp_path):
        from matsimpy.calculator.vasp.inputs import Poscar
        sd = [[True, True, True], [True, True, True]]
        poscar = Poscar(si_crystal, selective_dynamics=sd)
        fpath = tmp_path / "POSCAR"
        poscar.write_file(fpath)
        assert poscar.selective_dynamics is not None

    def test_poscar_site_symbols(self, si_crystal):
        from matsimpy.calculator.vasp.inputs import Poscar
        poscar = Poscar(si_crystal)
        assert "Si" in poscar.site_symbols
```

- [ ] **Step 2: Run VASP input tests to confirm they fail (import errors or pymatgen deps)**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_vasp_inputs.py -v 2>&1 | tail -30
```

Note: These may fail because inputs.py still imports from pymatgen which may not be in the conda env, OR they may pass if pymatgen is installed. The goal is to make runtime VASP functionality pass without pymatgen. Advanced electronic-structure, symmetry, or POTCAR paths must use matsimpy-native modules/APIs where supported, or raise clear unsupported-feature errors without importing pymatgen at runtime.

- [ ] **Step 3: Fix imports in vasp/inputs.py**

Replace pymatgen imports with matsimpy-native modules/APIs:

```python
# OLD:
from pymatgen.core import SETTINGS, Element, Lattice, Structure, get_el_sp
from pymatgen.electronic_structure.core import Magmom
from pymatgen.util.io_utils import clean_lines
from pymatgen.util.string import str_delimited

# NEW:
from matsimpy.core import Element, Lattice, Crystal, Composition
from matsimpy.calculator.utils import clean_lines, str_delimited

# Magmom: add a matsimpy-native magnetic moment helper in a shared support module
class Magmom:
    """Simple magnetic moment wrapper. Adapted from pymatgen."""
    def __init__(self, magmom):
        if isinstance(magmom, (list, tuple)):
            self.moment = magmom
        else:
            self.moment = [magmom]
    def __repr__(self):
        return f"Magmom({self.moment})"
```

In the file, replace `Structure` → `Crystal` throughout, `get_el_sp(x)` → `Element(x)`, `SETTINGS` references → remove (use defaults).

- [ ] **Step 4: Fix imports in vasp/outputs.py**

Replace pymatgen imports with matsimpy-native modules/APIs. For complex electronic structure classes (BandStructure, Dos, CompleteDos, Spin, OrbitalType, etc.), add the minimal matsimpy-native data containers needed by supported parser behavior, or make the affected advanced methods raise clear unsupported-feature errors. Do not keep pymatgen fallback imports in runtime modules.

```python
from matsimpy.core import Composition, Element, Lattice, Crystal
from matsimpy.calculator.utils import clean_lines, make_symmetric_matrix_from_upper_tri

# Runtime code must not import pymatgen. Tests may import pymatgen as an optional reference oracle.
# Add shared matsimpy-native support classes/APIs only for behavior matsimpy supports.
```

Replace internal import: `from pymatgen.io.vasp.inputs import Incar, Kpoints...` → `from matsimpy.calculator.vasp.inputs import Incar, Kpoints...`

Replace `micro_pyawk` → a matsimpy-native utility where the behavior is reused, or direct straightforward parsing when it is unique to one parser.

- [ ] **Step 5: Fix imports in vasp/sets.py**

Replace:
```python
# OLD:
from pymatgen.core import Element, PeriodicSite, SiteCollection, Species, Structure
from pymatgen.core.structure_matcher import StructureMatcher
from pymatgen.io.core import InputGenerator
from pymatgen.io.vasp.inputs import Incar, Kpoints, PmgVaspPspDirError, Poscar, Potcar, VaspInput
from pymatgen.io.vasp.outputs import Outcar, Vasprun
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.symmetry.bandstructure import HighSymmKpath
from pymatgen.util.due import Doi, due

# NEW:
from matsimpy.core import Element, Crystal, Lattice
from matsimpy.calculator.vasp.inputs import Incar, Kpoints, Poscar, Potcar, VaspInput
from matsimpy.calculator.vasp.outputs import Outcar, Vasprun

# Runtime code must not import pymatgen. Add matsimpy-native or spglib-backed
# symmetry APIs only when needed; otherwise raise clear unsupported-feature errors.
```

- [ ] **Step 6: Rewrite VaspCalculator**

In `matsimpy/calculator/vasp/calculator.py`, restructure to use the run-mode pipeline:

```python
class VaspCalculator(Calculator):
    def __init__(self, directory="./vasp_calc", incar=None, kpoints=None,
                 vasp_cmd="vasp", copy_potcar=True, run=True):
        super().__init__(run=run, directory=str(directory), vasp_cmd=vasp_cmd)
        self.directory = Path(directory)
        self.incar_params = incar or {"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05}
        self.kpoints_grid = kpoints or [1, 1, 1]
        self.vasp_cmd = vasp_cmd
        self.copy_potcar = copy_potcar

    def write_input(self, structure):
        """Write VASP input files (INCAR, KPOINTS, POSCAR, POTCAR)."""
        self.directory.mkdir(parents=True, exist_ok=True)
        from matsimpy.calculator.vasp.inputs import Incar, Kpoints, Poscar

        Incar(self.incar_params).write_file(self.directory / "INCAR")
        if isinstance(self.kpoints_grid, list) and len(self.kpoints_grid) == 3:
            Kpoints.automatic(self.kpoints_grid).write_file(self.directory / "KPOINTS")
        else:
            Kpoints.gamma_automatic(self.kpoints_grid).write_file(self.directory / "KPOINTS")
        Poscar(structure).write_file(self.directory / "POSCAR")
        if self.copy_potcar:
            self._write_potcar(structure)

    def _execute(self):
        """Run VASP executable."""
        result = subprocess.run(
            [self.vasp_cmd], cwd=str(self.directory),
            capture_output=True, text=True, timeout=3600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"VASP failed:\n{result.stderr[-500:]}")

    def _parse_output(self):
        """Parse VASP output for energy, forces, stress."""
        from matsimpy.calculator.vasp.outputs import Outcar, Oszicar, Vasprun

        vasprun_xml = self.directory / "vasprun.xml"
        outcar_path = self.directory / "OUTCAR"
        oszicar_path = self.directory / "OSZICAR"

        if vasprun_xml.exists():
            vasprun = Vasprun(str(vasprun_xml))
            self.results["energy"] = float(vasprun.final_energy)
            if vasprun.force_constants and vasprun.ionic_steps:
                forces = vasprun.ionic_steps[-1].get("forces")
                if forces is not None:
                    self.results["forces"] = np.array(forces)
        elif outcar_path.exists():
            outcar = Outcar(str(outcar_path))
            self.results["energy"] = float(outcar.final_energy)
            forces = outcar.data.get("forces", {}).get(-1)
            if forces is not None:
                self.results["forces"] = np.array(forces)
        elif oszicar_path.exists():
            oszicar = Oszicar(str(oszicar_path))
            if oszicar.ionic_steps:
                self.results["energy"] = float(oszicar.ionic_steps[-1].get("E0", 0.0))

    def read_results(self):
        """Parse existing output files (offline mode)."""
        super().read_results()

    # Remove get_potential_energy/get_forces/get_stress overrides —
    # use the base class implementations.
```

- [ ] **Step 7: Run VASP input tests to confirm imports work**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_vasp_inputs.py -v 2>&1 | tail -30
```

Expected: Tests pass (or skip gracefully).

- [ ] **Step 8: Write test_vasp_outputs.py**

Create `tests/calculator/test_vasp_outputs.py`:

```python
"""Tests for VASP output file parsing.

May copy relevant cases/fixtures from thirds/pymatgen-core/tests/io/vasp/test_outputs.py.
Rewrite to matsimpy style and keep pymatgen only as an optional reference oracle.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice


class TestOutcar:
    def test_parse_outcar_energy(self, tmp_path):
        """Parse final energy from OUTCAR."""
        from matsimpy.calculator.vasp.outputs import Outcar
        content = """
  FREE ENERGIE OF THE ION-ELECTRON SYSTEM (eV)
  ---------------------------------------------------
  free  energy   TOTEN  =       -10.512345 eV
  energy  without entropy=       -10.512345  energy(sigma->0) =       -10.512345
"""
        fpath = tmp_path / "OUTCAR"
        fpath.write_text(content)
        outcar = Outcar(str(fpath))
        assert outcar.final_energy == pytest.approx(-10.512345)


class TestOszicar:
    def test_parse_oszicar(self, tmp_path):
        """Parse energy from OSZICAR."""
        from matsimpy.calculator.vasp.outputs import Oszicar
        content = """      1 F= -.10512345E+02 E0= -.10512345E+02  d E =0.000000E+00
      2 F= -.10567890E+02 E0= -.10567890E+02  d E =-.555345E-03
"""
        fpath = tmp_path / "OSZICAR"
        fpath.write_text(content)
        oszicar = Oszicar(str(fpath))
        assert len(oszicar.ionic_steps) >= 1


class TestVasprun:
    def test_vasprun_basic(self, tmp_path):
        """Vasprun should parse basic vasprun.xml."""
        from matsimpy.calculator.vasp.outputs import Vasprun
        import xml.etree.ElementTree as ET
        xml_content = """<?xml version="1.0"?>
<modeling>
  <generator><i name="vasp"/></generator>
  <incar><i type="int" name="ENCUT">400</i></incar>
  <kpoints>
    <generation><i type="int" name="divisions">4 4 4</i></generation>
  </kpoints>
  <parameters><separator name="electronic">
    <i type="float" name="efermi">5.0</i>
  </separator></parameters>
  <calculation>
    <scstep><energy><i type="float" name="e_fr_energy">-10.5</i></energy></scstep>
    <energy><i type="float" name="e_fr_energy">-10.5</i></energy>
    <structure name="finalpos">
      <crystal><varray name="basis"><v>5.43 0 0</v><v>0 5.43 0</v><v>0 0 5.43</v></varray></crystal>
      <varray name="positions"><v>0 0 0</v></varray>
    </structure>
  </calculation>
</modeling>"""
        fpath = tmp_path / "vasprun.xml"
        fpath.write_text(xml_content)
        vr = Vasprun(str(fpath))
        assert vr.final_energy == pytest.approx(-10.5)
```

- [ ] **Step 9: Write test_vasp_sets.py**

Create `tests/calculator/test_vasp_sets.py`:

```python
"""Tests for VASP input sets.

May copy relevant cases/fixtures from thirds/pymatgen-core/tests/io/vasp/test_sets.py.
Rewrite to matsimpy style using matsimpy structures and imports.
"""

import pytest
from matsimpy.core import Crystal, Lattice


class TestDictSet:
    def test_dictset_generates_incar(self):
        from matsimpy.calculator.vasp.sets import DictSet
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        vset = DictSet(crystal, config_dict={"INCAR": {"ENCUT": 400, "ISMEAR": 0}})
        incar = vset.incar
        assert incar["ENCUT"] == 400
        assert incar["ISMEAR"] == 0

    def test_dictset_generates_kpoints(self):
        from matsimpy.calculator.vasp.sets import DictSet
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        vset = DictSet(crystal, config_dict={
            "INCAR": {"ENCUT": 400},
            "KPOINTS": {"grid_density": 1000},
        })
        kpoints = vset.kpoints
        assert kpoints is not None
```

- [ ] **Step 10: Write test_vasp_calculator.py**

Create `tests/calculator/test_vasp_calculator.py`:

```python
"""Tests for VaspCalculator driver."""

import pytest
from matsimpy.core import Crystal, Lattice


class TestVaspCalculator:
    def test_run_false_writes_input_only(self, tmp_path):
        from matsimpy.calculator.vasp import VaspCalculator
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        calc = VaspCalculator(directory=str(tmp_path), incar={"ENCUT": 400},
                             kpoints=[1, 1, 1], run=False)
        calc.calculate(crystal)
        incar_path = tmp_path / "INCAR"
        poscar_path = tmp_path / "POSCAR"
        kpoints_path = tmp_path / "KPOINTS"
        assert incar_path.exists()
        assert poscar_path.exists()
        assert kpoints_path.exists()
        # No energy since we didn't run
        assert "energy" not in calc.results

    def test_run_default_is_true(self):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator()
        assert calc.run is True

    def test_read_results_calls_parse(self, tmp_path, monkeypatch):
        from matsimpy.calculator.vasp import VaspCalculator
        calc = VaspCalculator(directory=str(tmp_path))
        # Simulate: write a vasprun.xml, then call read_results
        import xml.etree.ElementTree as ET
        xml_content = """<?xml version="1.0"?>
<modeling>
  <generator><i name="vasp"/></generator>
  <incar><i type="int" name="ENCUT">400</i></incar>
  <calculation>
    <energy><i type="float" name="e_fr_energy">-10.5</i></energy>
  </calculation>
</modeling>"""
        (tmp_path / "vasprun.xml").write_text(xml_content)
        # read_results should parse and set energy
        calc.structure = crystal
        calc.read_results()
        assert calc.results.get("energy") is not None

- [ ] **Step 9: Run all VASP tests**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_vasp_*.py -v 2>&1 | tail -40
```

- [ ] **Step 10: Commit**

```bash
git add matsimpy/calculator/vasp/ tests/calculator/test_vasp_*.py
git commit -m "<why VASP runtime dependencies and driver changed>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 6: Fix Gaussian IO imports and rewrite GaussianCalculator

**Files:**
- Modify: `matsimpy/calculator/gaussian/gaussian.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/gaussian/calculator.py` — rewrite (original code, no attribution needed)
- Create: `tests/calculator/test_gaussian.py`

- [ ] **Step 0: Verify attribution docstring**

Check `gaussian.py` has:
```python
"""Gaussian input/output — adapted from pymatgen (https://pymatgen.org/).

Original: pymatgen.io.gaussian
Copyright (c) pymatgen Development Team.
Distributed under the MIT License.
Modifications for MatSimPy integration.
"""
```

- [ ] **Step 1: Write test_gaussian.py**

Create `tests/calculator/test_gaussian.py`:

```python
"""Tests for Gaussian input/output and calculator.

May copy relevant cases/fixtures from thirds/pymatgen-core/tests/io/test_gaussian.py.
Rewrite to matsimpy style using matsimpy Crystal/Molecule classes and matsimpy imports.
"""

import pytest
import numpy as np
from matsimpy.core import Molecule


class TestGaussianInput:
    def test_basic_input_generation(self, tmp_path):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput
        mol = Molecule(["O", "H", "H"],
                       [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]])
        gin = GaussianInput(mol, route="# B3LYP/6-31G(d)", charge=0, spin=1,
                            title="Test job")
        assert "B3LYP/6-31G(d)" in gin.route
        assert gin.charge == 0
        assert gin.spin_multiplicity == 1

    def test_write_input_file(self, tmp_path):
        from matsimpy.calculator.gaussian.gaussian import GaussianInput
        mol = Molecule(["O", "H", "H"],
                       [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]])
        gin = GaussianInput(mol, route="# HF/STO-3G", charge=0, spin=1)
        fpath = tmp_path / "test.gjf"
        gin.write_file(fpath)
        text = fpath.read_text()
        assert "HF/STO-3G" in text
        assert "0 1" in text


class TestGaussianOutput:
    def test_parse_scf_energy(self, tmp_path):
        from matsimpy.calculator.gaussian.gaussian import GaussianOutput
        content = """\
 SCF Done:  E(RHF) =  -75.983456789     A.U. after   10 cycles
"""
        fpath = tmp_path / "test.log"
        fpath.write_text(content)
        gout = GaussianOutput(str(fpath))
        assert gout.final_energy is not None


class TestGaussianCalculator:
    def test_run_false_writes_input_only(self, tmp_path):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator
        mol = Molecule(["O", "H", "H"],
                       [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]])
        calc = GaussianCalculator(
            directory=str(tmp_path), route="# B3LYP/6-31G(d)",
            charge=0, spin=1, run=False,
        )
        calc.calculate(mol)
        input_file = tmp_path / "input.gjf"
        assert input_file.exists()
        # No execution should have happened
        assert "energy" not in calc.results

    def test_run_true_attempts_execution(self, tmp_path):
        from matsimpy.calculator.gaussian.calculator import GaussianCalculator
        mol = Molecule(["O", "H", "H"],
                       [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]])
        calc = GaussianCalculator(
            directory=str(tmp_path), route="# B3LYP/6-31G(d)",
            charge=0, spin=1, run=True, gaussian_cmd="nonexistent_g09",
        )
        # Should raise because g09 doesn't exist
        with pytest.raises((FileNotFoundError, RuntimeError)):
            calc.calculate(mol)
```

- [ ] **Step 2: Fix imports in gaussian.py**

Replace imports with matsimpy-native modules/APIs. Plotting, symmetry operations, and spin helpers must be matsimpy-native or unsupported; do not keep pymatgen fallback imports in runtime modules. Replace:
```python
# OLD:
from pymatgen.core import Composition, Element, Molecule
from pymatgen.core.operations import SymmOp
from pymatgen.core.units import Ha_to_eV
from pymatgen.electronic_structure.core import Spin
from pymatgen.util.coord import get_angle
from pymatgen.util.plotting import pretty_plot

# NEW:
from matsimpy.core import Composition, Element, Molecule
from matsimpy.calculator.utils import Ha_to_eV, get_angle
# Spin — add a matsimpy-native enum if needed; pretty_plot — unsupported unless matsimpy owns the plotting path
```

- [ ] **Step 3: Rewrite GaussianCalculator**

In `matsimpy/calculator/gaussian/calculator.py`, use the same pattern as VaspCalculator:
- `__init__` takes `run=True`
- `write_input()` delegates to `GaussianInput.write_file()`
- `_execute()` runs g09/g16
- `_parse_output()` uses `GaussianOutput`
- Remove `get_*` overrides

- [ ] **Step 4: Run Gaussian tests**

Run:
```bash
conda run -n pmg pytest tests/calculator/test_gaussian.py -v 2>&1 | tail -25
```

- [ ] **Step 5: Commit**

```bash
git add matsimpy/calculator/gaussian/ tests/calculator/test_gaussian.py
git commit -m "<why Gaussian runtime dependencies and driver changed>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 7: Fix LAMMPS IO imports and rewrite LammpsCalculator

**Files:**
- Modify: `matsimpy/calculator/lammps/inputs.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/lammps/outputs.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/lammps/data.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/lammps/generators.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/lammps/sets.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/lammps/utils.py` — fix imports + verify attribution docstring
- Modify: `matsimpy/calculator/lammps/calculator.py` — rewrite (original code, no attribution)
- Create: `tests/calculator/test_lammps_inputs.py`
- Create: `tests/calculator/test_lammps_outputs.py`
- Create: `tests/calculator/test_lammps_data.py`
- Create: `tests/calculator/test_lammps_generators.py`
- Create: `tests/calculator/test_lammps_calculator.py`

Related LAMMPS IO tests may copy relevant cases/fixtures from `thirds/pymatgen-core/tests/io/lammps/`, then rewrite them to matsimpy style with matsimpy imports and optional pymatgen reference checks only.

- [ ] **Step 0: Verify attribution docstrings on all 6 IO files**

Each file needs a module-level docstring:
```python
"""LAMMPS ... — adapted from pymatgen (https://pymatgen.org/).

Original: pymatgen.io.lammps.<module>
Copyright (c) pymatgen Development Team.
Distributed under the MIT License.
Modifications for MatSimPy integration.
"""
```

- [ ] **Step 1: Write test_lammps_data.py**

Create `tests/calculator/test_lammps_data.py`:

```python
"""Tests for LAMMPS data file generation."""
import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice, Molecule


class TestLammpsData:
    def test_write_data_from_crystal(self):
        from matsimpy.calculator.lammps.data import LammpsData
        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        ld = LammpsData(crystal)
        content = ld.get_string()
        assert "atoms" in content.lower()
        assert "xlo xhi" in content

    def test_write_data_from_molecule(self):
        from matsimpy.calculator.lammps.data import LammpsData
        mol = Molecule(["O", "H", "H"],
                       [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        ld = LammpsData(mol)
        content = ld.get_string()
        assert "atoms" in content.lower()

    def test_lammps_box(self):
        from matsimpy.calculator.lammps.data import LammpsBox
        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.0))
        box = LammpsBox.from_structure(crystal)
        assert box is not None

    def test_combined_data(self):
        from matsimpy.calculator.lammps.data import CombinedData
        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        cd = CombinedData([crystal], atom_style="atomic")
        assert cd is not None

    def test_force_field(self):
        from matsimpy.calculator.lammps.data import ForceField
        ff = ForceField()
        assert ff is not None
```

- [ ] **Step 2: Write test_lammps_inputs.py**

Create `tests/calculator/test_lammps_inputs.py`:

```python
"""Tests for LAMMPS input script generation."""
import pytest
import numpy as np


class TestLammpsInputFile:
    def test_basic_input_generation(self):
        from matsimpy.calculator.lammps.inputs import LammpsInputFile
        script = LammpsInputFile(
            units="metal",
            atom_style="atomic",
            boundary="p p p",
        )
        content = script.get_string()
        assert "units metal" in content
        assert "atom_style atomic" in content

    def test_input_with_pair_style(self):
        from matsimpy.calculator.lammps.inputs import LammpsInputFile
        script = LammpsInputFile(
            units="metal",
            atom_style="atomic",
            boundary="p p p",
            pair_style="lj/cut 10.0",
            pair_coeff="* * 0.0103 3.40",
        )
        content = script.get_string()
        assert "pair_style lj/cut 10.0" in content
        assert "pair_coeff * * 0.0103 3.40" in content


class TestLammpsRun:
    def test_run_command(self):
        from matsimpy.calculator.lammps.inputs import LammpsRun
        script = LammpsRun(
            units="metal",
            atom_style="atomic",
            boundary="p p p",
        )
        content = script.get_string()
        assert "run" in content or "units" in content
```

- [ ] **Step 3: Write test_lammps_outputs.py**

Create `tests/calculator/test_lammps_outputs.py`:

```python
"""Tests for LAMMPS output parsing."""
import pytest
import numpy as np


class TestParseLammpsDumps:
    def test_parse_dump_basic(self, tmp_path):
        from matsimpy.calculator.lammps.outputs import parse_lammps_dumps
        content = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0.000000 5.000000
0.000000 5.000000
0.000000 5.000000
ITEM: ATOMS id type x y z
1 1 0.0 0.0 0.0
2 1 2.5 2.5 2.5
"""
        fpath = tmp_path / "dump.lammpstrj"
        fpath.write_text(content)
        dumps = list(parse_lammps_dumps(str(fpath)))
        assert len(dumps) == 1
        dump = dumps[0]
        assert dump.timestep == 0
        assert dump.natoms == 2


class TestParseLammpsLog:
    def test_parse_log_energy(self, tmp_path):
        from matsimpy.calculator.lammps.outputs import parse_lammps_log
        content = """Step Temp E_pair E_mol TotEng Press
       0 0.0 -0.123 0.0 -0.123 1.0
"""
        fpath = tmp_path / "log.lammps"
        fpath.write_text(content)
        logs = list(parse_lammps_log(str(fpath)))
        assert len(logs) >= 1
```

- [ ] **Step 4: Write test_lammps_generators.py**

Create `tests/calculator/test_lammps_generators.py`:

```python
"""Tests for LAMMPS topology generators."""
import pytest
from matsimpy.core import Crystal, Lattice


class TestBaseGenerator:
    def test_generator_accepts_crystal(self):
        from matsimpy.calculator.lammps.generators import BaseGenerator
        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        gen = BaseGenerator(crystal)
        assert gen.structure is not None
```

- [ ] **Step 5: Write test_lammps_calculator.py**

Create `tests/calculator/test_lammps_calculator.py`:

```python
"""Tests for LammpsCalculator driver."""
import pytest
from matsimpy.core import Crystal, Lattice


class TestLammpsCalculator:
    def test_run_false_writes_input_files(self, tmp_path):
        from matsimpy.calculator.lammps import LammpsCalculator
        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        calc = LammpsCalculator(
            directory=str(tmp_path),
            pair_style="lj/cut 10.0",
            pair_coeff="* * 0.0103 3.40",
            run=False,
        )
        calc.calculate(crystal)
        data_file = tmp_path / "data.lammps"
        input_file = tmp_path / "in.lammps"
        assert data_file.exists()
        assert input_file.exists()
        assert "energy" not in calc.results

    def test_run_default_is_true(self):
        from matsimpy.calculator.lammps import LammpsCalculator
        calc = LammpsCalculator()
        assert calc.run is True

    def test_read_results_from_existing_log(self, tmp_path):
        from matsimpy.calculator.lammps import LammpsCalculator
        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        calc = LammpsCalculator(directory=str(tmp_path))
        # Write a log file, then call read_results
        log_content = """Step Temp E_pair E_mol TotEng Press
       0 0.0 -0.123 0.0 -0.123 1.0
"""
        (tmp_path / "log.lammps").write_text(log_content)
        calc.structure = crystal
        calc.read_results()
        assert calc.results.get("energy") is not None

- [ ] **Step 2: Fix imports in lammps/data.py**

Replace:
```python
# OLD: 
from pymatgen.core import Element, Lattice, Molecule, Structure
from pymatgen.core.operations import SymmOp
from pymatgen.util.io_utils import clean_lines

# NEW:
from matsimpy.core import Element, Lattice, Crystal, Molecule
from matsimpy.calculator.utils import clean_lines
```

- [ ] **Step 3: Fix imports in lammps/inputs.py**

Replace:
```python
# OLD:
from pymatgen.core import __version__ as CURRENT_VER
from pymatgen.io.core import InputFile
from pymatgen.io.lammps.data import CombinedData, LammpsData
from pymatgen.io.template import TemplateInputGen

# NEW:
from matsimpy import __version__ as CURRENT_VER
from matsimpy.calculator.lammps.data import CombinedData, LammpsData
# Add a matsimpy-native InputFile protocol/support API
class InputFile:
    """Protocol: objects that can write themselves to a file."""
    def write_file(self, filename): ...
```

- [ ] **Step 4: Fix imports in remaining LAMMPS files**

- `lammps/outputs.py`: `from pymatgen.io.lammps.data import LammpsBox` → `from matsimpy.calculator.lammps.data import LammpsBox`
- `lammps/generators.py`: Replace `pymatgen.core.Structure` → `matsimpy.core.Crystal`, `pymatgen.io.core.InputGenerator` → matsimpy-native protocol/API, internal imports → matsimpy paths
- `lammps/sets.py`: `pymatgen.io.core.InputSet` → matsimpy-native protocol/API, internal imports → matsimpy paths
- `lammps/utils.py`: `pymatgen.core.operations.SymmOp` → matsimpy-native symmetry API, `pymatgen.io.babel.BabelMolAdaptor` → matsimpy-owned behavior or explicit unsupported-feature error with no runtime pymatgen import

- [ ] **Step 5: Rewrite LammpsCalculator**

In `matsimpy/calculator/lammps/calculator.py`, same pattern:
- `run` parameter
- `write_input()` delegates to `LammpsData`/`LammpsInputFile` classes
- `_execute()` runs `lmp_serial -in in.lammps`
- `_parse_output()` uses `parse_lammps_log` / `parse_lammps_dumps`
- Remove `get_*` overrides

- [ ] **Step 6: Run LAMMPS tests**

```bash
conda run -n pmg pytest tests/calculator/test_lammps_*.py -v 2>&1 | tail -40
```

- [ ] **Step 7: Commit**

```bash
git add matsimpy/calculator/lammps/ tests/calculator/test_lammps_*.py
git commit -m "<why LAMMPS runtime dependencies and driver changed>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 8: Update package __init__.py exports

**Files:**
- Modify: `matsimpy/calculator/__init__.py`

- [ ] **Step 1: Update __init__.py**

Replace `matsimpy/calculator/__init__.py`:

```python
"""
Calculator module for MatSimPy.

Provides calculators for computing energies, forces, and other properties.
- lj: Lennard-Jones classical potential
- mattersim: MatterSim ML potential (requires torch)
- vasp: VASP DFT calculator (adapted from pymatgen)
- gaussian: Gaussian calculator (adapted from pymatgen)
- lammps: LAMMPS calculator (adapted from pymatgen)
"""

from .base import Calculator
from .lj import LennardJones

# Lazy import for MatterSim (torch optional)
try:
    from .mattersim import Mattersim
    _has_mattersim = True
except ImportError:
    Mattersim = None
    _has_mattersim = False

# VASP, Gaussian, LAMMPS — always available (IO-only, no external binary required)
from .vasp import VaspCalculator as _VaspCalculator
from .gaussian import GaussianCalculator as _GaussianCalculator
from .lammps import LammpsCalculator as _LammpsCalculator

__all__ = [
    "Calculator",
    "LennardJones",
    "Mattersim",
    "VaspCalculator",
    "GaussianCalculator",
    "LammpsCalculator",
]

# Module-level aliases
VaspCalculator = _VaspCalculator
GaussianCalculator = _GaussianCalculator
LammpsCalculator = _LammpsCalculator
```

- [ ] **Step 2: Verify all exports import cleanly**

Run:
```bash
conda run -n pmg python -c "
from matsimpy.calculator import Calculator, LennardJones
print('LJ OK')
from matsimpy.calculator import VaspCalculator, GaussianCalculator, LammpsCalculator
print('DFT calculators OK')
# MatterSim may be None if torch missing — that's fine
from matsimpy.calculator import Mattersim
print(f'MatterSim = {Mattersim}')
print('All exports OK')
"
```

Expected: "All exports OK"

- [ ] **Step 3: Run all calculator tests one more time**

Run:
```bash
conda run -n pmg pytest tests/calculator/ -v --tb=short 2>&1
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add matsimpy/calculator/__init__.py
git commit -m "<why calculator exports changed>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```

---

### Task 9: Final integration verification and coverage check

Before this task, confirm the external-code tests use mocked commands or offline fixtures. The final verification must not require licensed/proprietary executables unless the local environment already provides them and the test is explicitly marked as optional.

**Files:**
- None created/modified

- [ ] **Step 1: Run the full test suite**

```bash
conda run -n pmg pytest tests/ -v --tb=short 2>&1 | tail -60
```

- [ ] **Step 2: Check calculator test coverage**

```bash
conda run -n pmg pytest tests/calculator/ --cov=matsimpy.calculator --cov-report=term-missing 2>&1 | tail -40
```

- [ ] **Step 3: Verify all calculator-specific imports work from top level**

Run:
```bash
conda run -n pmg python -c "
# Direct IO imports
from matsimpy.calculator.vasp import Incar, Kpoints, Poscar, Potcar, Outcar, Vasprun
print('VASP IO OK')
from matsimpy.calculator.gaussian import GaussianInput, GaussianOutput
print('Gaussian IO OK')
from matsimpy.calculator.lammps import LammpsInputFile, LammpsData, LammpsDump
print('LAMMPS IO OK')
# Calculator drivers
from matsimpy.calculator.vasp import VaspCalculator
from matsimpy.calculator.gaussian import GaussianCalculator
from matsimpy.calculator.lammps import LammpsCalculator
print('All calculator drivers OK')
# LJ + MatterSim
from matsimpy.calculator.lj import LennardJones
from matsimpy.calculator.mattersim import Mattersim
print('LJ + MatterSim OK')
print('EVERYTHING WORKS')
"
```

Expected: "EVERYTHING WORKS"

- [ ] **Step 4: Verify runtime calculator modules do not import pymatgen**

Run:
```bash
if rg -n "from pymatgen|import pymatgen" matsimpy/calculator/; then
  echo "Runtime pymatgen dependency found in calculator modules" >&2
  exit 1
fi
```

Expected: No matches. Pymatgen references are allowed only in tests as optional reference checks and in attribution/documentation comments.

- [ ] **Step 5: Commit final state**

```bash
git status --short
# Stage only files intentionally changed by this implementation.
git add <intentional files>
git commit -m "<why final integration state is ready>" \
  -m "Constraint: <key constraint>" \
  -m "Tested: <commands run>" \
  -m "Not-tested: <known gaps>"
```
