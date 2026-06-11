# Core IO API Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move adapters/export into `matsimpy.io`, add core `from_file`/`to_file` conveniences, replace AI adapters/export skills with one IO skill, and fix the identified core mutability/cache/validation bugs.

**Architecture:** `matsimpy.io` becomes the only public boundary for file IO, third-party object conversion, and LaTeX table output. `Structure`, `Crystal`, and `Molecule` keep convenience methods, but those methods are thin wrappers over `matsimpy.io`. Bug fixes are covered by regression tests before implementation.

**Tech Stack:** Python, pytest/unittest, NumPy, optional ASE/pymatgen extras, existing MatSimPy IO registry, existing AI skill loader.

---

## File Structure

- Create: `matsimpy/io/pymatgen.py`
  - Owns `to_pymatgen()` and `from_pymatgen()` object conversion.
- Create: `matsimpy/io/latex.py`
  - Owns LaTeX table helpers moved from `matsimpy/export/latex.py`.
- Create: `matsimpy/ai/skills/io.py`
  - Replaces separate adapters/export AI skills.
- Modify: `matsimpy/io/ase.py`
  - Keeps `read_ASE()` / `write_ASE()` and gains `to_ase()` / `from_ase()`.
- Modify: `matsimpy/io/core.py`
  - Adds `read_file` and `write_file` aliases.
- Modify: `matsimpy/io/__init__.py`
  - Exports unified IO API.
- Modify: `matsimpy/core/structure.py`
  - Adds `from_file()` and `to_file()`.
  - Tightens `substitute()` index validation.
- Modify: `matsimpy/core/crystal.py`
  - Routes conversion methods to IO.
  - Adds typed `from_file()`.
  - Fixes `sites` snapshot behavior.
  - Tightens `substitute()` index validation.
- Modify: `matsimpy/core/molecule.py`
  - Routes conversion methods to IO.
  - Adds typed `from_file()`.
  - Fixes `sites` snapshot behavior.
  - Tightens `substitute()` index validation.
  - Fixes center-of-mass cache leak.
- Modify: `matsimpy/core/symmop.py`
  - Makes affine data safe from external mutation.
- Modify: `matsimpy/core/periodic_table.py`
  - Validates direct `Element.get_element()` input type.
- Modify: `matsimpy/core/composition.py`
  - Makes decimal formula rejection explicit.
- Modify: `matsimpy/calculator/base.py`
  - Stabilizes offline result hash behavior.
- Modify: `matsimpy/builders/bulk/random.py`
  - Imports pymatgen conversion from IO.
- Delete: `matsimpy/adapters/`
  - Removed public package.
- Delete: `matsimpy/export/`
  - Removed public package.
- Delete: `matsimpy/ai/skills/adapters.py`
  - Replaced by IO skill.
- Delete: `matsimpy/ai/skills/export.py`
  - Replaced by IO skill.
- Modify tests under `tests/io/`, `tests/core/`, `tests/ai/`, and `tests/test_packaging_runtime_contracts.py`.

## Task 1: Lock Unified IO Public API Tests

**Files:**
- Modify: `tests/io/test_io_converters.py`
- Modify: `tests/io/test_io_latex.py`
- Create: `tests/io/test_io_public_api.py`

- [ ] **Step 1: Update converter imports to the new public API**

In `tests/io/test_io_converters.py`, replace:

```python
from matsimpy.adapters.pymatgen import to_pymatgen, from_pymatgen
from matsimpy.adapters.ase import to_ase, from_ase
```

with:

```python
from matsimpy.io import to_pymatgen, from_pymatgen
from matsimpy.io import to_ase, from_ase
```

- [ ] **Step 2: Update LaTeX imports to the new public API**

In `tests/io/test_io_latex.py`, replace:

```python
from matsimpy.export.latex import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)
```

with:

```python
from matsimpy.io import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)
```

- [ ] **Step 3: Add public IO API export tests**

Create `tests/io/test_io_public_api.py`:

```python
"""Public API contract tests for matsimpy.io."""

import importlib


def test_io_exports_unified_public_api():
    import matsimpy.io as io

    expected = {
        "read",
        "write",
        "read_file",
        "write_file",
        "to_ase",
        "from_ase",
        "to_pymatgen",
        "from_pymatgen",
        "crystals_to_latex_table",
        "molecules_to_latex_table",
        "structures_to_latex_table",
        "save_latex_table",
    }
    assert expected <= set(io.__all__)
    for name in expected:
        assert hasattr(io, name)


def test_removed_public_packages_are_not_importable():
    for module_name in ("matsimpy.adapters", "matsimpy.export"):
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"{module_name} should not be public/importable")
```

- [ ] **Step 4: Run tests and verify expected failures**

Run:

```bash
python -m pytest tests/io/test_io_public_api.py tests/io/test_io_converters.py tests/io/test_io_latex.py -q
```

Expected: failures because `matsimpy.io` does not yet export conversion/LaTeX helpers and old packages still exist.

- [ ] **Step 5: Commit test changes after they fail for the expected reason**

```bash
git add tests/io/test_io_converters.py tests/io/test_io_latex.py tests/io/test_io_public_api.py
git commit -m "Lock the unified IO public API contract" -m "Constraint: adapters/export are being removed immediately from public API.
Confidence: high
Scope-risk: narrow
Directive: Keep third-party conversion and LaTeX exports under matsimpy.io only.
Tested: Targeted IO API tests fail before implementation for missing new exports and removed-package contract.
Not-tested: Full suite deferred until implementation."
```

## Task 2: Move Conversion and LaTeX Implementations into IO

**Files:**
- Modify: `matsimpy/io/ase.py`
- Create: `matsimpy/io/pymatgen.py`
- Create: `matsimpy/io/latex.py`
- Modify: `matsimpy/io/core.py`
- Modify: `matsimpy/io/__init__.py`

