# Calculator Modules Design — VASP, Gaussian, LAMMPS, LJ, MatterSim

**Date:** 2026-06-07
**Status:** approved target design; current implementation is partial
**Last checked:** 2026-06-07 against repository state

## Overview

Complete the calculator module with five calculators under a unified ASE-style interface. IO classes adapted from pymatgen-core (MIT License) live alongside calculator drivers in each subpackage, but copied runtime modules must depend on matsimpy-native modules/APIs rather than pymatgen. Two execution modes are the target design: online (`run=True`, default) and offline (`run=False`).

Current repository state is partial: LJ is implemented, VASP/Gaussian/LAMMPS have thin drivers plus mostly pymatgen-adapted IO, MatterSim is not present, and the base `Calculator` does not yet implement the target `run`/offline pipeline.

## Current Implementation Snapshot

| Area | Current state | Gap to target |
|------|---------------|---------------|
| `matsimpy/calculator/base.py` | Uses `_compute()` as the only abstract execution hook. No `run` parameter, no `write_input()` / `_execute()` / `_parse_output()` / `read_results()` contract. | Add the run-mode pipeline described below and keep result access through the base `get_*` methods. |
| LJ | `matsimpy/calculator/lj/calculator.py` is implemented and tested against basic molecule/crystal behavior and ASE references where ASE is available. | Add multi-species per-pair parameters / Lorentz-Berthelot mixing if required by this design. |
| MatterSim | No `matsimpy/calculator/mattersim/` package exists. | Restore from v0.4 and flatten into `calculator/mattersim/`. |
| VASP | `vasp/inputs.py`, `outputs.py`, and `sets.py` exist with attribution docstrings, but still import many pymatgen symbols directly. `VaspCalculator` writes inputs, executes VASP, and parses some outputs, but has no `run=False` mode or `read_results()`. | Replace all runtime pymatgen dependencies with matsimpy-native modules/APIs, complete driver split, optional POTCAR behavior, and remove `get_*` overrides. |
| Gaussian | `gaussian/gaussian.py` exists with attribution docstring but still imports pymatgen symbols directly. `GaussianCalculator` writes a simple `.gjf`, executes Gaussian, and parses energy only. | Replace all runtime pymatgen dependencies with matsimpy-native modules/APIs, delegate to `GaussianInput`/`GaussianOutput`, implement run-mode split and offline parse. |
| LAMMPS | LAMMPS IO files exist with attribution docstrings but still import pymatgen symbols directly. `LammpsCalculator` writes simple atomic data/input files, executes LAMMPS, and parses energy only. | Replace all runtime pymatgen dependencies with matsimpy-native modules/APIs, delegate to `LammpsData`/`LammpsInputFile`/`LammpsDump`, implement run-mode split and offline parse. |
| Package exports | Top-level `matsimpy.calculator.__all__` exports only `Calculator` and `LennardJones`. Subpackage exports vary. | Export all implemented calculators and use lazy MatterSim export so torch remains optional. |
| Tests | Existing calculator tests cover base, LJ, and import/basic initialization for VASP/Gaussian/LAMMPS. | Add the module-specific behavioral tests listed in the test plan. |

## Architecture

Target layout:

```
matsimpy/calculator/
├── base.py                  Calculator ABC — enhanced with run mode
├── utils.py                 Shared calculator utilities
├── electronic.py            Shared electronic helper types as needed
├── io.py                    Shared IO protocols/support types as needed
├── symmetry.py              Shared symmetry support as needed
├── lj/                      LennardJones — pure Python classical
│   └── calculator.py
├── mattersim/               MatterSim — ML potential (restored from v0.4)
│   ├── calculator.py        Mattersim class
│   └── dataloader.py        MatSimPyGraphConvertor, build_dataloader
├── vasp/                    VASP — external DFT
│   ├── calculator.py        VaspCalculator
│   ├── inputs.py            Incar, Kpoints, Poscar, Potcar   [adapted; matsimpy-native deps]
│   ├── outputs.py           Outcar, Vasprun, Oszicar...      [adapted; matsimpy-native deps]
│   └── sets.py              VaspInputSet, DictSet...         [adapted; matsimpy-native deps]
├── gaussian/                Gaussian — external QC
│   ├── calculator.py        GaussianCalculator
│   └── gaussian.py          GaussianInput, GaussianOutput    [adapted; matsimpy-native deps]
└── lammps/                  LAMMPS — external MD
    ├── calculator.py        LammpsCalculator
    ├── inputs.py            LammpsInputFile, LammpsRun       [adapted; matsimpy-native deps]
    ├── outputs.py           LammpsDump, parse_lammps_dumps   [adapted; matsimpy-native deps]
    ├── data.py              LammpsData, CombinedData         [adapted; matsimpy-native deps]
    ├── generators.py        BaseGenerator, LammpsGenerator   [adapted; matsimpy-native deps]
    ├── sets.py              LammpsInputSet                   [adapted; matsimpy-native deps]
    └── utils.py             Utility functions                [adapted; matsimpy-native deps]
```

