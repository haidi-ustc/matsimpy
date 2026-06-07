# Calculator Modules Design — VASP, Gaussian, LAMMPS, LJ, MatterSim

**Date:** 2026-06-07
**Status:** approved

## Overview

Complete the calculator module with five calculators under a unified ASE-style interface. IO classes adapted from pymatgen-core (MIT License) live alongside calculator drivers in each subpackage. Two execution modes: online (`run=True`, default) and offline (`run=False`).

## Architecture

```
matsimpy/calculator/
├── base.py                  Calculator ABC — enhanced with run mode
├── lj/                      LennardJones — pure Python classical
│   └── calculator.py
├── mattersim/               MatterSim — ML potential (restored from v0.4)
│   ├── calculator.py        Mattersim class
│   └── dataloader.py        MatSimPyGraphConvertor, build_dataloader
├── vasp/                    VASP — external DFT
│   ├── calculator.py        VaspCalculator
│   ├── inputs.py            Incar, Kpoints, Poscar, Potcar   [from pymatgen]
│   ├── outputs.py           Outcar, Vasprun, Oszicar...      [from pymatgen]
│   └── sets.py              VaspInputSet, DictSet...         [from pymatgen]
├── gaussian/                Gaussian — external QC
│   ├── calculator.py        GaussianCalculator
│   └── gaussian.py          GaussianInput, GaussianOutput    [from pymatgen]
└── lammps/                  LAMMPS — external MD
    ├── calculator.py        LammpsCalculator
    ├── inputs.py            LammpsInputFile, LammpsRun       [from pymatgen]
    ├── outputs.py           LammpsDump, parse_lammps_dumps   [from pymatgen]
    ├── data.py              LammpsData, CombinedData         [from pymatgen]
    ├── generators.py        BaseGenerator, LammpsGenerator   [from pymatgen]
    ├── sets.py              LammpsInputSet                   [from pymatgen]
    └── utils.py             Utility functions                [from pymatgen]
```

## Module Boundary

| Module | Responsibility | Does NOT handle |
|--------|---------------|-----------------|
| `matsimpy/io/` | Structure file I/O (POSCAR, CIF, XYZ...) via FormatRegistry | Calculator input generators, output parsers |
| `matsimpy/calculator/` | Calculator drivers, engine-specific IO, pure-Python computation | Structure file reading/writing |

**Rule:** If it involves running a calculation or generating engine-specific inputs (Incar, LammpsData, GaussianInput...), it belongs in `calculator/`. If it reads/writes a structure format that multiple tools can use (POSCAR, CIF, XYZ...), it belongs in `io/`.

## Calculator Base Class (base.py)

### Enhancements

Add `run` parameter and split the computation pipeline into discrete steps:

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
    def _parse_output(self):           # internal parser
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

- **Status:** Fully implemented in `lj/calculator.py` (309 lines)
- **Enhancements needed:**
  - Multi-species support with per-pair sigma/epsilon via Lorentz-Berthelot mixing rules
- **Tests:** Enhance existing test — energy conservation, force consistency, Ar FCC known energy

### MatterSim (restore from v0.4)

- **Source:** Git commit `845e79e` (`calculator/ml/mattersim.py` + `calculator/ml/dataloader.py`)
- **Restore to:** `calculator/mattersim/calculator.py` + `calculator/mattersim/dataloader.py`
- **Changes from v0.4:**
  - Flatten from `calculator.ml.mattersim` → `calculator.mattersim`
  - Inherit directly from `Calculator` (drop `BaseML` — only one ML calculator)
  - Update relative imports to absolute (`from ...core` → `from matsimpy.core`)
  - `__init__.py` exports `Mattersim`
- **Key features:**
  - Loads MatterSim M3GNet-based models via checkpoint
  - Supports model shortcuts (`mattersim-v1.0.0-5M`, `mattersim-v1.0.0-1M`)
  - Uses matsimpy native graph conversion (no ASE dependency)
  - Computes energy, forces, stress for both Crystal and Molecule
  - Lazy model loading (torch optional)
- **Tests:** Model loading (requires torch/torch-geometric, use `@pytest.mark.requires_torch`), energy/forces prediction, serialization (no torch needed), device handling. Tests that require torch skip gracefully when it's absent.

### VASP

- **Status:** IO classes (`inputs.py`, `outputs.py`, `sets.py`) adapted from pymatgen (~13.5k lines). Calculator driver (`calculator.py`) is thin ~151 lines.
- **Work needed:**
  - **`inputs.py`, `outputs.py`, `sets.py`:** Fix pymatgen imports → matsimpy equivalents (Structure→Crystal, Element→Element, Lattice→Lattice, etc.). Add module-level attribution docstrings.
  - **`calculator.py`:** Rewrite with proper `write_input` / `_execute` / `_parse_output` / `read_results` separation. Remove overrides of `get_*` methods (use base class). Make POTCAR handling optional.