- [ ] **Step 1: Add object conversion functions to `matsimpy/io/ase.py`**

Copy the existing conversion logic from `matsimpy/adapters/ase.py` into `matsimpy/io/ase.py` below the file reader/writer functions:

```python
def to_ase(structure):
    """Convert MatSimPy Crystal or Molecule to an ASE Atoms object."""
    from ..core import Crystal, Molecule

    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from ase import Atoms
    except ImportError as exc:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install 'MatSimPy[io]'"
        ) from exc

    symbols = list(structure.species)
    if isinstance(structure, Crystal):
        return Atoms(
            symbols=symbols,
            positions=structure.cart_positions.tolist(),
            cell=structure.lattice.matrix,
            pbc=structure.pbc,
        )
    return Atoms(symbols=symbols, positions=structure.positions.tolist())


def from_ase(ase_atoms):
    """Convert an ASE Atoms object to a MatSimPy Crystal or Molecule."""
    from ..core import Crystal, Molecule, Lattice

    try:
        from ase import Atoms
    except ImportError as exc:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install 'MatSimPy[io]'"
        ) from exc

    if not isinstance(ase_atoms, Atoms):
        raise ValueError(f"Expected ASE Atoms object, got {type(ase_atoms)}")

    symbols = list(ase_atoms.get_chemical_symbols())
    positions = ase_atoms.get_positions().tolist()
    cell = ase_atoms.get_cell()
    pbc = ase_atoms.get_pbc()
    if cell is not None and cell.any() and any(pbc):
        return Crystal(
            symbols,
            positions,
            Lattice(cell.array),
            coords_are_cartesian=True,
            pbc=list(pbc),
        )
    return Molecule(symbols, positions)
```

Update `__all__` in `matsimpy/io/ase.py` to include:

```python
__all__ = ["read_ASE", "write_ASE", "to_ase", "from_ase"]
```

- [ ] **Step 2: Create `matsimpy/io/pymatgen.py`**

```python
"""pymatgen object conversion helpers for MatSimPy structures."""

from __future__ import annotations


def to_pymatgen(structure):
    """Convert MatSimPy Crystal or Molecule to a pymatgen object."""
    from ..core import Crystal, Molecule

    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError as exc:
        raise ImportError(
            "pymatgen is required for conversion. Install with: pip install 'MatSimPy[io]'"
        ) from exc

    if isinstance(structure, Crystal):
        return PymatgenStructure(
            structure.lattice.matrix,
            list(structure.species),
            structure.cart_positions.tolist(),
            coords_are_cartesian=True,
        )
    return PymatgenMolecule(list(structure.species), structure.positions.tolist())


def from_pymatgen(pymatgen_obj):
    """Convert pymatgen Structure or Molecule to a MatSimPy structure."""
    from ..core import Crystal, Molecule, Lattice

    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError as exc:
        raise ImportError(
            "pymatgen is required for conversion. Install with: pip install 'MatSimPy[io]'"
        ) from exc

    if isinstance(pymatgen_obj, PymatgenStructure):
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        return Crystal(
            species,
            pymatgen_obj.cart_coords.tolist(),
            Lattice(pymatgen_obj.lattice.matrix),
            coords_are_cartesian=True,
        )
    if isinstance(pymatgen_obj, PymatgenMolecule):
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        return Molecule(species, pymatgen_obj.cart_coords.tolist())

    raise ValueError(
        f"Unsupported pymatgen object type: {type(pymatgen_obj)}. "
        "Expected Structure or Molecule."
    )


__all__ = ["to_pymatgen", "from_pymatgen"]
```

- [ ] **Step 3: Create `matsimpy/io/latex.py`**

Move the full implementation from `matsimpy/export/latex.py` into `matsimpy/io/latex.py`. Keep the existing function names and `__all__`.

- [ ] **Step 4: Add file aliases in `matsimpy/io/core.py`**

At the end of `matsimpy/io/core.py`, add:

```python
read_file = read
write_file = write

__all__ = ["read", "write", "read_file", "write_file"]
```

- [ ] **Step 5: Export the unified API from `matsimpy/io/__init__.py`**

Add imports:

```python
from .core import read, write, read_file, write_file
from .ase import read_ASE, write_ASE, to_ase, from_ase
from .pymatgen import to_pymatgen, from_pymatgen
from .latex import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)
```

Add these names to `__all__`.

- [ ] **Step 6: Run IO tests**

Run:

```bash
python -m pytest tests/io/test_io_public_api.py tests/io/test_io_converters.py tests/io/test_io_latex.py -q
```

Expected: converter and LaTeX import tests pass except `test_removed_public_packages_are_not_importable`, which will still fail until old packages are deleted in Task 6.

- [ ] **Step 7: Commit IO migration**

```bash
git add matsimpy/io/ase.py matsimpy/io/pymatgen.py matsimpy/io/latex.py matsimpy/io/core.py matsimpy/io/__init__.py
git commit -m "Move conversion and LaTeX APIs into IO" -m "Constraint: matsimpy.io is the sole public boundary for conversion and export.
Rejected: New adapter/export wrapper packages | user requested immediate removal from public API.
Confidence: high
Scope-risk: moderate
Directive: Keep optional ASE/pymatgen imports lazy and error messages pointed at MatSimPy[io].
Tested: Targeted IO tests run; removed-package contract remains pending until old packages are deleted.
Not-tested: Full suite deferred."
```

## Task 3: Add Core File Convenience API

**Files:**
- Modify: `matsimpy/core/structure.py`
- Modify: `matsimpy/core/crystal.py`
- Modify: `matsimpy/core/molecule.py`
- Create: `tests/core/test_structure_file_api.py`

- [ ] **Step 1: Add failing tests**

Create `tests/core/test_structure_file_api.py`:

```python
"""Tests for Structure/Crystal/Molecule file convenience APIs."""

import pytest

from matsimpy.core import Crystal, Lattice, Molecule, Structure
from matsimpy.exceptions import StructureTypeError


def test_structure_from_file_returns_reader_result(tmp_path):
    path = tmp_path / "water.xyz"
    path.write_text("2\nwater\nH 0 0 0\nO 0 0 1\n")

    result = Structure.from_file(path)

    assert isinstance(result, Molecule)
    assert result.species == ("H", "O")


def test_structure_to_file_writes_with_registry(tmp_path):
    molecule = Molecule(["H", "O"], [[0, 0, 0], [0, 0, 1]])
    path = tmp_path / "water.xyz"

    molecule.to_file(path)

    assert path.exists()
    assert "H" in path.read_text()


def test_crystal_from_file_rejects_molecule_result(tmp_path):
    path = tmp_path / "water.xyz"
    path.write_text("2\nwater\nH 0 0 0\nO 0 0 1\n")

    with pytest.raises(StructureTypeError):
        Crystal.from_file(path)


def test_molecule_from_file_rejects_crystal_result(tmp_path):
    crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    path = tmp_path / "si.json"
    crystal.to_file(path, format="json")

    with pytest.raises(StructureTypeError):
        Molecule.from_file(path, format="json")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/core/test_structure_file_api.py -q
```

Expected: fails because `from_file` and `to_file` are not implemented.

- [ ] **Step 3: Implement `Structure.from_file()` and `Structure.to_file()`**

In `matsimpy/core/structure.py`, add methods on `Structure`:

```python
    @classmethod
    def from_file(cls, filename, format=None, **kwargs):
        """Read a structure from a file using matsimpy.io."""
        from ..io import read_file

        return read_file(filename, format=format, **kwargs)

    def to_file(self, filename, format=None, **kwargs) -> None:
        """Write this structure to a file using matsimpy.io."""
        from ..io import write_file

        write_file(self, filename, format=format, **kwargs)
```

- [ ] **Step 4: Implement typed subclass `from_file()` methods**

In `matsimpy/core/crystal.py`, add:

```python
    @classmethod
    def from_file(cls, filename, format=None, **kwargs) -> "Crystal":
        from ..exceptions import StructureTypeError
        from ..io import read_file

        structure = read_file(filename, format=format, **kwargs)
        if not isinstance(structure, cls):
            raise StructureTypeError(
                f"Expected Crystal from {filename!r}, got {type(structure).__name__}"
            )
        return structure
```

In `matsimpy/core/molecule.py`, add:

```python
    @classmethod
    def from_file(cls, filename, format=None, **kwargs) -> "Molecule":
        from ..exceptions import StructureTypeError
        from ..io import read_file

        structure = read_file(filename, format=format, **kwargs)
        if not isinstance(structure, cls):
            raise StructureTypeError(
                f"Expected Molecule from {filename!r}, got {type(structure).__name__}"
            )
        return structure
```

- [ ] **Step 5: Run file API tests**

Run:

```bash
python -m pytest tests/core/test_structure_file_api.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add matsimpy/core/structure.py matsimpy/core/crystal.py matsimpy/core/molecule.py tests/core/test_structure_file_api.py
git commit -m "Add structure file convenience APIs" -m "Constraint: Core methods must stay thin wrappers over matsimpy.io.
Confidence: high
Scope-risk: narrow
Directive: Do not duplicate IO registry dispatch inside core classes.
Tested: python -m pytest tests/core/test_structure_file_api.py -q
Not-tested: Full suite deferred."
```

## Task 4: Route Core Third-Party Conversion Methods Through IO

**Files:**
- Modify: `matsimpy/core/crystal.py`
- Modify: `matsimpy/core/molecule.py`
- Modify: `matsimpy/builders/bulk/random.py`
- Modify: `tests/io/test_io_converters.py`

- [ ] **Step 1: Update core conversion imports**

In `matsimpy/core/crystal.py`, replace imports inside conversion methods:

```python
from ..adapters.pymatgen import to_pymatgen
from ..adapters.ase import to_ase
from ..adapters.pymatgen import from_pymatgen
from ..adapters.ase import from_ase
```

with:

```python
from ..io import to_pymatgen
from ..io import to_ase
from ..io import from_pymatgen
from ..io import from_ase
```

Make the same replacement in `matsimpy/core/molecule.py`.

- [ ] **Step 2: Update builder import**

In `matsimpy/builders/bulk/random.py`, replace:

```python
from ...adapters.pymatgen import from_pymatgen
```

with:

```python
from ...io import from_pymatgen
```

- [ ] **Step 3: Add an import-boundary assertion**

Append to `tests/io/test_io_public_api.py`:

```python
def test_no_runtime_imports_from_removed_adapter_or_export_packages():
    import pathlib

    root = pathlib.Path("matsimpy")
    offenders = []
    for path in root.rglob("*.py"):
        if "adapters" in path.parts or "export" in path.parts:
            continue
        text = path.read_text()
        if "matsimpy.adapters" in text or "..adapters" in text or "...adapters" in text:
            offenders.append(str(path))
        if "matsimpy.export" in text or "..export" in text or "...export" in text:
            offenders.append(str(path))
    assert offenders == []
```

- [ ] **Step 4: Run conversion tests**

Run:

```bash
python -m pytest tests/io/test_io_public_api.py tests/io/test_io_converters.py -q
```

Expected: conversion tests pass. `test_removed_public_packages_are_not_importable` remains pending until Task 6. `test_no_runtime_imports_from_removed_adapter_or_export_packages` may still report `matsimpy/ai/skills/adapters.py` or `matsimpy/ai/skills/export.py` until Task 5 removes those old AI skill modules.

- [ ] **Step 5: Commit**