Missing dependency surfaces from copied pymatgen modules should be added as small, documented matsimpy-native modules/APIs in this shared calculator layer when they are generally useful. Electronic helper types may be copied/adapted from pymatgen with attribution, but they become matsimpy-owned code and must not import pymatgen at runtime. Do not hide replacements as one-off patches, adapters, or private shim classes inside copied VASP/Gaussian/LAMMPS files.

## Module Boundary

| Module | Responsibility | Does NOT handle |
|--------|---------------|-----------------|
| `matsimpy/io/` | Structure file I/O (POSCAR, CIF, XYZ...) via FormatRegistry | Calculator input generators, output parsers |
| `matsimpy/calculator/` | Calculator drivers, engine-specific IO, pure-Python computation | Structure file reading/writing |

**Rule:** If it involves running a calculation or generating engine-specific inputs (Incar, LammpsData, GaussianInput...), it belongs in `calculator/`. If it reads/writes a structure format that multiple tools can use (POSCAR, CIF, XYZ...), it belongs in `io/`.

## Calculator Base Class (base.py)

### Target Enhancements

Add a `run` parameter and split the computation pipeline into discrete steps:

```python
class Calculator(ABC, MSONable):
    def __init__(self, run: bool = True, **parameters):
        self.run = run
        ...

    def calculate(self, structure):
        # Always: write input files
        self.write_input(structure)
        self._last_structure_hash = structure._structural_hash()

        if self.run:
            self._execute()         # subprocess call
            self._parse_output()    # parse fresh output

    # Public API
    def write_input(self, structure):   # subclasses implement
    def read_results(self):             # offline parse (user calls after manual run)
    def get_potential_energy(self) -> float:
    def get_forces(self) -> np.ndarray:
    def get_stress(self, voigt=False) -> np.ndarray:

    # Internal hooks
    def _execute(self):                 # optional — subprocess
    def _parse_output(self):            # internal parser
```

### Flow

```
run=True (default):
  calculate(structure)
    → write_input(structure)     [always]
    → _execute()                 [subprocess]
    → _parse_output()            [parses fresh output]
  → get_potential_energy(), get_forces(), get_stress()

run=False (offline):
  calculate(structure)
    → write_input(structure)     [always]
  ... user runs code manually ...
  → read_results()               [user calls this]
  → get_potential_energy(), get_forces(), get_stress()
```

## Per-Calculator Design

### LJ (LennardJones)

- **Current status:** Implemented in `lj/calculator.py` and covered by `tests/calculator/test_calculator_lennard_jones.py`.
- **Enhancements needed:**
  - Multi-species support with per-pair sigma/epsilon via Lorentz-Berthelot mixing rules.
- **Tests:** Enhance existing test coverage for energy conservation, force consistency, and Ar FCC known energy / ASE reference behavior.

### MatterSim (restore from v0.4)

- **Current status:** Not present in the repository.
- **Source:** Git commit `845e79e` (`calculator/ml/mattersim.py` + `calculator/ml/dataloader.py`).
- **Restore to:** `calculator/mattersim/calculator.py` + `calculator/mattersim/dataloader.py`.
- **Changes from v0.4:**
  - Flatten from `calculator.ml.mattersim` → `calculator.mattersim`.
  - Inherit directly from `Calculator` (drop `BaseML` — only one ML calculator).
  - Update relative imports to absolute (`from ...core` → `from matsimpy.core`).
  - `__init__.py` exports `Mattersim`.
- **Key features:**
  - Loads MatterSim M3GNet-based models via checkpoint.
  - Supports model shortcuts (`mattersim-v1.0.0-5M`, `mattersim-v1.0.0-1M`).
  - Uses matsimpy native graph conversion (no ASE dependency).
  - Computes energy, forces, stress for both Crystal and Molecule.
  - Lazy model loading (torch optional).
