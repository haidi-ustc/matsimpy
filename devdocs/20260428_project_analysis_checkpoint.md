# MatSimPy Project Analysis Checkpoint

**Date:** 2026-04-28  
**Environment:** `conda run -n pmg ...` / `/opt/miniconda3/envs/pmg/bin/python`  
**Repo:** `/Users/haidi/dev/matsimpy`  
**Git HEAD:** `afa762a` (`master`, `origin/master`) - Fix Heusler alloy builder to match reference CIF structures

## Context

Initial user request:

> Analyze this existing project.
> 1. Understand overall architecture
> 2. Identify completed vs unfinished parts
> 3. Detect potential issues or risks
> 4. Ask me any missing context before proceeding

User later clarified: use conda env `pmg`.

## Architecture Summary

MatSimPy is a Python materials-simulation toolkit, currently version `0.1.0` / Alpha.

Main modules:

- `matsimpy/core/` — central data model: `Structure`, `Crystal`, `Molecule`, `Lattice`, `Site`, `Composition`, `Element`, graph utilities.
- `matsimpy/builders/` — structure generation: bulk, surface, alloy, molecule, defects, nanostructure; `interface/` is placeholder.
- `matsimpy/transformation/` — geometric, lattice, atomic, chemical, structural transformations plus composite high-throughput helpers.
- `matsimpy/io/` — VASP, CIF, XYZ, PDB, XSF, JSON, ASE, MOL, LaTeX export.
- `matsimpy/calculator/` — calculators: classical LJ, optional/partial ML MatterSim, DFT skeleton.
- `matsimpy/symmetry/` — spglib-based symmetry analysis.
- `matsimpy/storage/` — maggma-backed data storage.
- `matsimpy/ai/` — AI/MCP framework, partial.
- `matsimpy/ui/` — CLI exists; Jupyter/web are empty.
- `matsimpy/analysis/`, `matsimpy/visualization/` — mostly placeholder/empty.

Observed scale:

- 131 Python files under `matsimpy/`
- ~31.8k LOC under `matsimpy/`
- 79 test files
- 1333 pytest-collected tests

## Completed / Mostly Usable Areas

- `core`
- `builders`, except `builders/interface`
- `transformation`
- `io` basic formats
- `symmetry`
- `config`
- `utils.selection`
- Classical calculator: `LennardJones`
- Documentation/examples are broad and useful

## Partial Areas

- `calculator.ml` — depends on `torch`/MatterSim; unavailable in current `pmg`.
- `storage` — implementation exists but `maggma` missing in current `pmg`.
- `ai` — framework exists; real integrations/transports are partial.
- `ui.cli` — implemented but likely needs functional audit.

## Unfinished / Placeholder Areas

- `analysis/*` — TODO-only modules; exports empty `__all__`.
- `visualization` — empty.
- `builders/interface` — placeholder only.
- `code/vasp.py` — `write_input` and `read_output` raise `NotImplementedError`.
- `code/quantum_espresso.py` — input writer exists; output parser raises `NotImplementedError`.
- `calculator/dft` — abstract/skeleton only.
- `ui/jupyter`, `ui/web` — empty.
- `code/pwdft.py` — empty.

## Environment / Dependency Findings in `pmg`

Command used:

```bash
conda run -n pmg python -c "import sys, importlib.util; print(sys.executable); [print(pkg, 'OK' if importlib.util.find_spec(pkg) else 'MISSING') for pkg in ['numpy','scipy','maggma','spglib','pymatgen','ase','torch','rdkit']]"
```

Observed:

- Python: `/opt/miniconda3/envs/pmg/bin/python`
- `numpy`: OK
- `scipy`: OK
- `maggma`: MISSING
- `spglib`: OK
- `pymatgen`: OK
- `ase`: OK
- `torch`: MISSING
- `rdkit`: MISSING

## Test Result Observed

A full pytest run was initially started without explicitly wrapping with `conda run -n pmg`, but output indicates it was using the `pmg` interpreter/site-packages:

- Platform: darwin
- Python: 3.12.7
- pytest: 9.0.3
- rootdir: `/Users/haidi/dev/matsimpy`
- configfile: `pytest.ini` with warning: ignoring pytest config in `pyproject.toml`
- collected: 1333 items

Result:

```text
17 failed, 1281 passed, 35 skipped, 52 warnings
```

All 17 failures were in `tests/test_storage.py`, caused by missing `maggma`:

```text
ImportError: maggma is required for DataStorage. Install with: pip install maggma or pip install matsimpy[storage]
```

Warnings included spglib deprecations and NumPy 2.0 deprecations in nanotube code.

## Potential Issues / Risks

### Test and Dependency Risks

- `maggma` missing in `pmg`; storage tests fail.
- `torch` missing in `pmg`; ML/MatterSim functionality not verified.
- `rdkit` missing in `pmg`; SMILES/molecule builder functionality may skip/fail depending on tests.
- Optional dependency policy unclear: should optional tests skip when dependencies are absent, or should dev env include all extras?

### Packaging / CI Risks

- README mentions `requirements.txt` and `requirements-dev.txt`, but they were not found.
- `.workflow/*.yml` references:
  - `pip3 install -r requirements.txt`
  - `python3 ./main.py`
- `main.py` was not found.
- Both `pytest.ini` and `pyproject.toml` define pytest config; pytest warns it is ignoring pyproject pytest config.
- `packages = { find = {} }` may package `tests` because `tests/__init__.py` exists.

### Product / API Risks

- README/docs advertise several features that are partial or optional, notably AI, DFT, storage, ML, visualization, CLI.
- DFT integration is incomplete but surfaced in docs.
- `analysis` module exists but exports no usable functionality.
- `visualization` package is empty.
- MatterSim tests are skipped in current env; real ML behavior not verified.
- Some devdocs are stale relative to current repo counts/status.

## Missing Context Questions Asked

Before proceeding, ask/confirm:

1. What is the immediate goal: release readiness, research use, CI repair, docs cleanup, feature completion, or code quality?
2. Should missing optional dependencies be installed into `pmg`, especially `maggma`, `torch`, `rdkit`, MatterSim?
3. Should tests pass in a minimal core env, or only in a full optional env?
4. Which unfinished area matters most: `analysis`, `visualization`, DFT/VASP/QE, storage, AI, CLI, or packaging/CI?
5. Are breaking API/doc changes acceptable if they improve consistency?
6. Is Gitee workflow support required, or should CI be modernized separately?

## Notes

- `omx explore` could not be used because the explore harness required cargo/prebuilt binary and failed locally.
- Created local runtime artifacts during analysis: `.omx/` existed/was untracked; pytest created `.pytest_cache/` and `configs/` appeared in working tree.