```bash
git add matsimpy/core/crystal.py matsimpy/core/molecule.py matsimpy/builders/bulk/random.py tests/io/test_io_public_api.py
git commit -m "Route core conversions through IO" -m "Constraint: Core convenience methods remain, but adapters package is no longer an implementation dependency.
Confidence: high
Scope-risk: narrow
Directive: Future optional conversion helpers belong under matsimpy.io.
Tested: python -m pytest tests/io/test_io_public_api.py tests/io/test_io_converters.py -q
Not-tested: Full suite deferred."
```

## Task 5: Replace AI Adapters/Export Skills with IO Skill

**Files:**
- Create: `matsimpy/ai/skills/io.py`
- Delete: `matsimpy/ai/skills/adapters.py`
- Delete: `matsimpy/ai/skills/export.py`
- Modify: `tests/ai/test_skill_loader.py`

- [ ] **Step 1: Update AI skill discovery tests**

In `tests/ai/test_skill_loader.py`, replace the assertions around lines 299-328 with:

```python
def test_discover_builtin_skills_includes_ai_coverage_expansion():
    skills = discover_builtin_skills()
    names = {s["name"] for s in skills}

    assert names >= {"calculator", "symmetry", "io"}
    assert "adapters" not in names
    assert "export" not in names


def test_new_ai_coverage_skills_have_expected_keywords_and_functions():
    skills = {s["name"]: s for s in discover_builtin_skills()}

    assert {"energy", "force", "calculator", "lj"} <= set(skills["calculator"]["keywords"])
    assert {"symmetry", "space group", "conventional"} <= set(skills["symmetry"]["keywords"])
    assert {"ase", "pymatgen", "convert", "latex", "read", "write"} <= set(skills["io"]["keywords"])

    calc_functions = {fn.name for fn in skills["calculator"]["functions"]}
    symmetry_functions = {fn.name for fn in skills["symmetry"]["functions"]}
    io_functions = {fn.name for fn in skills["io"]["functions"]}

    assert {"list_calculators", "calculate_lennard_jones", "write_calculator_input"} <= calc_functions
    assert {"analyze_symmetry", "get_conventional_cell"} <= symmetry_functions
    assert {
        "read_structure",
        "write_structure",
        "to_ase",
        "from_ase",
        "to_pymatgen",
        "from_pymatgen",
        "structures_to_latex_table",
        "save_latex_table",
    } <= io_functions
```

Also change the compact schema loop to:

```python
    for skill_name in ("calculator", "symmetry", "io"):
```

- [ ] **Step 2: Run AI skill tests and verify failure**

Run:

```bash
python -m pytest tests/ai/test_skill_loader.py -q
```

Expected: fails because `matsimpy/ai/skills/io.py` does not exist and old skills still exist.

- [ ] **Step 3: Create `matsimpy/ai/skills/io.py`**

```python
"""IO skill — read, write, convert, and export MatSimPy structures."""

from __future__ import annotations

from matsimpy.ai.executor import get_last_structure
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import sig_to_schema

SKILL_NAME = "io"
SKILL_DESCRIPTION = "Read, write, convert, and export MatSimPy structures"
SKILL_KEYWORDS: list[str] = [
    "io",
    "read",
    "write",
    "file",
    "save",
    "load",
    "ase",
    "pymatgen",
    "convert",
    "conversion",
    "latex",
    "table",
    "report",
]


def _require_structure(structure):
    if structure is not None:
        return structure
    structure = get_last_structure()
    if structure is None:
        raise ValueError("No structure available. Create or read a structure first.")
    return structure


def _default_structures(structures):
    if structures is not None:
        return structures
    return [_require_structure(None)]


def _summarize_external_object(obj):
    return {
        "type": type(obj).__name__,
        "module": type(obj).__module__,
        "repr": repr(obj)[:500],
    }


def _read_structure(path: str, format: str | None = None):
    from matsimpy.io import read_file

    return read_file(path, format=format)


def _write_structure(path: str, structure=None, format: str | None = None):
    from matsimpy.io import write_file

    structure = _require_structure(structure)
    write_file(structure, path, format=format)
    return {"saved_to": path, "format": format, "num_atoms": len(structure)}


def _to_ase(structure=None):
    from matsimpy.io import to_ase

    return _summarize_external_object(to_ase(_require_structure(structure)))


def _from_ase(ase_atoms):
    from matsimpy.io import from_ase

    return from_ase(ase_atoms)


def _to_pymatgen(structure=None):
    from matsimpy.io import to_pymatgen

    return _summarize_external_object(to_pymatgen(_require_structure(structure)))


def _from_pymatgen(pymatgen_obj):
    from matsimpy.io import from_pymatgen

    return from_pymatgen(pymatgen_obj)


def _structures_to_latex_table(
    structures=None,
    caption: str = "Structures",
    label: str = "tab:structures",
    separate_by_type: bool = True,
    use_mhchem: bool = False,
):
    from matsimpy.io import structures_to_latex_table

    return {
        "latex": structures_to_latex_table(
            _default_structures(structures),
            caption=caption,
            label=label,
            separate_by_type=separate_by_type,
            use_mhchem=use_mhchem,
        )
    }


def _save_latex_table(
    path: str,
    structures=None,
    caption: str | None = None,
    label: str | None = None,
    separate_by_type: bool = True,
    use_mhchem: bool = False,
):
    from matsimpy.io import save_latex_table

    structures = _default_structures(structures)
    save_latex_table(
        structures,
        path,
        caption=caption,
        label=label,
        separate_by_type=separate_by_type,
        use_mhchem=use_mhchem,
    )
    return {"saved_to": path, "format": "latex", "num_structures": len(structures)}


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef("read_structure", "Read a structure from a file", sig_to_schema(_read_structure), _read_structure, SKILL_NAME),
        FunctionDef("write_structure", "Write a structure to a file", sig_to_schema(_write_structure), _write_structure, SKILL_NAME),
        FunctionDef("to_ase", "Convert a MatSimPy structure to an ASE Atoms summary", sig_to_schema(_to_ase), _to_ase, SKILL_NAME),
        FunctionDef("from_ase", "Convert an ASE Atoms object to a MatSimPy structure", sig_to_schema(_from_ase), _from_ase, SKILL_NAME),
        FunctionDef("to_pymatgen", "Convert a MatSimPy structure to a pymatgen object summary", sig_to_schema(_to_pymatgen), _to_pymatgen, SKILL_NAME),
        FunctionDef("from_pymatgen", "Convert a pymatgen object to a MatSimPy structure", sig_to_schema(_from_pymatgen), _from_pymatgen, SKILL_NAME),
        FunctionDef("structures_to_latex_table", "Create a LaTeX table for structures", sig_to_schema(_structures_to_latex_table), _structures_to_latex_table, SKILL_NAME),
        FunctionDef("save_latex_table", "Save a LaTeX table for structures", sig_to_schema(_save_latex_table), _save_latex_table, SKILL_NAME),
    ]
```