- **Tests:** Model loading (requires torch/torch-geometric, use `@pytest.mark.requires_torch`), energy/forces prediction, serialization (no torch needed), device handling. Tests that require torch skip gracefully when absent.

### VASP

- **Current status:** IO classes (`inputs.py`, `outputs.py`, `sets.py`) are present and attributed, but still depend heavily on pymatgen imports. Calculator driver is thin and does not implement offline mode.
- **Work needed:**
  - **`inputs.py`, `outputs.py`, `sets.py`:** Fix pymatgen imports → matsimpy-native modules/APIs (Structure→Crystal, Element→Element, Lattice→Lattice, etc.). Keep module-level attribution docstrings.
  - Remove all runtime pymatgen imports from copied VASP modules. Missing dependency surfaces must be added gracefully to matsimpy as coherent modules/APIs, not as one-off patches, adapters, or private shim classes.
  - Unsupported advanced behavior must raise a clear matsimpy error instead of importing pymatgen at runtime.
  - **`calculator.py`:** Rewrite with proper `write_input` / `_execute` / `_parse_output` / `read_results` separation. Remove overrides of `get_*` methods (use base class). Make POTCAR handling optional and deterministic.
- **Tests (4 files):**
  - `test_vasp_inputs.py` — Incar read/write, Kpoints generation, Poscar roundtrip (with selective dynamics), Potcar hash verification.
  - `test_vasp_outputs.py` — Outcar energy/forces/stress parsing, Vasprun XML parsing, Oszicar/Chgcar parsing.
  - `test_vasp_sets.py` — VaspInputSet/DictSet generation from Crystal structures.
  - `test_vasp_calculator.py` — run=True/False modes, energy/forces/stress extraction.

### Gaussian

- **Current status:** IO class file (`gaussian.py`) is present and attributed, but still imports pymatgen symbols. Calculator driver writes a simple input file directly and parses energy only.
- **Work needed:**
  - **`gaussian.py`:** Fix pymatgen imports → matsimpy-native modules/APIs. Keep attribution docstring.
  - Remove all runtime pymatgen imports from copied Gaussian modules. Missing dependency surfaces must be added gracefully to matsimpy as coherent modules/APIs, not as one-off patches, adapters, or private shim classes.
  - Unsupported advanced behavior must raise a clear matsimpy error instead of importing pymatgen at runtime.
  - **`calculator.py`:** Rewrite with run mode, delegate to GaussianInput/GaussianOutput, implement `read_results()`.
- **Tests (1 file):**
  - `test_gaussian.py` — GaussianInput generation (route, charge, spin), GaussianOutput parsing (SCF energy, forces, vibrations), calculator run=True/False.

### LAMMPS

- **Current status:** IO files (`inputs.py`, `outputs.py`, `data.py`, `generators.py`, `sets.py`, `utils.py`) are present and attributed, but still import pymatgen symbols. Calculator driver writes simple atomic inputs directly and parses energy only.
- **Work needed:**
  - **IO files:** Fix pymatgen imports → matsimpy-native modules/APIs. Keep attribution docstrings.
  - Remove all runtime pymatgen imports from copied LAMMPS modules. Missing dependency surfaces must be added gracefully to matsimpy as coherent modules/APIs, not as one-off patches, adapters, or private shim classes.
  - Unsupported advanced behavior must raise a clear matsimpy error instead of importing pymatgen at runtime.
  - **`calculator.py`:** Rewrite with run mode, delegate to LammpsData/LammpsInputFile/LammpsDump, implement `read_results()`.
- **Tests (5 files):**
  - `test_lammps_inputs.py` — Script generation, pair style/coeff configuration.
  - `test_lammps_outputs.py` — Dump file parsing, log file parsing.
  - `test_lammps_data.py` — Data file generation for Crystal/Molecule, box bounds.
  - `test_lammps_generators.py` — Topology generation, force field assignment.
  - `test_lammps_calculator.py` — run=True/False modes, energy extraction.

## Attribution Strategy

Three-tier labeling for all code adapted from pymatgen-core (MIT License):

1. **Module-level docstring** (every adapted file):
   ```python
   """VASP input file classes — adapted from pymatgen (https://pymatgen.org/).

   Original: pymatgen.io.vasp.inputs
   Copyright (c) pymatgen Development Team.
   Distributed under the MIT License.
   Modifications for MatSimPy integration.
   """
   ```