- **Tests (4 files):**
  - `test_vasp_inputs.py` — Incar read/write, Kpoints generation, Poscar roundtrip (with selective dynamics), Potcar hash verification
  - `test_vasp_outputs.py` — Outcar energy/forces/stress parsing, Vasprun XML parsing, Oszicar/Chgcar parsing
  - `test_vasp_sets.py` — VaspInputSet/DictSet generation from Crystal structures
  - `test_vasp_calculator.py` — run=True/False modes, energy/forces/stress extraction

### Gaussian

- **Status:** IO classes (`gaussian.py`) adapted from pymatgen (~1.3k lines). Calculator driver (`calculator.py`) is 108 lines.
- **Work needed:**
  - **`gaussian.py`:** Fix pymatgen imports → matsimpy. Add attribution docstring.
  - **`calculator.py`:** Rewrite with run mode, delegate to GaussianInput/GaussianOutput.
- **Tests (1 file):**
  - `test_gaussian.py` — GaussianInput generation (route, charge, spin), GaussianOutput parsing (SCF energy, forces, vibrations), calculator run=True/False

### LAMMPS

- **Status:** IO classes (`inputs.py`, `outputs.py`, `data.py`, `generators.py`, `sets.py`, `utils.py`) adapted from pymatgen (~3.7k lines). Calculator driver (`calculator.py`) is 124 lines.
- **Work needed:**
  - **IO files:** Fix pymatgen imports → matsimpy. Add attribution docstrings.
  - **`calculator.py`:** Rewrite with run mode, delegate to LammpsData/LammpsInputFile/LammpsDump.
- **Tests (5 files):**
  - `test_lammps_inputs.py` — Script generation, pair style/coeff configuration
  - `test_lammps_outputs.py` — Dump file parsing, log file parsing
  - `test_lammps_data.py` — Data file generation for Crystal/Molecule, box bounds
  - `test_lammps_generators.py` — Topology generation, force field assignment
  - `test_lammps_calculator.py` — run=True/False modes, energy extraction

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

All tests written fresh in matsimpy style, inspired by pymatgen-core test cases.

| Module | Test File(s) | Key Scenarios |
|--------|-------------|---------------|
| base | `test_calculator_base.py` (enhance) | calculate() flow, parameter management, serialization, run=True/False |
| LJ | `test_calculator_lennard_jones.py` (enhance) | Ar FCC energy, force consistency, multi-species mixing |
| MatterSim | `test_mattersim.py` (new) | Numpy demo model, energy/forces, serialization |
| VASP | `test_vasp_inputs.py`, `test_vasp_outputs.py`, `test_vasp_sets.py`, `test_vasp_calculator.py` (all new) | INCAR/KPOINTS/POSCAR/POTCAR roundtrip, OUTCAR/vasprun.xml parsing, input set generation, run modes |
| Gaussian | `test_gaussian.py` (new) | Input generation, output parsing, calculator modes |
| LAMMPS | `test_lammps_inputs.py`, `test_lammps_outputs.py`, `test_lammps_data.py`, `test_lammps_generators.py`, `test_lammps_calculator.py` (all new) | Script generation, dump/log parsing, data file roundtrip, run modes |

## Implementation Order

Dependencies between subpackages dictate the order:

1. **base.py** — enhanced Calculator ABC with `run` mode (blocks all calculator drivers)
2. **LJ** — multi-species mixing (independent, pure Python)
3. **MatterSim** — restore from v0.4, flatten structure, update imports (independent, pure Python)
4. **VASP** — fix imports across 3 IO files, rewrite calculator (depends on base.py)
5. **Gaussian** — fix imports, rewrite calculator (depends on base.py)
6. **LAMMPS** — fix imports across 5+ IO files, rewrite calculator (depends on base.py)
7. **`__init__.py`** — update exports to include all five calculators + lazy import for MatterSim (torch optional)
8. **Tests** — written alongside each calculator as it's completed

Steps 2-3 can run in parallel. Steps 4-6 can run in parallel after step 1.

## Design Decisions

1. **IO stays in calculator subpackages** — users can import IO classes directly (`from matsimpy.calculator.vasp import Incar`) or use via calculator
2. **Dual execution mode** — `run=True` (default, matches ASE), `run=False` (offline input generation)
3. **Tests rewritten fresh** — matsimpy style, pymatgen-test-case-inspired
4. **Attribution at module level** — clear, consistent MIT License labeling
5. **MatterSim inherits Calculator directly** — no BaseML intermediary (only one ML calculator)
6. **Boundary: io/ for structure files, calculator/ for engine files + computation**