- [ ] **Step 4: Delete old AI skill modules**

Delete:

```bash
git rm matsimpy/ai/skills/adapters.py matsimpy/ai/skills/export.py
```

- [ ] **Step 5: Run AI skill tests**

Run:

```bash
python -m pytest tests/ai/test_skill_loader.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add matsimpy/ai/skills/io.py tests/ai/test_skill_loader.py
git rm matsimpy/ai/skills/adapters.py matsimpy/ai/skills/export.py
git commit -m "Replace adapter and export AI skills with IO" -m "Constraint: AI tool surfaces must match the new public IO API.
Rejected: Keeping separate adapters/export skills | those packages are no longer public.
Confidence: high
Scope-risk: moderate
Directive: Add future read/write/convert/export AI helpers to the io skill.
Tested: python -m pytest tests/ai/test_skill_loader.py -q
Not-tested: Full AI runtime suite deferred."
```

## Task 6: Remove Old Public Packages

**Files:**
- Delete: `matsimpy/adapters/__init__.py`
- Delete: `matsimpy/adapters/ase.py`
- Delete: `matsimpy/adapters/pymatgen.py`
- Delete: `matsimpy/export/__init__.py`
- Delete: `matsimpy/export/latex.py`
- Modify: tests that still import removed packages

- [ ] **Step 1: Search for remaining old imports**

Run:

```bash
rg -n "matsimpy\\.adapters|matsimpy\\.export|\\.adapters|\\.export" matsimpy tests
```

Expected: only references inside files scheduled for deletion or tests asserting removal.

- [ ] **Step 2: Delete old packages**

Run:

```bash
git rm -r matsimpy/adapters matsimpy/export
```

- [ ] **Step 3: Run public API tests**

Run:

```bash
python -m pytest tests/io/test_io_public_api.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/io/test_io_public_api.py
git rm -r matsimpy/adapters matsimpy/export
git commit -m "Remove adapter and export public packages" -m "Constraint: User explicitly requested immediate public API removal.
Rejected: Deprecation wrappers | incompatible with the requested public API cleanup.
Confidence: high
Scope-risk: moderate
Directive: matsimpy.io owns all conversion and export APIs after this commit.
Tested: python -m pytest tests/io/test_io_public_api.py -q
Not-tested: Full suite deferred."
```

## Task 7: Fix Core Immutability and Cache Leaks

**Files:**
- Modify: `matsimpy/core/crystal.py`
- Modify: `matsimpy/core/molecule.py`
- Modify: `matsimpy/core/symmop.py`
- Modify: `tests/core/test_site_properties_validation.py`
- Modify: `tests/core/test_core_edge_cases.py`
- Create: `tests/core/test_symmop_immutability.py`

- [ ] **Step 1: Add sites leak tests**

Append to `tests/core/test_site_properties_validation.py`:

```python
def test_crystal_sites_returns_safe_snapshots():
    from matsimpy.core import Crystal, Lattice

    crystal = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5))
    leaked = crystal.sites
    leaked[0].specie = "K"
    leaked[0].position = [9, 9, 9]

    assert crystal.species == ("Na", "Cl")
    assert crystal.sites[0].specie == "Na"
    assert crystal.formula == "NaCl"


def test_molecule_sites_returns_safe_snapshots():
    from matsimpy.core import Molecule

    molecule = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])
    leaked = molecule.sites
    leaked[0].specie = "N"
    leaked[0].position = [9, 9, 9]

    assert molecule.species == ("C", "O")
    assert molecule.sites[0].specie == "C"
    assert molecule.formula == "CO"
```

- [ ] **Step 2: Add center-of-mass cache leak test**

Append to `tests/core/test_core_edge_cases.py`:

```python
def test_molecule_center_of_mass_return_value_does_not_mutate_cache():
    from matsimpy.core import Molecule

    molecule = Molecule(["H", "O"], [[0, 0, 0], [0, 0, 1]])
    com = molecule.get_center_of_mass()
    com[0] = 999

    assert molecule.get_center_of_mass()[0] != 999
```

- [ ] **Step 3: Add SymmOp mutation tests**

Create `tests/core/test_symmop_immutability.py`:

```python
"""Regression tests for SymmOp internal matrix safety."""

import numpy as np
import pytest

from matsimpy.core.symmop import SymmOp


def test_rotation_matrix_return_does_not_mutate_symmop():
    op = SymmOp.from_rotation_and_translation(np.eye(3), [1, 2, 3])
    rotation = op.rotation_matrix

    with pytest.raises(ValueError):
        rotation[0, 0] = 7

    assert op.rotation_matrix[0, 0] == 1


def test_translation_vector_return_does_not_mutate_symmop():
    op = SymmOp.from_rotation_and_translation(np.eye(3), [1, 2, 3])
    translation = op.translation_vector

    with pytest.raises(ValueError):
        translation[0] = 7

    assert op.translation_vector[0] == 1
```

- [ ] **Step 4: Run tests and verify failures**