2. **Class-level docstring** (significant adaptations, e.g., Poscar using Crystal):
   ```python
   class Poscar:
       """POSCAR writer/reader — adapted from pymatgen.io.vasp.inputs.Poscar.

       Uses matsimpy Crystal instead of pymatgen Structure.
       """
   ```

3. **Inline comment** (specific algorithm copies):
   ```python
   # Adapted from pymatgen.io.vasp.inputs — POTCAR hash verification logic
   ```

**Files NOT needing attribution:** All `calculator.py` files (original matsimpy code), `lj/` (original), `mattersim/` (original), all test files (original, inspired by pymatgen test cases).

## Test Plan

All tests written fresh in matsimpy style, inspired by pymatgen-core test cases. Tests may use pymatgen only as an optional reference implementation/oracle and must skip gracefully when pymatgen is unavailable. Runtime modules under `matsimpy/calculator/` must not depend on pymatgen.

| Module | Test File(s) | Key Scenarios |
|--------|-------------|---------------|
| base | `test_calculator_base.py` (enhance) | calculate() flow, parameter management, serialization, run=True/False |
| LJ | `test_calculator_lennard_jones.py` (enhance) | Ar FCC energy, force consistency, multi-species mixing |
| MatterSim | `test_mattersim.py` / `test_calculator_mattersim.py` (new or restored) | Numpy demo model, energy/forces, serialization, torch-optional skips |
| VASP | `test_vasp_inputs.py`, `test_vasp_outputs.py`, `test_vasp_sets.py`, `test_vasp_calculator.py` (all new) | INCAR/KPOINTS/POSCAR/POTCAR roundtrip, OUTCAR/vasprun.xml parsing, input set generation, run modes |
| Gaussian | `test_gaussian.py` (new) | Input generation, output parsing, calculator modes |
| LAMMPS | `test_lammps_inputs.py`, `test_lammps_outputs.py`, `test_lammps_data.py`, `test_lammps_generators.py`, `test_lammps_calculator.py` (all new) | Script generation, dump/log parsing, data file roundtrip, run modes |
| smoke/import | `test_vasp_imports.py` (existing) | Current import and constructor smoke coverage for VASP/Gaussian/LAMMPS |
| dependency guard | shell/static check | `matsimpy/calculator/**` contains no `from pymatgen` or `import pymatgen` runtime imports; pymatgen references are limited to tests, attribution, and documentation |

## Implementation Order

Dependencies between subpackages dictate the order:

1. **base.py** — enhance Calculator ABC with `run` mode (blocks all calculator drivers).
2. **LJ** — multi-species mixing (independent, pure Python).
3. **MatterSim** — restore from v0.4, flatten structure, update imports (independent from external calculators).
4. **VASP** — fix imports across 3 IO files, rewrite calculator (depends on base.py).
5. **Gaussian** — fix imports, rewrite calculator (depends on base.py).
6. **LAMMPS** — fix imports across 5+ IO files, rewrite calculator (depends on base.py).
7. **`__init__.py`** — update exports to include all five calculators + lazy import for MatterSim (torch optional).
8. **Tests** — write/expand tests alongside each calculator as it is completed.

Steps 2-3 can run in parallel. Steps 4-6 can run in parallel after step 1.

Each implementation step is a separate commit checkpoint after its local verification passes. Commits must stage only the files intentionally changed for that step and must follow the repository Lore Commit Protocol.

## Design Decisions

1. **IO stays in calculator subpackages** — users can import IO classes directly (`from matsimpy.calculator.vasp import Incar`) or use via calculator.
2. **Dual execution mode** — `run=True` (default, matches ASE), `run=False` (offline input generation).
3. **Tests rewritten fresh** — matsimpy style, pymatgen-test-case-inspired.
4. **Attribution at module level** — clear, consistent MIT License labeling.
5. **MatterSim inherits Calculator directly** — no BaseML intermediary (only one ML calculator).
6. **Boundary: io/ for structure files, calculator/ for engine files + computation.**

## Open Risks

- Direct pymatgen imports remain in adapted IO modules today; implementation must remove them from runtime code rather than preserving them as optional fallbacks.
- The target base-class run-mode design is not backward compatible with current subclasses unless `_compute()` is kept as a compatibility hook or all calculators are migrated together.
- External executable tests need fixtures/mocks or offline sample outputs so CI does not require VASP, Gaussian, or LAMMPS binaries.
