# Calculator Modules — Implementation Plan

**Goal:** Copy VASP/Gaussian/LAMMPS from pymatgen-core, restructure calculator into subpackages, remove code/ and dft/ml.

**Architecture:** 4 calculator subpackages (lj, vasp, gaussian, lammps). Each has inputs.py + outputs.py. Adapted from pymatgen with matsimpy equivalents.

## Tasks

### Task 1: Copy pymatgen-core VASP modules, adapt to matsimpy
- Copy pymatgen.io.vasp.{inputs,outputs,sets} → calculator/vasp/
- Replace pymatgen Structure with matsimpy Crystal, Lattice imports
- Replace pymatgen Element with matsimpy Element
- Add acknowledgment headers

### Task 2: Copy pymatgen-core Gaussian + LAMMPS modules
- Copy pymatgen.io.gaussian → calculator/gaussian/
- Copy pymatgen.io.lammps → calculator/lammps/
- Same adaptation

### Task 3: Move LJ, cleanup old modules
- Move classical/lennard_jones.py → lj/calculator.py
- Remove code/ package
- Remove calculator/dft/, calculator/ml/
- Update calculator/__init__.py

### Task 4: Write tests, verify
- Tests for VASP input/output parsing
- Tests for Gaussian, LAMMPS
- Tests for LJ
- Full test suite