Run:

```bash
python -m pytest tests/core/test_site_properties_validation.py tests/core/test_core_edge_cases.py tests/core/test_symmop_immutability.py -q
```

Expected: new tests fail for mutable `sites`, COM cache, or SymmOp views.

- [ ] **Step 5: Fix `Crystal.sites` and `Molecule.sites`**

In both `matsimpy/core/crystal.py` and `matsimpy/core/molecule.py`, change `sites` to return freshly built snapshot tuples. For `Crystal`, use:

```python
    @property
    def sites(self):
        """Return immutable tuple of site snapshots."""
        props = self.site_properties if self.site_properties else [{} for _ in self.species]
        return tuple(
            CrystalSite(
                position,
                specie,
                self.lattice,
                coords_are_cartesian=False,
                properties=prop,
            )
            for position, specie, prop in zip(self.frac_positions, self.species, props)
        )
```

For `Molecule`, use:

```python
    @property
    def sites(self):
        """Return immutable tuple of site snapshots."""
        props = self.site_properties if self.site_properties else [{} for _ in self.species]
        return tuple(
            Site(position, specie, properties=prop)
            for position, specie, prop in zip(self.positions, self.species, props)
        )
```

- [ ] **Step 6: Fix center-of-mass cache return**

In `matsimpy/core/molecule.py`, update `get_center_of_mass()` return statements so cached data is copied:

```python
        if self._cached_com is not None:
            return list(self._cached_com)
```

and after computing:

```python
        self._cached_com = center_of_mass.tolist()
        return list(self._cached_com)
```

- [ ] **Step 7: Fix SymmOp matrix safety**

In `matsimpy/core/symmop.py`, after validating `affine_matrix`, store it read-only:

```python
        self.affine_matrix = np.array(affine_matrix, dtype=float)
        if self.affine_matrix.shape != (4, 4):
            raise ValueError("Affine matrix must be 4x4")
        self.affine_matrix.flags.writeable = False
```

Update properties:

```python
    @property
    def rotation_matrix(self):
        result = self.affine_matrix[:3, :3].copy()
        result.flags.writeable = False
        return result

    @property
    def translation_vector(self):
        result = self.affine_matrix[:3, 3].copy()
        result.flags.writeable = False
        return result
```

- [ ] **Step 8: Run tests**

Run:

```bash
python -m pytest tests/core/test_site_properties_validation.py tests/core/test_core_edge_cases.py tests/core/test_symmop_immutability.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add matsimpy/core/crystal.py matsimpy/core/molecule.py matsimpy/core/symmop.py tests/core/test_site_properties_validation.py tests/core/test_core_edge_cases.py tests/core/test_symmop_immutability.py
git commit -m "Seal core mutable view leaks" -m "Constraint: Core structures promise immutable-return mutation semantics.
Rejected: Making Site globally immutable in this step | returning snapshots fixes the parent-structure leak with less API churn.
Confidence: high
Scope-risk: moderate
Directive: Do not expose cached Site objects or writable SymmOp matrix views.
Tested: python -m pytest tests/core/test_site_properties_validation.py tests/core/test_core_edge_cases.py tests/core/test_symmop_immutability.py -q
Not-tested: Full suite deferred."
```

## Task 8: Fix Substitute Index Validation

**Files:**
- Modify: `matsimpy/core/structure.py`
- Modify: `matsimpy/core/crystal.py`
- Modify: `matsimpy/core/molecule.py`
- Modify: `tests/core/test_structure_mutations.py`

- [ ] **Step 1: Add negative index tests**

Append to `tests/core/test_structure_mutations.py`:

```python
def test_molecule_substitute_rejects_negative_index():
    molecule = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])

    with pytest.raises(IndexError):
        molecule.substitute(-1, "N")

    with pytest.raises(IndexError):
        molecule.substitute([-1], ["N"])


def test_crystal_substitute_rejects_negative_index():
    crystal = Crystal(["Si", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5))

    with pytest.raises(IndexError):
        crystal.substitute(-1, "Ge")

    with pytest.raises(IndexError):
        crystal.substitute([-1], ["Ge"])
```

If the file lacks `pytest`, add:

```python
import pytest
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/core/test_structure_mutations.py -q
```

Expected: new negative-index tests fail before implementation.

- [ ] **Step 3: Add shared index validation helper**

In `matsimpy/core/structure.py`, add a private helper near mutation helpers:

```python
    def _validate_atom_indices(self, indices) -> list[int]:
        """Normalize and validate atom indices for mutation methods."""
        if isinstance(indices, int):
            normalized = [indices]
        else:
            normalized = list(indices)

        n_atoms = len(self.species)
        for idx in normalized:
            if not isinstance(idx, int):
                raise TypeError(f"Atom index must be an integer, got {type(idx)}")
            if idx < 0 or idx >= n_atoms:
                raise IndexError(f"Atom index {idx} out of range [0, {n_atoms})")
        return normalized
```

- [ ] **Step 4: Use helper in substitute implementations**

In `Structure.substitute`, `Crystal.substitute`, and `Molecule.substitute`, normalize selected indices through:

```python
indices_list = self._validate_atom_indices(indices)
```

For `AtomSelection`, call the helper after extracting indices:

```python
indices_list = self._validate_atom_indices(indices.indices)
```

Keep existing mismatched-length and dict mapping behavior unchanged.

- [ ] **Step 5: Run mutation tests**

Run:

```bash
python -m pytest tests/core/test_structure_mutations.py tests/core/test_substitution_dict_selection.py tests/core/test_atom_selection_class.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add matsimpy/core/structure.py matsimpy/core/crystal.py matsimpy/core/molecule.py tests/core/test_structure_mutations.py
git commit -m "Reject negative substitute indices" -m "Constraint: substitute index behavior must align with remove_atom.
Rejected: Supporting Python negative indices | it conflicts with existing remove_atom validation.
Confidence: high
Scope-risk: narrow
Directive: Reuse the shared mutation-index validator for future mutation APIs.
Tested: python -m pytest tests/core/test_structure_mutations.py tests/core/test_substitution_dict_selection.py tests/core/test_atom_selection_class.py -q
Not-tested: Full suite deferred."
```

## Task 9: Fix Calculator Offline Cache Semantics

**Files:**
- Modify: `matsimpy/calculator/base.py`
- Create: `tests/calculator/test_calculator_offline_cache.py`

- [ ] **Step 1: Add fake calculator tests**

Create `tests/calculator/test_calculator_offline_cache.py`:

```python
"""Regression tests for offline calculator result cache binding."""

from matsimpy.calculator.base import Calculator
from matsimpy.core import Molecule


class OfflineFakeCalculator(Calculator):
    def write_input(self, structure):
        self.written_hash = structure._structural_hash()

    def run_calculation(self):
        self.run_count = getattr(self, "run_count", 0) + 1

    def _parse_output(self):
        self.results = {
            "energy": 12.5,
            "forces": [[0.0, 0.0, 0.0]],
            "stress": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }


def test_read_results_preserves_hash_from_offline_calculate():
    structure = Molecule(["H"], [[0, 0, 0]])
    calc = OfflineFakeCalculator(run=False)
    structure.calc = calc

    calc.calculate(structure)
    calc.read_results()

    assert calc._last_structure_hash == structure._structural_hash()
    assert structure.get_potential_energy() == 12.5
    assert getattr(calc, "run_count", 0) == 0


def test_cached_offline_result_recomputes_for_different_structure():
    structure = Molecule(["H"], [[0, 0, 0]])
    other = Molecule(["H"], [[0, 0, 1]])
    calc = OfflineFakeCalculator(run=False)
    structure.calc = calc

    calc.calculate(structure)
    calc.read_results()
    other.calc = calc

    other.get_potential_energy()

    assert calc._last_structure_hash == other._structural_hash()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/calculator/test_calculator_offline_cache.py -q
```

Expected: at least one test fails if offline hash binding is incomplete.

- [ ] **Step 3: Make `calculate()` record hash before run mode branch**

In `matsimpy/calculator/base.py`, ensure `calculate()` sets:

```python
        self.structure = structure
        self._last_structure_hash = structure._structural_hash()
```

before the branch that skips `run_calculation()` when `run=False`.

- [ ] **Step 4: Keep `read_results()` hash conservative**

In `read_results()`, after `_parse_output()`, keep:

```python
        self._calculation_performed = True
```

Do not clear `_last_structure_hash`. If `self.structure` is set and `_last_structure_hash` is `None`, bind it:

```python
        if self.structure is not None and self._last_structure_hash is None:
            self._last_structure_hash = self.structure._structural_hash()
```

- [ ] **Step 5: Run calculator tests**

Run:

```bash
python -m pytest tests/calculator/test_calculator_offline_cache.py tests/calculator -q
```

Expected: all calculator tests pass.

- [ ] **Step 6: Commit**

```bash
git add matsimpy/calculator/base.py tests/calculator/test_calculator_offline_cache.py
git commit -m "Bind offline calculator results to structure hashes" -m "Constraint: run=False workflows must not make cached results look structure-agnostic.
Confidence: medium
Scope-risk: moderate
Directive: Calculator result caches must be invalidated by structure hash changes.
Tested: python -m pytest tests/calculator/test_calculator_offline_cache.py tests/calculator -q
Not-tested: External calculator executables."
```

## Task 10: Fix Element, Composition, Lattice, and Serialization Edge Cases

**Files:**
- Modify: `matsimpy/core/periodic_table.py`
- Modify: `matsimpy/core/composition.py`
- Modify: `tests/core/test_core_design_fixes.py`
- Modify: `tests/core/test_composition_parser.py`
- Modify: `tests/core/test_lattice_comprehensive.py`
- Modify: `tests/contracts/test_structure_model_contract.py`

- [ ] **Step 1: Add tests**

Add to `tests/core/test_core_design_fixes.py` as a new unittest class near the other Element tests:

```python
class TestElementInputValidation(unittest.TestCase):
    def test_element_get_element_rejects_non_string_inputs(self):
        with self.assertRaises(TypeError):
            Element.get_element(1)
        with self.assertRaises(TypeError):
            Element.get_element(None)
```

Add to `tests/core/test_composition_parser.py` inside `TestCompositionParserNested`:

```python
    def test_decimal_formula_counts_are_rejected_explicitly(self):
        with self.assertRaises(ValueError) as context:
            Composition("Fe0.5Ni0.5")
        self.assertIn("decimal", str(context.exception).lower())
```

Add to `tests/core/test_lattice_comprehensive.py` inside the class that already tests invalid lattice parameters:

```python
    def test_from_parameters_rejects_near_degenerate_angles(self):
        with self.assertRaises(ValueError):
            Lattice.from_parameters(1, 1, 1, 0.000001, 90, 90)

        with self.assertRaises(ValueError):
            Lattice.from_parameters(1, 1, 1, 179.999999, 90, 90)
```

Append to `tests/contracts/test_structure_model_contract.py`:

```python
def test_crystal_as_dict_roundtrip_uses_fractional_coordinates():
    from matsimpy.core import Crystal, Lattice
    import numpy as np

    lattice = Lattice.cubic(10)
    crystal = Crystal(["Si"], [[0.25, 0.25, 0.25]], lattice)
    data = crystal.as_dict()

    assert data["positions"] == [[0.25, 0.25, 0.25]]
    roundtrip = Crystal.from_dict(data)
    np.testing.assert_allclose(roundtrip.frac_positions, crystal.frac_positions)
    np.testing.assert_allclose(roundtrip.cart_positions, crystal.cart_positions)
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```bash
python -m pytest tests/core/test_core_design_fixes.py tests/core/test_composition_parser.py tests/core/test_lattice_comprehensive.py tests/contracts/test_structure_model_contract.py -q
```

Expected: Element and decimal-policy tests fail before implementation; lattice/serialization tests may already pass.

- [ ] **Step 3: Fix `Element.get_element()`**

In `matsimpy/core/periodic_table.py`, at the top of `Element.get_element`, add:

```python
        if not isinstance(symbol, str):
            raise TypeError(f"Element symbol must be a string, got {type(symbol)}")
```

- [ ] **Step 4: Make decimal rejection explicit**

In `matsimpy/core/composition.py`, near the start of `_parse_formula`, before the current allowed-character regex check, add:

```python
        if "." in formula:
            raise ValueError(
                "Decimal formula counts are not supported; use integer formula counts"
            )
```

- [ ] **Step 5: Stabilize lattice angle error behavior if needed**

If the new lattice tests fail with a non-`ValueError`, adjust `Lattice.from_parameters()` to reject near-degenerate angles explicitly:

```python
        min_angle = min(alpha, beta, gamma)
        max_angle = max(alpha, beta, gamma)
        if min_angle <= 1e-6 or max_angle >= 180 - 1e-6:
            raise ValueError("Lattice angles must be safely between 0 and 180 degrees")
```

Use the file's existing validation style if it already has an angle validation block.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m pytest tests/core/test_core_design_fixes.py tests/core/test_composition_parser.py tests/core/test_lattice_comprehensive.py tests/contracts/test_structure_model_contract.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add matsimpy/core/periodic_table.py matsimpy/core/composition.py matsimpy/core/lattice.py tests/core/test_core_design_fixes.py tests/core/test_composition_parser.py tests/core/test_lattice_comprehensive.py tests/contracts/test_structure_model_contract.py
git commit -m "Clarify core validation edge cases" -m "Constraint: Reported edge cases should become explicit core contracts.
Rejected: Adding decimal composition support now | broader fractional composition semantics need separate design.
Confidence: high
Scope-risk: narrow
Directive: Keep Crystal serialization tests focused on fractional coordinate round-trips.
Tested: python -m pytest tests/core/test_core_design_fixes.py tests/core/test_composition_parser.py tests/core/test_lattice_comprehensive.py tests/contracts/test_structure_model_contract.py -q
Not-tested: Full suite deferred."
```

## Task 11: Packaging and Runtime Contract Updates

**Files:**
- Modify: `tests/test_packaging_runtime_contracts.py`
- Modify: any docs/tests that still mention removed imports

- [ ] **Step 1: Search for stale public API names**

Run:

```bash
rg -n "matsimpy\\.adapters|matsimpy\\.export|adapters|export" README.md docs examples matsimpy tests pyproject.toml
```

Expected: only legitimate non-public wording remains. Update examples/tests that import removed packages to use `matsimpy.io`.

- [ ] **Step 2: Update packaging runtime contract**

In `tests/test_packaging_runtime_contracts.py`, update any public API assertions that mention adapters/export so they instead check `matsimpy.io` and AI `io` skill behavior.

Add a smoke test:

```python
def test_io_import_does_not_require_optional_converter_dependencies(monkeypatch):
    import builtins
    import importlib

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"ase", "pymatgen"}:
            raise ModuleNotFoundError(f"blocked optional dependency: {name}", name=name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    import matsimpy.io

    importlib.reload(matsimpy.io)
```

- [ ] **Step 3: Run packaging/runtime tests**

Run:

```bash
python -m pytest tests/test_packaging_runtime_contracts.py tests/ai/test_skill_loader.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_packaging_runtime_contracts.py README.md docs examples tests matsimpy
git commit -m "Update runtime contracts for IO API cleanup" -m "Constraint: Removed public APIs must not remain in examples or packaging contracts.
Confidence: high
Scope-risk: moderate
Directive: Public conversion/export documentation should point to matsimpy.io.
Tested: python -m pytest tests/test_packaging_runtime_contracts.py tests/ai/test_skill_loader.py -q
Not-tested: Full suite deferred."
```

## Task 12: Final Verification

**Files:**
- No planned source edits unless verification finds stale references or failures.

- [ ] **Step 1: Run stale import search**

Run:

```bash
rg -n "matsimpy\\.adapters|matsimpy\\.export|from \\.\\.adapters|from \\.\\.export|from \\.\\.\\.adapters|from \\.\\.\\.export" matsimpy tests docs examples README.md
```

Expected: no output.

- [ ] **Step 2: Run focused test groups**

Run:

```bash
python -m pytest tests/io tests/core tests/calculator/test_calculator_offline_cache.py tests/ai/test_skill_loader.py tests/test_packaging_runtime_contracts.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run full suite**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass; skipped optional-dependency tests are acceptable when extras are unavailable.

- [ ] **Step 4: Inspect final git state**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: clean worktree after final commits; recent commits reflect the task sequence.

- [ ] **Step 5: Final commit if verification required small fixes**

If verification required small fixes, commit with:

```bash
git add <changed-files>
git commit -m "Finish IO API cleanup verification fixes" -m "Constraint: Final changes are limited to stale references or test failures found during verification.
Confidence: high
Scope-risk: narrow
Directive: Keep public conversion/export imports under matsimpy.io.
Tested: python -m pytest -q
Not-tested: External optional dependency behavior beyond installed extras."
```

## Self-Review

- Spec coverage: covered IO public API, removed adapters/export, core file methods, core third-party wrappers, AI skill consolidation, stale internal imports, mutability/cache bugs, validation edge cases, and final verification.
- Placeholder scan: no unfinished-marker steps remain; each task has exact files, commands, and expected outcomes.
- Type consistency: uses existing `StructureTypeError`, `Crystal`, `Molecule`, `Lattice`, `Composition`, `Element`, and IO registry names consistently.
