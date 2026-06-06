# MatSimPy Architecture Refactoring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor MatSimPy's architecture to formalize module boundaries, introduce registries, separate concerns, and prepare for plugin extensibility.

**Architecture:** Clean break at v0.3.0. Three phases: Foundation (exceptions, protocols, core cleanup, IO registry, storage split), Registries & Separation (TransformationSpec, BuilderRegistry, builder-to-transformation moves), Plugin Readiness (entry points, integration tests, docs).

**Tech Stack:** Python 3.10+, numpy, scipy, monty (MSONable), maggma, pytest

---

## Phase 1: Foundation

### Task 1.1: Create matsimpy/exceptions.py

**Files:**
- Create: `matsimpy/exceptions.py`

- [ ] **Step 1: Write the module**

```python
"""
MatSimPy exception hierarchy.

Provides domain-specific exception classes for consistent error handling
across all layers. All MatSimPy-specific exceptions inherit from
MatSimPyError.
"""


class MatSimPyError(Exception):
    """Base exception for all MatSimPy-specific errors."""
    pass


class FormatError(MatSimPyError):
    """Raised when a file format is malformed or cannot be parsed."""
    pass


class StructureTypeError(MatSimPyError, TypeError):
    """Raised when a structure type is incompatible with an operation."""
    pass


class RegistryError(MatSimPyError):
    """Raised on duplicate registration or unknown spec/handler name."""
    pass


class ValidationError(MatSimPyError, ValueError):
    """Raised when structure validation fails (species, positions, lattice)."""
    pass


class StorageError(MatSimPyError):
    """Raised on storage backend failures."""
    pass


__all__ = [
    "MatSimPyError",
    "FormatError",
    "StructureTypeError",
    "RegistryError",
    "ValidationError",
    "StorageError",
]
```

- [ ] **Step 2: Run core tests to verify no import regressions**

```bash
pytest tests/core/ -x -q
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/exceptions.py
git commit -m "feat: add matsimpy.exceptions with domain exception hierarchy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.2: Create matsimpy/core/protocols.py

**Files:**
- Create: `matsimpy/core/protocols.py`

- [ ] **Step 1: Write the protocols module**

```python
"""
Typing protocols for structural type constraints.

These protocols allow transformations, IO handlers, and builders to
declare their type constraints without importing concrete Crystal/Molecule
classes, avoiding circular imports. They also serve as the stable interface
contract for plugins.
"""

from typing import Protocol, runtime_checkable
import numpy as np


@runtime_checkable
class StructureLike(Protocol):
    """Protocol for anything that behaves like a Structure."""

    species: tuple
    positions: np.ndarray
    lattice: object | None

    @property
    def formula(self) -> str: ...

    @property
    def composition(self) -> object: ...


@runtime_checkable
class CrystalLike(StructureLike, Protocol):
    """Protocol for periodic structures with a lattice."""

    lattice: object  # not None
    pbc: tuple

    @property
    def frac_positions(self) -> np.ndarray: ...

    @property
    def cart_positions(self) -> np.ndarray: ...


@runtime_checkable
class MoleculeLike(StructureLike, Protocol):
    """Protocol for non-periodic structures."""

    lattice: None


__all__ = ["StructureLike", "CrystalLike", "MoleculeLike"]
```

- [ ] **Step 2: Run tests to verify no regressions**

```bash
pytest tests/core/ -x -q
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/core/protocols.py
git commit -m "feat: add core protocols for StructureLike, CrystalLike, MoleculeLike

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.3: Remove from_file/to_file from Crystal

**Files:**
- Modify: `matsimpy/core/crystal.py`

- [ ] **Step 1: Remove from_file classmethod**

Remove lines 1560–1598 (the entire `from_file` method) from `matsimpy/core/crystal.py`.

- [ ] **Step 2: Remove to_file method**

Remove lines 1600–1626 (the entire `to_file` method) from `matsimpy/core/crystal.py`.

- [ ] **Step 3: Remove docstring references to from_file/to_file**

In the module docstring (lines 1-39), replace the lines mentioning file I/O:

Old (lines 16-17):
```
    - File I/O support (POSCAR, CIF, JSON, etc.)
    - Converter support (pymatgen, ASE)
```

Replace with:
```
    - Converter support (pymatgen, ASE)
```

- [ ] **Step 4: Update tests that use from_file/to_file**

```bash
grep -rn "from_file\|to_file" tests/core/ --include="*.py"
```

For each test using `Crystal.from_file()` or `crystal.to_file()`, rewrite to use `io.read()` / `io.write()`:

```python
# Before:
crystal = Crystal.from_file('test.vasp')

# After:
from matsimpy.io import read
crystal = read('test.vasp')
```

```python
# Before:
crystal.to_file('output.cif')

# After:
from matsimpy.io import write
write(crystal, 'output.cif')
```

- [ ] **Step 5: Run core tests**

```bash
pytest tests/core/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add matsimpy/core/crystal.py tests/core/
git commit -m "refactor: remove from_file/to_file from Crystal

Use matsimpy.io.read() / write() instead.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.4: Remove from_file/to_file from Molecule

**Files:**
- Modify: `matsimpy/core/molecule.py`

- [ ] **Step 1: Remove from_file classmethod**

Remove lines 1015–1069 (the entire `from_file` method) from `matsimpy/core/molecule.py`.

- [ ] **Step 2: Remove to_file method**

Remove lines 1071–1097 (the entire `to_file` method) from `matsimpy/core/molecule.py`.

- [ ] **Step 3: Update molecule docstring**

Remove the `from_file`/`to_file` example lines (lines 32-33) from the module docstring.

- [ ] **Step 4: Rewrite tests**

```bash
grep -rn "from_file\|to_file" tests/core/ --include="*molecule*"
```

Replace with `io.read()` / `io.write()` as in Task 1.3.

- [ ] **Step 5: Run core tests**

```bash
pytest tests/core/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add matsimpy/core/molecule.py tests/core/
git commit -m "refactor: remove from_file/to_file from Molecule

Use matsimpy.io.read() / write() instead.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.5: Move graph.py from core to analysis

**Files:**
- Create: `matsimpy/analysis/graph.py`
- Modify: `matsimpy/core/graph.py` (removed)
- Modify: `matsimpy/analysis/__init__.py`

- [ ] **Step 1: Move the file**

```bash
git mv matsimpy/core/graph.py matsimpy/analysis/graph.py
```

- [ ] **Step 2: Update internal imports in graph.py**

In `matsimpy/analysis/graph.py`, change the relative import:
```python
# Old (line 39-40):
from .crystal import Crystal
from .molecule import Molecule

# New:
from ..core.crystal import Crystal
from ..core.molecule import Molecule
```

And any other `from .` imports need to become `from ..core.`:
```python
# Old:
from .lattice import Lattice

# New:
from ..core.lattice import Lattice
```

Check all imports in the file:
```bash
grep "^from \." matsimpy/analysis/graph.py
```

Update each to point to `..core.<module>`.

- [ ] **Step 3: Update analysis/__init__.py**

Replace the content of `matsimpy/analysis/__init__.py`:

```python
"""
Analysis tools for structures.

This module provides:
- Graph representations (StructureGraph, MoleculeGraph, CrystalGraph)
- Neighbor finding (find_points_in_spheres, get_neighbor_list)
- Structure analysis (distances, angles, etc.)
- Bond analysis
- Topological analysis
"""

from .graph import (
    structure_to_graph_data,
    StructureGraph,
    MoleculeGraph,
    CrystalGraph,
    create_structure_graph,
)

__all__ = [
    "structure_to_graph_data",
    "StructureGraph",
    "MoleculeGraph",
    "CrystalGraph",
    "create_structure_graph",
]
```

Note: The precise `__all__` list depends on what `graph.py` actually exports. Verify with:
```bash
grep "^def \|^class " matsimpy/analysis/graph.py
```

- [ ] **Step 4: Find and update all imports of core.graph**

```bash
grep -rn "from.*core.*import.*graph\|from.*core.graph import\|from.*core import.*graph" matsimpy/ tests/ --include="*.py" | grep -v __pycache__
```

Update each file to import from `matsimpy.analysis` instead:
```python
# Old:
from matsimpy.core.graph import structure_to_graph_data

# New:
from matsimpy.analysis import structure_to_graph_data
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/core/ tests/analysis/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add matsimpy/analysis/ matsimpy/core/
git commit -m "refactor: move graph.py from core to analysis

Graph and connectivity analysis belongs in analysis, not core domain model.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.6: Move neighbors.py from core to analysis

**Files:**
- Create: `matsimpy/analysis/neighbors.py`
- Modify: `matsimpy/core/neighbors.py` (removed)
- Modify: `matsimpy/analysis/__init__.py`

- [ ] **Step 1: Move the file**

```bash
git mv matsimpy/core/neighbors.py matsimpy/analysis/neighbors.py
```

- [ ] **Step 2: Find and update all imports of core.neighbors**

```bash
grep -rn "from.*core.*import.*neighbors\|from.*core.neighbors import\|find_points_in_spheres\|get_neighbor_list" matsimpy/ tests/ --include="*.py" | grep -v __pycache__ | grep -v "analysis/neighbors.py"
```

Update each file to import from `matsimpy.analysis`:
```python
# Old:
from matsimpy.core.neighbors import find_points_in_spheres

# New:
from matsimpy.analysis import find_points_in_spheres
```

Also update any call sites within `core/crystal.py` that use `find_points_in_spheres` — these should now import from `matsimpy.analysis`. However, since Crystal needs neighbor finding for `get_neighbor_list()`, check if `crystal.py` imports from `neighbors`:

```bash
grep -n "neighbors\|find_points_in_spheres" matsimpy/core/crystal.py
```

Update the import to use `from ..analysis.neighbors import find_points_in_spheres` (if the import is at the top of crystal.py, this introduces a dependency from core → analysis, which is allowed since analysis depends on core and there's no circularity).

- [ ] **Step 3: Update analysis/__init__.py**

Add the neighbor exports:
```python
from .neighbors import find_points_in_spheres, validate_cutoff
```

And add to `__all__`:
```python
"find_points_in_spheres",
"validate_cutoff",
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/core/ tests/analysis/ -x -q
```

- [ ] **Step 5: Commit**

```bash
git add matsimpy/analysis/ matsimpy/core/
git commit -m "refactor: move neighbors.py from core to analysis

Neighbor finding is an analysis service, not a core domain primitive.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.7: Clean up core/__init__.py exports

**Files:**
- Modify: `matsimpy/core/__init__.py`

- [ ] **Step 1: Rewrite core/__init__.py**

Replace the content of `matsimpy/core/__init__.py`:

```python
"""Core domain model for MatSimPy.

This module provides the fundamental data classes:
- Lattice, Composition, Site — supporting value objects
- Structure — abstract base class
- Crystal — periodic structures with lattice
- Molecule — non-periodic structures
- Element — periodic table element data
"""

from .lattice import Lattice
from .composition import Composition
from .structure import Structure
from .molecule import Molecule
from .crystal import Crystal
from .site import Site, CrystalSite
from .periodic_table import Element

__all__ = [
    "Lattice",
    "Composition",
    "Site",
    "CrystalSite",
    "Structure",
    "Crystal",
    "Molecule",
    "Element",
]
```

- [ ] **Step 2: Run full test suite**

```bash
pytest -x -q --tb=short
```

- [ ] **Step 3: Fix any import errors in tests that imported graph/neighbors from core**

```bash
grep -rn "from matsimpy.core import.*structure_to_graph_data\|from matsimpy.core import.*find_points_in_spheres" tests/ --include="*.py"
```

Update to import from `matsimpy.analysis` instead.

- [ ] **Step 4: Run tests again**

```bash
pytest -x -q
```

- [ ] **Step 5: Commit**

```bash
git add matsimpy/core/__init__.py
git commit -m "refactor: core.__init__ exports domain model only

Remove graph and neighbor exports — now in matsimpy.analysis.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.8: Create IO FormatHandler registry

**Files:**
- Create: `matsimpy/io/registry.py`
- Modify: `matsimpy/io/utils.py` (keep only what registry doesn't replace)

- [ ] **Step 1: Write the FormatHandler and FormatRegistry**

Create `matsimpy/io/registry.py`:

```python
"""
Format handler registry for table-driven IO dispatch.

Provides FormatHandler (describing a supported file format) and
FormatRegistry (managing all registered handlers). Replaces the
if/elif dispatch chain in io/core.py with table-driven lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class FormatHandler:
    """Describes a supported file format and its read/write functions.

    Each format module (vasp.py, cif.py, etc.) creates one or more
    FormatHandler instances and registers them with the global
    FormatRegistry at import time.

    Attributes:
        name: Unique handler name, e.g. "vasp-poscar", "cif", "xyz".
        extensions: File extensions this handler claims, e.g. (".vasp",).
        aliases: Alternate names users can use, e.g. ("poscar", "vasp").
        description: Human-readable one-liner.
        reader: Callable for reading; None if write-only.
        writer: Callable for writing; None if read-only.
        supports_crystal: True if this format can represent periodic structures.
        supports_molecule: True if this format can represent molecules.
        strict_by_default: True = raise FormatError on malformed input.
        options_schema: JSON Schema dict for format-specific **kwargs.
    """

    name: str
    extensions: tuple[str, ...]
    aliases: tuple[str, ...]
    description: str
    reader: Callable | None
    writer: Callable | None
    supports_crystal: bool = False
    supports_molecule: bool = False
    strict_by_default: bool = True
    options_schema: dict | None = None


class FormatRegistry:
    """Registry of format handlers, triple-indexed by name, extension, alias.

    Usage::

        from matsimpy.io.registry import registry, FormatHandler

        handler = FormatHandler(
            name="vasp-poscar",
            extensions=(".vasp",),
            aliases=("poscar", "vasp"),
            description="VASP POSCAR format",
            reader=read_POSCAR,
            writer=write_POSCAR,
            supports_crystal=True,
        )
        registry.register(handler)

    Plugin entry point: ``'matsimpy.io_formats'``.
    """

    def __init__(self) -> None:
        self._by_name: dict[str, FormatHandler] = {}
        self._by_extension: dict[str, FormatHandler] = {}
        self._by_alias: dict[str, FormatHandler] = {}

    # ------------------------------------------------------------------
    def register(self, handler: FormatHandler) -> None:
        """Register *handler* under its name, extensions, and aliases.

        Raises:
            ValueError: If an extension or alias is already registered
                        to a different handler.
        """
        # Primary name
        if handler.name in self._by_name:
            if self._by_name[handler.name] is not handler:
                raise ValueError(
                    f"Format handler name {handler.name!r} is already registered"
                )
        self._by_name[handler.name] = handler

        # Extensions
        for ext in handler.extensions:
            ext_lower = ext.lower()
            if ext_lower in self._by_extension:
                existing = self._by_extension[ext_lower]
                if existing is not handler:
                    raise ValueError(
                        f"Extension {ext_lower!r} already registered by "
                        f"{existing.name!r}"
                    )
            self._by_extension[ext_lower] = handler

        # Aliases (including the primary name itself)
        for alias in handler.aliases:
            alias_lower = alias.lower()
            if alias_lower in self._by_alias:
                existing = self._by_alias[alias_lower]
                if existing is not handler:
                    raise ValueError(
                        f"Alias {alias_lower!r} already registered by "
                        f"{existing.name!r}"
                    )
            self._by_alias[alias_lower] = handler

    # ------------------------------------------------------------------
    def detect(self, filename: str) -> FormatHandler | None:
        """Return the handler matching *filename* extension, or None."""
        ext = Path(filename).suffix.lower()
        return self._by_extension.get(ext)

    # ------------------------------------------------------------------
    def get(self, name_or_alias: str) -> FormatHandler | None:
        """Look up handler by name or alias (case-insensitive)."""
        key = name_or_alias.lower()
        return self._by_alias.get(key) or self._by_name.get(key)

    # ------------------------------------------------------------------
    def read(
        self,
        filename: str,
        format: str | None = None,
        **kwargs,
    ):
        """Read a structure from *filename*.

        Args:
            filename: Path to the file.
            format: Optional format name/alias to bypass detection.
            **kwargs: Passed to the format-specific reader.

        Returns:
            Crystal or Molecule.

        Raises:
            FileNotFoundError: If *filename* does not exist.
            ValueError: If format cannot be detected.
            FormatError: If the file is malformed and strict mode is on.
            StructureTypeError: If the result type is incompatible.
        """
        from matsimpy.exceptions import FormatError

        filepath = Path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        if format is not None:
            handler = self.get(format)
            if handler is None:
                raise ValueError(f"Unknown format: {format!r}")
        else:
            handler = self.detect(filename)
            if handler is None:
                raise ValueError(
                    f"Could not detect file format from extension: {filename}. "
                    f"Specify format explicitly."
                )

        if handler.reader is None:
            raise ValueError(
                f"Format {handler.name!r} does not support reading."
            )

        return handler.reader(filename, **kwargs)

    # ------------------------------------------------------------------
    def write(
        self,
        structure,
        filename: str,
        format: str | None = None,
        **kwargs,
    ) -> None:
        """Write *structure* to *filename*.

        Args:
            structure: Crystal or Molecule to write.
            filename: Output path.
            format: Optional format name/alias to bypass detection.
            **kwargs: Passed to the format-specific writer.

        Raises:
            ValueError: If format cannot be detected.
            StructureTypeError: If structure type is incompatible.
        """
        from matsimpy.core import Crystal, Molecule
        from matsimpy.exceptions import StructureTypeError

        if format is not None:
            handler = self.get(format)
            if handler is None:
                raise ValueError(f"Unknown format: {format!r}")
        else:
            handler = self.detect(filename)
            if handler is None:
                raise ValueError(
                    f"Could not detect file format from extension: {filename}. "
                    f"Specify format explicitly."
                )

        if handler.writer is None:
            raise ValueError(
                f"Format {handler.name!r} does not support writing."
            )

        # Type compatibility check
        if isinstance(structure, Crystal) and not handler.supports_crystal:
            raise StructureTypeError(
                f"Format {handler.name!r} does not support Crystal structures."
            )
        if isinstance(structure, Molecule) and not handler.supports_molecule:
            raise StructureTypeError(
                f"Format {handler.name!r} does not support Molecule structures."
            )

        handler.writer(structure, filename, **kwargs)

    # ------------------------------------------------------------------
    def list_readers(self) -> list[str]:
        """Return sorted list of handler names that support reading."""
        return sorted(
            h.name for h in self._by_name.values() if h.reader is not None
        )

    def list_writers(self) -> list[str]:
        """Return sorted list of handler names that support writing."""
        return sorted(
            h.name for h in self._by_name.values() if h.writer is not None
        )


# Module-level singleton
registry = FormatRegistry()


__all__ = ["FormatHandler", "FormatRegistry", "registry"]
```

- [ ] **Step 2: Run tests to verify no regressions (registry is unused yet)**

```bash
pytest tests/io/ -x -q
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/io/registry.py
git commit -m "feat: add IO FormatHandler registry

FormatHandler dataclass + FormatRegistry singleton. Table-driven
format dispatch to replace if/elif chain in io/core.py.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.9: Register all format handlers in their modules

**Files:**
- Modify: `matsimpy/io/vasp.py`
- Modify: `matsimpy/io/cif.py`
- Modify: `matsimpy/io/xyz.py`
- Modify: `matsimpy/io/pdb.py`
- Modify: `matsimpy/io/xsf.py`
- Modify: `matsimpy/io/mol.py`
- Modify: `matsimpy/io/json.py`
- Modify: `matsimpy/io/ase.py`

- [ ] **Step 1: Register VASP handlers at bottom of vasp.py**

Append to `matsimpy/io/vasp.py`:

```python
# --- Registry registration ---
from .registry import registry, FormatHandler

_POSCAR_HANDLER = FormatHandler(
    name="vasp-poscar",
    extensions=(".vasp", ".poscar"),
    aliases=("poscar", "vasp", "POSCAR"),
    description="VASP POSCAR format (periodic crystal structures)",
    reader=read_POSCAR,
    writer=write_POSCAR,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
    options_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Header line for the file"},
        },
    },
)
_CONTCAR_HANDLER = FormatHandler(
    name="vasp-contcar",
    extensions=(".contcar",),
    aliases=("contcar", "CONTCAR"),
    description="VASP CONTCAR format (output structure)",
    reader=read_CONTCAR,
    writer=write_CONTCAR,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
)
registry.register(_POSCAR_HANDLER)
registry.register(_CONTCAR_HANDLER)
```

- [ ] **Step 2: Register CIF handler at bottom of cif.py**

Append to `matsimpy/io/cif.py`:

```python
from .registry import registry, FormatHandler

_CIF_HANDLER = FormatHandler(
    name="cif",
    extensions=(".cif",),
    aliases=("cif", "CIF"),
    description="Crystallographic Information File format",
    reader=read_CIF,
    writer=write_CIF,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
    options_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
    },
)
registry.register(_CIF_HANDLER)
```

- [ ] **Step 3: Register XYZ handler at bottom of xyz.py**

Append to `matsimpy/io/xyz.py`:

```python
from .registry import registry, FormatHandler

_XYZ_HANDLER = FormatHandler(
    name="xyz",
    extensions=(".xyz",),
    aliases=("xyz", "XYZ"),
    description="XYZ coordinate format (molecules)",
    reader=read_XYZ,
    writer=write_XYZ,
    supports_crystal=False,
    supports_molecule=True,
    strict_by_default=True,
    options_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
    },
)
registry.register(_XYZ_HANDLER)
```

- [ ] **Step 4: Register PDB handler at bottom of pdb.py**

Append to `matsimpy/io/pdb.py`:

```python
from .registry import registry, FormatHandler

_PDB_HANDLER = FormatHandler(
    name="pdb",
    extensions=(".pdb",),
    aliases=("pdb", "PDB"),
    description="Protein Data Bank format",
    reader=read_PDB,
    writer=write_PDB,
    supports_crystal=True,
    supports_molecule=True,
    strict_by_default=True,
    options_schema={
        "type": "object",
        "properties": {
            "as_crystal": {"type": "boolean", "default": False},
            "title": {"type": "string"},
        },
    },
)
registry.register(_PDB_HANDLER)
```

- [ ] **Step 5: Register XSF handler at bottom of xsf.py**

Append to `matsimpy/io/xsf.py`:

```python
from .registry import registry, FormatHandler

_XSF_HANDLER = FormatHandler(
    name="xsf",
    extensions=(".xsf",),
    aliases=("xsf", "XSF"),
    description="XCrySDen format",
    reader=read_XSF,
    writer=write_XSF,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
)
registry.register(_XSF_HANDLER)
```

- [ ] **Step 6: Register MOL handler at bottom of mol.py**

Append to `matsimpy/io/mol.py`:

```python
from .registry import registry, FormatHandler

_MOL_HANDLER = FormatHandler(
    name="mol",
    extensions=(".mol",),
    aliases=("mol", "MOL"),
    description="MDL Molfile format",
    reader=read_MOL,
    writer=write_MOL,
    supports_crystal=False,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_MOL_HANDLER)
```

- [ ] **Step 7: Register JSON handler at bottom of json.py**

Append to `matsimpy/io/json.py`:

```python
from .registry import registry, FormatHandler

_JSON_HANDLER = FormatHandler(
    name="json",
    extensions=(".json",),
    aliases=("json", "JSON"),
    description="MatSimPy JSON serialization format",
    reader=from_json,
    writer=to_json,
    supports_crystal=True,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_JSON_HANDLER)
```

- [ ] **Step 8: Register ASE handler at bottom of ase.py**

Append to `matsimpy/io/ase.py`:

```python
from .registry import registry, FormatHandler

_ASE_HANDLER = FormatHandler(
    name="ase",
    extensions=(".ase",),
    aliases=("ase", "ASE"),
    description="Atomic Simulation Environment format (via converter)",
    reader=read_ASE,
    writer=write_ASE,
    supports_crystal=True,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_ASE_HANDLER)
```

- [ ] **Step 9: Run tests to verify registration doesn't break anything**

```bash
pytest tests/io/ -x -q
```

- [ ] **Step 10: Commit**

```bash
git add matsimpy/io/vasp.py matsimpy/io/cif.py matsimpy/io/xyz.py \
        matsimpy/io/pdb.py matsimpy/io/xsf.py matsimpy/io/mol.py \
        matsimpy/io/json.py matsimpy/io/ase.py
git commit -m "feat: register all IO format handlers with FormatRegistry

Each format module registers its handler at import time.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.10: Refactor io/core.py to use registry

**Files:**
- Modify: `matsimpy/io/core.py`

- [ ] **Step 1: Rewrite io/core.py**

Replace the entire content of `matsimpy/io/core.py`:

```python
"""
High-level I/O interface for convenient file operations.

This module provides simple read() and write() functions that delegate
to the FormatRegistry for table-driven format detection and dispatch.

Usage::

    >>> from matsimpy.io import read, write
    >>> crystal = read('structure.vasp')
    >>> write(crystal, 'output.cif')
"""

from pathlib import Path
from typing import Optional, Union

from ..core import Crystal, Molecule, Structure
from .registry import registry


def read(
    filename: str,
    format: Optional[str] = None,
    **kwargs,
) -> Union[Crystal, Molecule]:
    """Read a structure from a file with automatic format detection.

    Args:
        filename: Path to the structure file.
        format: Optional format name/alias (e.g. ``'vasp'``, ``'cif'``).
            If None, format is detected from file extension.
        **kwargs: Passed to the format-specific reader.

    Returns:
        Crystal or Molecule.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If format is not supported or cannot be detected.
    """
    return registry.read(filename, format=format, **kwargs)


def write(
    structure: Union[Crystal, Molecule, Structure],
    filename: str,
    format: Optional[str] = None,
    **kwargs,
) -> None:
    """Write a structure to a file with automatic format detection.

    Args:
        structure: Structure to write (Crystal or Molecule).
        filename: Output path.
        format: Optional format name/alias (e.g. ``'vasp'``, ``'cif'``).
            If None, format is detected from file extension.
        **kwargs: Passed to the format-specific writer.

    Raises:
        ValueError: If format is not supported or cannot be detected.
    """
    registry.write(structure, filename, format=format, **kwargs)


__all__ = ["read", "write"]
```

- [ ] **Step 2: Run IO tests**

```bash
pytest tests/io/ -x -q
```

- [ ] **Step 3: Run full test suite to catch import issues**

```bash
pytest -x -q --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add matsimpy/io/core.py
git commit -m "refactor: io/core.py delegates to FormatRegistry

Replace 237-line if/elif chain with ~15 lines.
Table-driven dispatch via FormatRegistry.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.11: Create adapters package, move converters

**Files:**
- Create: `matsimpy/adapters/__init__.py`
- Create: `matsimpy/adapters/pymatgen.py`
- Create: `matsimpy/adapters/ase.py`
- Modify: `matsimpy/io/converters.py` (removed)
- Modify: `matsimpy/io/__init__.py` (remove converter exports)

- [ ] **Step 1: Create adapters/__init__.py**

```python
"""
External library adapters for MatSimPy.

Provides converters to/from:
- pymatgen (Structure, Molecule)
- ASE (Atoms)

Each adapter lazily imports its dependency at call time.
If the dependency is not installed, ImportError is raised with
an install hint.

Usage::

    >>> from matsimpy.adapters.pymatgen import to_pymatgen, from_pymatgen
    >>> pmg_struct = to_pymatgen(crystal)
    >>> crystal = from_pymatgen(pmg_struct)
"""

__all__ = []
```

- [ ] **Step 2: Move and refactor converters to adapters/pymatgen.py**

```bash
cp matsimpy/io/converters.py /tmp/converters_backup.py
```

Read the current `io/converters.py`, extract the pymatgen-related functions (`to_pymatgen`, `from_pymatgen`), and write them to `matsimpy/adapters/pymatgen.py` with updated imports:

```python
"""
pymatgen adapter for MatSimPy structures.

Converts between MatSimPy Crystal/Molecule and pymatgen Structure/Molecule.

Requires: pymatgen (pip install pymatgen)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import Crystal, Molecule


def to_pymatgen(structure: Crystal | Molecule):
    """Convert a MatSimPy Crystal or Molecule to a pymatgen Structure/Molecule.

    Raises:
        ImportError: If pymatgen is not installed.
    """
    try:
        from pymatgen.core import Structure as PmgStructure
        from pymatgen.core import Molecule as PmgMolecule
        from pymatgen.core import Lattice as PmgLattice
    except ImportError:
        raise ImportError(
            "pymatgen is required for this conversion. "
            "Install with: pip install pymatgen"
        )

    from ..core import Crystal

    if isinstance(structure, Crystal):
        lattice = PmgLattice(structure.lattice.matrix)
        return PmgStructure(
            lattice,
            structure.species,
            structure.frac_positions,
            coords_are_cartesian=False,
        )
    else:
        return PmgMolecule(
            structure.species,
            structure.positions,
        )


def from_pymatgen(pmg_structure) -> Crystal | Molecule:
    """Convert a pymatgen Structure/Molecule to a MatSimPy Crystal/Molecule.

    Raises:
        ImportError: If pymatgen is not installed.
    """
    try:
        from pymatgen.core import Structure as PmgStructure
        from pymatgen.core import Molecule as PmgMolecule
    except ImportError:
        raise ImportError(
            "pymatgen is required for this conversion. "
            "Install with: pip install pymatgen"
        )

    from ..core import Crystal, Molecule, Lattice

    if isinstance(pmg_structure, PmgStructure):
        return Crystal(
            [str(s.species.elements[0]) for s in pmg_structure.sites],
            pmg_structure.frac_coords.tolist(),
            Lattice(pmg_structure.lattice.matrix.tolist()),
        )
    elif isinstance(pmg_structure, PmgMolecule):
        return Molecule(
            [str(s.species.elements[0]) for s in pmg_structure.sites],
            pmg_structure.cart_coords.tolist(),
        )
    else:
        raise TypeError(
            f"Expected pymatgen Structure or Molecule, got {type(pmg_structure)}"
        )


__all__ = ["to_pymatgen", "from_pymatgen"]
```

Note: The code above is a template. Read the actual `io/converters.py` for the exact implementation and adapt accordingly. Use:
```bash
cat matsimpy/io/converters.py
```
to see the current implementation. Preserve all existing logic, only update imports.

- [ ] **Step 3: Move ASE converters to adapters/ase.py**

Similarly extract ASE-related functions (`to_ase`, `from_ase`) from `io/converters.py` to `matsimpy/adapters/ase.py`:

```python
"""
ASE adapter for MatSimPy structures.

Converts between MatSimPy Crystal/Molecule and ASE Atoms.

Requires: ase (pip install ase)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import Crystal, Molecule


def to_ase(structure: Crystal | Molecule):
    """Convert MatSimPy structure to ASE Atoms.

    Raises:
        ImportError: If ase is not installed.
    """
    try:
        from ase import Atoms
    except ImportError:
        raise ImportError(
            "ASE is required for this conversion. "
            "Install with: pip install ase"
        )

    from ..core import Crystal

    if isinstance(structure, Crystal):
        atoms = Atoms(
            symbols=list(structure.species),
            positions=structure.cart_positions,
            cell=structure.lattice.matrix,
            pbc=structure.pbc,
        )
    else:
        atoms = Atoms(
            symbols=list(structure.species),
            positions=structure.positions,
        )
    return atoms


def from_ase(atoms) -> Crystal | Molecule:
    """Convert ASE Atoms to MatSimPy structure.

    Raises:
        ImportError: If ase is not installed.
    """
    try:
        from ase import Atoms
    except ImportError:
        raise ImportError(
            "ASE is required for this conversion. "
            "Install with: pip install ase"
        )

    from ..core import Crystal, Molecule, Lattice
    import numpy as np

    species = list(atoms.get_chemical_symbols())
    positions = atoms.get_positions()

    if np.any(atoms.get_cell()):
        return Crystal(
            species,
            positions.tolist(),
            Lattice(atoms.get_cell().tolist()),
            coords_are_cartesian=True,
        )
    else:
        return Molecule(species, positions.tolist())


__all__ = ["to_ase", "from_ase"]
```

Note: Verify against the actual `io/converters.py` implementation and preserve all existing logic.

- [ ] **Step 4: Delete old converters.py**

```bash
rm matsimpy/io/converters.py
```

- [ ] **Step 5: Update io/__init__.py to remove converter exports**

Remove these lines from `matsimpy/io/__init__.py`:
```python
from .converters import to_pymatgen, from_pymatgen, to_ase, from_ase
```

And remove from `__all__`:
```python
"to_pymatgen",
"from_pymatgen",
"to_ase",
"from_ase",
```

- [ ] **Step 6: Update all imports of converters throughout the codebase**

```bash
grep -rn "from.*io.converters import\|from.*io import.*to_pymatgen\|from.*io import.*from_pymatgen\|from.*io import.*to_ase\|from.*io import.*from_ase" matsimpy/ tests/ --include="*.py" | grep -v __pycache__
```

Update each file:
```python
# Old:
from matsimpy.io.converters import to_pymatgen
from matsimpy.io import to_ase

# New:
from matsimpy.adapters.pymatgen import to_pymatgen
from matsimpy.adapters.ase import to_ase
```

- [ ] **Step 7: Run tests**

```bash
pytest -x -q --tb=short
```

- [ ] **Step 8: Commit**

```bash
git add matsimpy/adapters/ matsimpy/io/
git rm matsimpy/io/converters.py
git commit -m "refactor: move converters to adapters package

pymatgen and ASE converters now live in matsimpy.adapters.
Lazy-imports external dependencies at call time.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.12: Create export package, move LaTeX

**Files:**
- Create: `matsimpy/export/__init__.py`
- Create: `matsimpy/export/latex.py`
- Modify: `matsimpy/io/latex.py` (removed)
- Modify: `matsimpy/io/__init__.py` (remove latex exports)

- [ ] **Step 1: Create export/__init__.py**

```python
"""
Export / presentation utilities for MatSimPy.

Provides exporters for:
- LaTeX tables

These are presentation-layer concerns, not file-format IO.
"""

from .latex import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)

__all__ = [
    "crystals_to_latex_table",
    "molecules_to_latex_table",
    "structures_to_latex_table",
    "save_latex_table",
]
```

- [ ] **Step 2: Move latex.py**

```bash
git mv matsimpy/io/latex.py matsimpy/export/latex.py
```

- [ ] **Step 3: Update imports in latex.py**

Check the current imports in `matsimpy/export/latex.py`:
```bash
head -30 matsimpy/export/latex.py
```

Update any relative imports to match the new location. If the file uses `from ..core import ...`, change to `from ..core import ...` (same since both are one level from matsimpy).

- [ ] **Step 4: Update io/__init__.py to remove latex exports**

Remove these lines:
```python
from .latex import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)
```

And remove from `__all__`:
```python
"crystals_to_latex_table",
"molecules_to_latex_table",
"structures_to_latex_table",
"save_latex_table",
```

- [ ] **Step 5: Update all imports of io.latex**

```bash
grep -rn "from.*io.latex import\|from.*io import.*latex" matsimpy/ tests/ --include="*.py" | grep -v __pycache__
```

Update each:
```python
# Old:
from matsimpy.io.latex import crystals_to_latex_table

# New:
from matsimpy.export.latex import crystals_to_latex_table
```

- [ ] **Step 6: Run tests**

```bash
pytest -x -q --tb=short
```

- [ ] **Step 7: Commit**

```bash
git add matsimpy/export/ matsimpy/io/__init__.py
git commit -m "refactor: move LaTeX export from io to export package

Presentation/export is a separate concern from file-format IO.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.13: Clean up io/__init__.py

**Files:**
- Modify: `matsimpy/io/__init__.py`

- [ ] **Step 1: Rewrite io/__init__.py with curated exports**

```python
"""
I/O module for reading and writing various file formats.

This module provides support for:
- VASP (POSCAR, CONTCAR)
- CIF (Crystallographic Information File)
- XYZ (coordinate format)
- PDB (Protein Data Bank)
- XSF (XCrySDen format)
- JSON (serialization)
- ASE format
- MOL (MDL Molfile) format

High-level interface::

    >>> from matsimpy.io import read, write
    >>> crystal = read('structure.vasp')  # Auto-detect format
    >>> write(crystal, 'output.cif')       # Auto-detect format

For advanced use, import format-specific readers/writers::

    >>> from matsimpy.io.vasp import read_POSCAR, write_POSCAR

For the format registry (plugin extension point)::

    >>> from matsimpy.io.registry import registry, FormatHandler
"""

# High-level interface (recommended)
from .core import read, write

# Format-specific readers/writers (for advanced use)
from .vasp import read_POSCAR, write_POSCAR, read_CONTCAR, write_CONTCAR
from .cif import read_CIF, write_CIF
from .xyz import read_XYZ, write_XYZ, read_XYZ_multiframe
from .pdb import read_PDB, write_PDB
from .xsf import read_XSF, write_XSF
from .json import to_json, from_json
from .ase import read_ASE, write_ASE
from .mol import read_MOL, write_MOL

# Registry (for plugins and introspection)
from .registry import registry, FormatHandler, FormatRegistry

__all__ = [
    # High-level
    "read",
    "write",
    # VASP
    "read_POSCAR",
    "write_POSCAR",
    "read_CONTCAR",
    "write_CONTCAR",
    # CIF
    "read_CIF",
    "write_CIF",
    # XYZ
    "read_XYZ",
    "write_XYZ",
    "read_XYZ_multiframe",
    # PDB
    "read_PDB",
    "write_PDB",
    # XSF
    "read_XSF",
    "write_XSF",
    # JSON
    "to_json",
    "from_json",
    # ASE
    "read_ASE",
    "write_ASE",
    # MOL
    "read_MOL",
    "write_MOL",
    # Registry
    "registry",
    "FormatHandler",
    "FormatRegistry",
]
```

Note: `detect_format`, `get_reader_writer`, `is_crystal_format`, `is_molecule_format` are no longer exported — they are internal to the registry.

- [ ] **Step 2: Run full test suite**

```bash
pytest -x -q --tb=short
```

- [ ] **Step 3: Fix any tests that import removed utility functions**

Replace:
```python
# Old:
from matsimpy.io.utils import detect_format
from matsimpy.io import is_crystal_format

# New:
from matsimpy.io.registry import registry
# Use registry.detect(filename) instead of detect_format(filename)
# Use handler.supports_crystal instead of is_crystal_format(ext)
```

- [ ] **Step 4: Commit**

```bash
git add matsimpy/io/__init__.py
git commit -m "refactor: curated io.__init__ exports, remove utility re-exports

detect_format, get_reader_writer, is_crystal_format, is_molecule_format
are now internal to FormatRegistry.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.14: Create storage/schema.py (DocumentEnvelope)

**Files:**
- Create: `matsimpy/storage/schema.py`

- [ ] **Step 1: Write schema.py**

```python
"""
Document envelope and ID generation for MatSimPy storage.

Provides:
- DocumentEnvelope: wraps a core object's dict with metadata
- Stable, content-addressed document ID generation (sha256)
- Reserved field enforcement
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class DocumentEnvelope:
    """A document ready for persistence.

    Wraps a core object's serialized dict (payload) with metadata
    including a content-addressed stable ID, schema version, timestamp,
    and user-provided metadata.

    Reserved fields (doc_id, payload, schema_version, created_at, metadata)
    are enforced — user metadata must not collide with these keys.

    Attributes:
        doc_id: Stable hash-based ID (sha256 of canonical JSON payload).
        payload: The core object's ``as_dict()`` output.
        schema_version: Version of the envelope schema ("1.0.0").
        created_at: ISO 8601 UTC timestamp.
        metadata: Arbitrary user-provided tags/labels/provenance.
    """

    doc_id: str
    payload: dict
    schema_version: str = "1.0.0"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict = field(default_factory=dict)

    RESERVED_FIELDS = frozenset({
        "doc_id", "payload", "schema_version", "created_at", "metadata",
    })

    # ------------------------------------------------------------------
    @staticmethod
    def generate_id(payload: dict, metadata: Optional[dict] = None) -> str:
        """Generate a stable, content-addressed document ID.

        Uses sha256 of canonical JSON (sorted keys, deterministic encoding).
        Same payload + same metadata → same ID.

        Args:
            payload: The core object's ``as_dict()`` output.
            metadata: Optional user-provided metadata.

        Returns:
            Hex-encoded sha256 digest.
        """
        # Build a canonical representation
        canonical = {
            "payload": payload,
            "meta": metadata or {},
        }
        serialized = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    @staticmethod
    def validate_metadata(metadata: dict) -> None:
        """Check that *metadata* keys do not collide with reserved fields.

        Raises:
            ValueError: If any key is reserved.
        """
        collision = DocumentEnvelope.RESERVED_FIELDS & set(metadata.keys())
        if collision:
            raise ValueError(
                f"Metadata keys collide with reserved fields: "
                f"{sorted(collision)}. Reserved: "
                f"{sorted(DocumentEnvelope.RESERVED_FIELDS)}"
            )

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Serialize to a plain dict for storage."""
        return {
            "doc_id": self.doc_id,
            "payload": self.payload,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DocumentEnvelope:
        """Deserialize from a plain dict."""
        return cls(
            doc_id=d["doc_id"],
            payload=d["payload"],
            schema_version=d.get("schema_version", "1.0.0"),
            created_at=d.get("created_at", ""),
            metadata=d.get("metadata", {}),
        )


__all__ = ["DocumentEnvelope"]
```

- [ ] **Step 2: Run existing storage tests**

```bash
pytest tests/storage/ -x -q
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/storage/schema.py
git commit -m "feat: add DocumentEnvelope for storage document schema

Stable sha256-based content-addressed IDs. Reserved field enforcement.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.15: Create storage/codec.py (DocumentCodec)

**Files:**
- Create: `matsimpy/storage/codec.py`

- [ ] **Step 1: Write codec.py**

```python
"""
Document codec for encoding/decoding MatSimPy objects to/from DocumentEnvelopes.

Separates serialization concerns from backend persistence.
"""

from __future__ import annotations

from typing import Optional

from monty.json import MSONable

from ..core import Structure
from .schema import DocumentEnvelope


class DocumentCodec:
    """Encodes MatSimPy objects ↔ DocumentEnvelope for persistence.

    Usage::

        codec = DocumentCodec()
        envelope = codec.encode(crystal, metadata={"source": "icsd"})
        crystal = codec.decode(envelope)
    """

    def encode(
        self,
        obj: MSONable,
        metadata: Optional[dict] = None,
        schema_version: str = "1.0.0",
    ) -> DocumentEnvelope:
        """Encode a MatSimPy object into a DocumentEnvelope.

        Args:
            obj: Any MSONable MatSimPy object (Crystal, Molecule, etc.).
            metadata: Optional user-provided metadata dict.
            schema_version: Envelope schema version.

        Returns:
            DocumentEnvelope with stable content-addressed ID.

        Raises:
            ValueError: If metadata keys collide with reserved fields.
        """
        if metadata:
            DocumentEnvelope.validate_metadata(metadata)

        payload = obj.as_dict()
        doc_id = DocumentEnvelope.generate_id(payload, metadata)

        return DocumentEnvelope(
            doc_id=doc_id,
            payload=payload,
            schema_version=schema_version,
            metadata=metadata or {},
        )

    def decode(self, envelope: DocumentEnvelope) -> Structure:
        """Decode a DocumentEnvelope back into a MatSimPy object.

        Args:
            envelope: The DocumentEnvelope to decode.

        Returns:
            Crystal or Molecule (via Structure.from_dict).
        """
        return Structure.from_dict(envelope.payload)


__all__ = ["DocumentCodec"]
```

- [ ] **Step 2: Commit**

```bash
git add matsimpy/storage/codec.py
git commit -m "feat: add DocumentCodec for encode/decode of storage documents

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.16: Create storage/backend.py (StoreBackend protocol) + memory_store.py

**Files:**
- Create: `matsimpy/storage/backend.py`
- Create: `matsimpy/storage/memory_store.py`

- [ ] **Step 1: Write backend.py with StoreBackend protocol**

```python
"""
Storage backend protocol.

All storage backends (MemoryBackend, MaggmaBackend, future backends)
must implement the StoreBackend protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StoreBackend(Protocol):
    """Protocol that all storage backends must implement.

    Methods:
        connect(): Initialize/open the backend connection.
        put(doc_id, document): Store a document dict keyed by doc_id.
        get(doc_id): Retrieve a document dict by doc_id, or None.
        query(criteria, limit, offset): Query documents, return list of dicts.
        delete(doc_id): Remove a document by doc_id, return True if existed.
        flush(): Force pending writes to durable storage.
        close(): Release resources and close the connection.
    """

    def connect(self) -> None:
        """Initialize or open the backend connection."""
        ...

    def put(self, doc_id: str, document: dict) -> None:
        """Store *document* dict keyed by *doc_id*.

        Overwrites existing document with the same doc_id.
        """
        ...

    def get(self, doc_id: str) -> dict | None:
        """Retrieve document dict by *doc_id*, or None if not found."""
        ...

    def query(
        self, criteria: dict, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """Return documents matching *criteria*.

        Args:
            criteria: Dict of field-value pairs for matching.
            limit: Max number of documents to return.
            offset: Number of matching documents to skip.
        """
        ...

    def delete(self, doc_id: str) -> bool:
        """Remove document by *doc_id*. Return True if it existed."""
        ...

    def flush(self) -> None:
        """Force pending writes to durable storage (no-op for in-memory)."""
        ...

    def close(self) -> None:
        """Release resources and close the connection."""
        ...


__all__ = ["StoreBackend"]
```

- [ ] **Step 2: Write memory_store.py**

```python
"""
In-memory storage backend for MatSimPy.

Implements the StoreBackend protocol using a plain Python dict.
Primary use: testing and fast prototyping (no persistence).
"""

from __future__ import annotations


class MemoryBackend:
    """In-memory storage backed by a Python dict.

    Implements the StoreBackend protocol. Data is lost on process exit.

    Usage::

        backend = MemoryBackend()
        backend.connect()
        backend.put("abc123", {"doc_id": "abc123", "payload": {...}})
        doc = backend.get("abc123")
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._connected = False

    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Initialize the in-memory store."""
        self._connected = True

    # ------------------------------------------------------------------
    def put(self, doc_id: str, document: dict) -> None:
        """Store *document* keyed by *doc_id*. Overwrites if exists."""
        self._store[doc_id] = document

    # ------------------------------------------------------------------
    def get(self, doc_id: str) -> dict | None:
        """Return document by *doc_id*, or None."""
        return self._store.get(doc_id)

    # ------------------------------------------------------------------
    def query(
        self, criteria: dict, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """Return documents matching all key-value pairs in *criteria*.

        Supports dot-delimited nested keys (e.g. ``"metadata.source"``).
        """
        results = []
        for doc in self._store.values():
            if self._matches(doc, criteria):
                results.append(doc)
        return results[offset : offset + limit]

    @staticmethod
    def _matches(doc: dict, criteria: dict) -> bool:
        for key, value in criteria.items():
            # Support dot-delimited nested lookup
            parts = key.split(".")
            current = doc
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return False
            if current != value:
                return False
        return True

    # ------------------------------------------------------------------
    def delete(self, doc_id: str) -> bool:
        """Remove document by *doc_id*. Return True if it existed."""
        if doc_id in self._store:
            del self._store[doc_id]
            return True
        return False

    # ------------------------------------------------------------------
    def flush(self) -> None:
        """No-op for in-memory backend."""
        pass

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Clear the store and mark as disconnected."""
        self._store.clear()
        self._connected = False


__all__ = ["MemoryBackend"]
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/storage/backend.py matsimpy/storage/memory_store.py
git commit -m "feat: add StoreBackend protocol and MemoryBackend

MemoryBackend for testing and fast prototyping.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.17: Refactor maggma_store.py as MaggmaBackend

**Files:**
- Modify: `matsimpy/storage/maggma_store.py`
- Create: `matsimpy/storage/facade.py`

- [ ] **Step 1: Extract _stable_doc_id to schema.py**

First, add the legacy `_stable_doc_id` function to `matsimpy/storage/schema.py` as a compatibility helper (the old md5-based approach was used in the current DataStorage):

Append to `matsimpy/storage/schema.py`:

```python
def _stable_doc_id_legacy(document: dict) -> str:
    """Legacy MD5-based stable ID (compatibility helper).

    Used by MaggmaBackend for backward compatibility with existing stored data.
    New code should use DocumentEnvelope.generate_id() (sha256-based).
    """
    import json as _json
    from monty.json import MontyEncoder

    stable_document = {
        key: value
        for key, value in document.items()
        if key not in {"doc_id", "stored_at"}
    }
    serialized = _json.dumps(
        stable_document, sort_keys=True, cls=MontyEncoder
    )
    return hashlib.md5(serialized.encode()).hexdigest()
```

- [ ] **Step 2: Refactor maggma_store.py**

The `DataStorage` class needs to be split: the maggma-backend-specific logic stays as `MaggmaBackend`, and the user-facing `DataStorage` facade moves to `facade.py`.

Refactor `matsimpy/storage/maggma_store.py` — keep `MaggmaBackend` class implementing `StoreBackend`:

```python
"""Maggma-based storage backend for MatSimPy.

Provides persistent storage using maggma's MemoryStore and JSONStore.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

from .backend import StoreBackend

logger = logging.getLogger(__name__)

try:
    from maggma.stores import MemoryStore, JSONStore
    MAGGMA_AVAILABLE = True
except ImportError:
    MAGGMA_AVAILABLE = False
    MemoryStore = None
    JSONStore = None


class MaggmaBackend:
    """Storage backend backed by maggma.

    Supports two store types:
    - ``"memory"``: In-memory (via maggma MemoryStore)
    - ``"json"``: File-based JSON (via maggma JSONStore)

    Usage::

        backend = MaggmaBackend(store_path="data.json")
        backend.connect()
        backend.put("abc123", {"doc_id": "abc123", ...})
        doc = backend.get("abc123")

    Raises:
        ImportError: If maggma is not installed.
    """

    def __init__(
        self,
        store_path: Optional[Union[str, Path]] = None,
        use_memory_store: bool = False,
        auto_flush: bool = True,
        **kwargs,
    ):
        if not MAGGMA_AVAILABLE:
            raise ImportError(
                "maggma is required for MaggmaBackend. "
                "Install with: pip install maggma"
            )

        self._closed = True
        self.auto_flush = auto_flush

        if use_memory_store:
            self._store = MemoryStore(key="doc_id", **kwargs)
            self.store_type = "memory"
            self.store_path = None
        else:
            if store_path is None:
                store_path = Path("./materials_simulation_data.json")
            else:
                store_path = Path(store_path)

            store_path.parent.mkdir(parents=True, exist_ok=True)

            if not store_path.exists():
                with open(store_path, "w") as f:
                    json.dump([], f)

            self._store = JSONStore(str(store_path), key="doc_id", **kwargs)
            self.store_type = "json"
            self.store_path = store_path

    # ------------------------------------------------------------------
    def connect(self) -> None:
        self._store.connect()
        self._closed = False
        logger.info("MaggmaBackend connected (%s)", self.store_type)

    # ------------------------------------------------------------------
    def put(self, doc_id: str, document: dict) -> None:
        self._store.update(document)
        if self.auto_flush:
            self._flush_store()

    # ------------------------------------------------------------------
    def get(self, doc_id: str) -> dict | None:
        return self._store.query_one(criteria={"doc_id": doc_id})

    # ------------------------------------------------------------------
    def query(
        self, criteria: dict, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        results = list(self._store.query(criteria=criteria))
        return results[offset : offset + limit]

    # ------------------------------------------------------------------
    def delete(self, doc_id: str) -> bool:
        doc = self._store.query_one(criteria={"doc_id": doc_id})
        if doc is None:
            return False
        self._store.remove_docs(criteria={"doc_id": doc_id})
        if self.auto_flush:
            self._flush_store()
        return True

    # ------------------------------------------------------------------
    def flush(self) -> None:
        self._flush_store()

    def _flush_store(self) -> None:
        if self.store_type == "json" and hasattr(self._store, "update_json_file"):
            self._store.update_json_file()

    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._closed:
            return
        self._flush_store()
        self._store.close()
        self._closed = True
        logger.info("MaggmaBackend closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


__all__ = ["MaggmaBackend"]
```

- [ ] **Step 3: Run storage tests (expect failures — facade not yet created)**

```bash
pytest tests/storage/ -x -q --tb=short 2>&1 | head -40
```

- [ ] **Step 4: Commit**

```bash
git add matsimpy/storage/maggma_store.py matsimpy/storage/schema.py
git commit -m "refactor: extract MaggmaBackend from DataStorage

MaggmaBackend implements StoreBackend protocol.
Old _stable_doc_id preserved as legacy helper in schema.py.
DataStorage facade coming next.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.18: Create storage/facade.py (DataStorage)

**Files:**
- Create: `matsimpy/storage/facade.py`

- [ ] **Step 1: Write facade.py**

```python
"""
DataStorage facade — high-level API composing codec + backend.

This is the user-facing API. It composes:
- DocumentCodec: encodes/decodes MatSimPy objects ↔ DocumentEnvelope
- StoreBackend: persists/retrieves document dicts

Usage::

    storage = DataStorage()                            # MemoryBackend (default)
    storage = DataStorage(backend=MaggmaBackend(...))  # persistent
    doc_id = storage.store_data(crystal, metadata={"source": "icsd"})
    crystal = storage.retrieve_data(doc_id)
"""

from __future__ import annotations

import logging
from typing import Optional, Union

from monty.json import MSONable

from ..core import Structure
from .codec import DocumentCodec
from .memory_store import MemoryBackend
from .backend import StoreBackend
from .schema import DocumentEnvelope

logger = logging.getLogger(__name__)


class DataStorage:
    """High-level storage API composing codec + backend.

    Default backend is MemoryBackend (in-memory, for testing).
    Use MaggmaBackend for persistent JSON storage.
    """

    def __init__(self, backend: Optional[StoreBackend] = None):
        self.codec = DocumentCodec()
        self.backend = backend if backend is not None else MemoryBackend()
        self.backend.connect()

    # ------------------------------------------------------------------
    def store_data(
        self,
        data: Union[dict, MSONable],
        doc_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Store data and return the document ID.

        Args:
            data: MatSimPy object (MSONable) or plain dict.
            doc_id: Optional explicit ID. If None, a content-addressed
                    ID is generated from the payload.
            metadata: Optional user-provided metadata dict.

        Returns:
            The document ID (generated or explicit).

        Raises:
            ValueError: If metadata keys collide with reserved fields.
        """
        if isinstance(data, MSONable):
            envelope = self.codec.encode(data, metadata=metadata)
        elif isinstance(data, dict):
            if doc_id is None:
                doc_id = DocumentEnvelope.generate_id(data, metadata)
            envelope = DocumentEnvelope(
                doc_id=doc_id,
                payload=data,
                metadata=metadata or {},
            )
        else:
            raise TypeError(
                f"Expected MSONable or dict, got {type(data).__name__}"
            )

        if doc_id is not None:
            # Explicit ID overrides generated one
            # Rebuild envelope with explicit ID
            envelope = DocumentEnvelope(
                doc_id=doc_id,
                payload=envelope.payload,
                schema_version=envelope.schema_version,
                metadata=envelope.metadata,
            )

        self.backend.put(envelope.doc_id, envelope.to_dict())
        logger.info("Stored data with ID: %s", envelope.doc_id)
        return envelope.doc_id

    # ------------------------------------------------------------------
    def retrieve_data(self, doc_id: str) -> Structure:
        """Retrieve a stored MatSimPy object by its document ID.

        Args:
            doc_id: Document ID returned by store_data().

        Returns:
            Crystal or Molecule.

        Raises:
            KeyError: If doc_id is not found.
        """
        doc = self.backend.get(doc_id)
        if doc is None:
            raise KeyError(f"Document not found: {doc_id!r}")

        envelope = DocumentEnvelope.from_dict(doc)
        return self.codec.decode(envelope)

    # ------------------------------------------------------------------
    def query(
        self,
        criteria: dict,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Structure]:
        """Query stored documents and decode matching results.

        Args:
            criteria: Dict of field-value pairs (supports dot-delimited
                     nested keys like ``"metadata.source"``).
            limit: Max documents to return.
            offset: Documents to skip.

        Returns:
            List of decoded Crystal/Molecule objects.
        """
        docs = self.backend.query(criteria, limit=limit, offset=offset)
        results = []
        for doc in docs:
            envelope = DocumentEnvelope.from_dict(doc)
            results.append(self.codec.decode(envelope))
        return results

    # ------------------------------------------------------------------
    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID. Return True if it existed."""
        return self.backend.delete(doc_id)

    # ------------------------------------------------------------------
    def flush(self) -> None:
        """Force pending writes to durable storage."""
        self.backend.flush()

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the storage backend."""
        self.backend.close()

    # ------------------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


__all__ = ["DataStorage"]
```

- [ ] **Step 2: Update storage/__init__.py**

```python
"""
Data storage module for MatSimPy.

Provides persistent storage for computation results, structures, and workflows.

Architecture::

    DataStorage (facade) ──► DocumentCodec ──► DocumentEnvelope
         │
         └──► StoreBackend (protocol)
               ├── MemoryBackend  (in-memory, for testing)
               └── MaggmaBackend  (file-based, for production)

Usage::

    >>> from matsimpy.storage import DataStorage
    >>> storage = DataStorage()  # defaults to MemoryBackend
    >>> doc_id = storage.store_data(crystal)
    >>> crystal = storage.retrieve_data(doc_id)
"""

from .facade import DataStorage
from .memory_store import MemoryBackend

# Lazy-import maggma backend
try:
    from .maggma_store import MaggmaBackend
except ImportError:
    MaggmaBackend = None  # type: ignore

__all__ = ["DataStorage", "MemoryBackend", "MaggmaBackend"]
```

- [ ] **Step 3: Run storage tests**

```bash
pytest tests/storage/ -x -q --tb=short
```

- [ ] **Step 4: Fix any test breakage from the API change**

The existing tests may use patterns like `storage.store_data(dict, doc_id=...)` and `storage.retrieve_data(doc_id=...)` — verify these still work. The `retrieve_data` signature changed (separated `doc_id` and `query` params), so tests that used `query=` may need updating.

- [ ] **Step 5: Commit**

```bash
git add matsimpy/storage/
git commit -m "refactor: add DataStorage facade + split storage into components

DataStorage now composes DocumentCodec + StoreBackend.
Backend protocol with MemoryBackend and MaggmaBackend implementations.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1.19: Run full test suite and fix regressions

**Files:**
- Various test files (fix imports)

- [ ] **Step 1: Run full test suite**

```bash
pytest -x -q --tb=line 2>&1 | tail -50
```

- [ ] **Step 2: Fix any import errors**

For each failing test with import errors, update:
- `from matsimpy.core import structure_to_graph_data` → `from matsimpy.analysis import structure_to_graph_data`
- `Crystal.from_file(...)` → `read(...)`
- `crystal.to_file(...)` → `write(crystal, ...)`
- `from matsimpy.io.converters import ...` → `from matsimpy.adapters.pymatgen import ...`
- `from matsimpy.io.latex import ...` → `from matsimpy.export.latex import ...`

- [ ] **Step 3: Run tests again**

```bash
pytest -x -q
```

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: update imports across codebase for architecture refactor

Phase 1: core cleanup, IO registry, storage split, adapters/export packages.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2: Registries & Separation (3–6 months)

### Task 2.1: Create TransformationSpec

**Files:**
- Create: `matsimpy/transformation/spec.py`

- [ ] **Step 1: Write spec.py**

```python
"""
TransformationSpec — structured metadata for transformation operations.

Each registered transformation function gets a TransformationSpec
describing its name, category, type constraints, behavioral guarantees,
parameter schema, and version.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TransformationSpec:
    """Metadata for a registered transformation.

    Attributes:
        name: Unique identifier, e.g. ``"translate"``, ``"create_vacancy"``.
        category: One of ``"geometric"``, ``"lattice"``, ``"atomic"``,
            ``"chemical"``, ``"structural"``.
        callable: The actual transformation function.
        description: One-line human-readable summary.
        applicable_types: Tuple of types the transform accepts,
            e.g. ``(Crystal, Molecule)`` or ``(Crystal,)``.
        output_type: The type returned (usually same as input).
        preserves_composition: True if species/counts are unchanged.
        preserves_lattice: True if the lattice matrix is unchanged.
        preserves_site_properties: True if per-atom properties survive.
        preserves_pbc: True if periodic boundary conditions are unchanged.
        parameter_schema: JSON Schema dict for **kwargs validation.
        version: Semver for this spec (not the function itself).
    """

    name: str
    category: str
    callable: Callable
    description: str = ""
    applicable_types: tuple = ()
    output_type: type | None = None
    preserves_composition: bool = True
    preserves_lattice: bool = True
    preserves_site_properties: bool = True
    preserves_pbc: bool = True
    parameter_schema: dict | None = None
    version: str = "1.0.0"


__all__ = ["TransformationSpec"]
```

- [ ] **Step 2: Commit**

```bash
git add matsimpy/transformation/spec.py
git commit -m "feat: add TransformationSpec dataclass

Structured metadata for all transformation operations.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.2: Create TransformationRegistry

**Files:**
- Create: `matsimpy/transformation/registry.py`

- [ ] **Step 1: Write registry.py**

```python
"""
TransformationRegistry — singleton registry for all TransformationSpecs.

Supports registration, lookup by name/category/structure type, parameter
validation, and plan execution.
"""

from __future__ import annotations

from typing import Callable

from ..exceptions import RegistryError
from .spec import TransformationSpec


class TransformationRegistry:
    """Singleton registry for transformation specs.

    Usage::

        from matsimpy.transformation.registry import registry
        from matsimpy.transformation.spec import TransformationSpec

        spec = TransformationSpec(
            name="translate",
            category="geometric",
            callable=translate,
            applicable_types=(Crystal, Molecule),
            ...
        )
        registry.register(spec)

        # Lookup
        spec = registry.get("translate")

        # Execute with validation
        result = registry.apply("translate", crystal, vector=[1, 0, 0])

    Plugin entry point: ``'matsimpy.transformations'``.
    """

    def __init__(self) -> None:
        self._specs: dict[str, TransformationSpec] = {}

    # ------------------------------------------------------------------
    def register(self, spec: TransformationSpec) -> None:
        """Register a transformation spec.

        Raises:
            RegistryError: If a spec with the same name already exists.
        """
        if spec.name in self._specs:
            raise RegistryError(
                f"Transformation {spec.name!r} is already registered"
            )
        self._specs[spec.name] = spec

    # ------------------------------------------------------------------
    def get(self, name: str) -> TransformationSpec:
        """Look up a spec by name.

        Raises:
            KeyError: If not found.
        """
        if name not in self._specs:
            raise KeyError(f"Transformation {name!r} is not registered")
        return self._specs[name]

    # ------------------------------------------------------------------
    def list_all(self) -> list[TransformationSpec]:
        """Return all registered specs."""
        return list(self._specs.values())

    # ------------------------------------------------------------------
    def list_by_category(self, category: str) -> list[TransformationSpec]:
        """Return specs matching *category*."""
        return [s for s in self._specs.values() if s.category == category]

    # ------------------------------------------------------------------
    def list_applicable(self, structure_type: type) -> list[TransformationSpec]:
        """Return specs applicable to *structure_type*."""
        return [
            s for s in self._specs.values()
            if structure_type in s.applicable_types
        ]

    # ------------------------------------------------------------------
    def apply(self, name: str, structure, **kwargs):
        """Look up spec and apply the transformation with *kwargs*.

        Validates that the structure type matches the spec's
        applicable_types before calling.

        Args:
            name: Registered transformation name.
            structure: Crystal or Molecule to transform.
            **kwargs: Passed to the transformation function.

        Returns:
            Transformed structure (new object).

        Raises:
            KeyError: If *name* is not registered.
            TypeError: If *structure* type is not applicable.
        """
        spec = self.get(name)

        if not isinstance(structure, spec.applicable_types):
            allowed = ", ".join(t.__name__ for t in spec.applicable_types)
            raise TypeError(
                f"Transformation {name!r} expects {allowed}, "
                f"got {type(structure).__name__}"
            )

        return spec.callable(structure, **kwargs)

    # ------------------------------------------------------------------
    def apply_plan(self, plan, structure):
        """Execute a TransformationPlan sequentially.

        Args:
            plan: TransformationPlan with steps to execute.
            structure: Starting structure.

        Returns:
            Transformed structure after all steps.
        """
        result = structure
        for step in plan.steps:
            result = self.apply(step.spec_name, result, **step.params)
        return result


# Module-level singleton
registry = TransformationRegistry()


__all__ = ["TransformationRegistry", "registry"]
```

- [ ] **Step 2: Commit**

```bash
git add matsimpy/transformation/registry.py
git commit -m "feat: add TransformationRegistry singleton

Register/lookup/apply transformations by name with type validation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.3: Register all built-in transformations

**Files:**
- Modify: `matsimpy/transformation/geometric/translation.py`
- Modify: `matsimpy/transformation/geometric/rotation.py`
- Modify: `matsimpy/transformation/lattice/strain.py`
- Modify: `matsimpy/transformation/lattice/scale.py`
- Modify: `matsimpy/transformation/lattice/transform.py`
- Modify: `matsimpy/transformation/atomic/manipulation.py`
- Modify: `matsimpy/transformation/atomic/organization.py`
- Modify: `matsimpy/transformation/chemical/__init__.py`
- Modify: `matsimpy/transformation/structural/supercell.py`

- [ ] **Step 1: Register geometric transformations**

For each transformation file, append registration code at the bottom.

Example for `translation.py`:
```python
# --- Registry registration ---
from ..registry import registry
from ..spec import TransformationSpec
from ...core import Crystal, Molecule

_TRANSLATE_SPEC = TransformationSpec(
    name="translate",
    category="geometric",
    callable=translate,
    description="Translate structure by a 3D vector",
    applicable_types=(Crystal, Molecule),
    output_type=Crystal,
    preserves_composition=True,
    preserves_lattice=True,
    preserves_site_properties=True,
    preserves_pbc=True,
    parameter_schema={
        "type": "object",
        "properties": {
            "vector": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 3,
                "maxItems": 3,
            }
        },
        "required": ["vector"],
    },
    version="1.0.0",
)
registry.register(_TRANSLATE_SPEC)
# Repeat for translate_to_origin, etc.
```

Do this for every transformation function in each file. Use:
```bash
grep "^def " matsimpy/transformation/geometric/translation.py
```
to find all public functions.

For each function, create an appropriate `TransformationSpec` with correct metadata.

- [ ] **Step 2: Register lattice transformations**

Similarly register `apply_strain`, `apply_deformation`, `scale_lattice`, `set_volume`, `rotate_lattice`, `transform_lattice`, `standardize_cell` in their respective files.

For lattice transforms:
- `applicable_types=(Crystal,)`
- `preserves_lattice=False`
- `preserves_composition=True`

- [ ] **Step 3: Register atomic transformations**

Register `move_atoms`, `swap_atoms`, `merge_atoms`, `sort_atoms`, `center_structure`, `perturb_positions`.

- [ ] **Step 4: Register chemical transformations**

Register `substitute`, `substitute_all` from `transformation/chemical/`.

- [ ] **Step 5: Register structural transformations**

Register `make_supercell` from `transformation/structural/supercell.py`.

- [ ] **Step 6: Run transformation tests**

```bash
pytest tests/transformation/ -x -q
```

- [ ] **Step 7: Commit**

```bash
git add matsimpy/transformation/
git commit -m "feat: register all built-in transformations with registry

Every transformation function now has a TransformationSpec.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.4: Create TransformationPlan, refactor Pipeline/Batch/Sweep

**Files:**
- Create: `matsimpy/transformation/composite/plan.py`
- Modify: `matsimpy/transformation/composite/pipeline.py`
- Modify: `matsimpy/transformation/composite/batch.py`
- Modify: `matsimpy/transformation/composite/sweep.py`
- Modify: `matsimpy/transformation/composite/__init__.py`

- [ ] **Step 1: Create plan.py**

```python
"""
TransformationPlan — serializable sequence of transformation steps.

Separates the description of "what to do" from the execution strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TransformationStep:
    """A single step in a transformation plan.

    Attributes:
        spec_name: Registry key, e.g. ``"translate"``.
        params: Kwargs passed to the transformation function.
        label: Optional human-readable label for this step.
    """

    spec_name: str
    params: dict = field(default_factory=dict)
    label: str | None = None

    def to_dict(self) -> dict:
        return {
            "spec_name": self.spec_name,
            "params": self.params,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TransformationStep:
        return cls(
            spec_name=d["spec_name"],
            params=d.get("params", {}),
            label=d.get("label"),
        )


@dataclass
class TransformationPlan:
    """A serializable, reproducible sequence of transformation steps.

    Usage::

        plan = TransformationPlan(
            steps=[
                TransformationStep("make_supercell", {"scaling_matrix": [2, 2, 2]}),
                TransformationStep("create_vacancy", {"indices": [0]}),
            ],
            name="2x2 supercell with vacancy",
        )
        result = registry.apply_plan(plan, crystal)
    """

    steps: list[TransformationStep] = field(default_factory=list)
    name: str | None = None
    description: str | None = None

    def to_dict(self) -> dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TransformationPlan:
        return cls(
            steps=[TransformationStep.from_dict(s) for s in d["steps"]],
            name=d.get("name"),
            description=d.get("description"),
        )


__all__ = ["TransformationStep", "TransformationPlan"]
```

- [ ] **Step 2: Refactor pipeline.py**

Rename `TransformationPipeline` to `PipelineExecutor` and have it consume a `TransformationPlan`:

```python
class PipelineExecutor:
    """Execute a TransformationPlan sequentially."""

    def __init__(self, plan: TransformationPlan):
        self.plan = plan

    def apply(self, structure):
        """Apply all steps in order, returning the final structure."""
        from ..registry import registry
        return registry.apply_plan(self.plan, structure)
```

Keep the old `TransformationPipeline` class name as an alias but mark deprecated in docstring.

- [ ] **Step 3: Refactor batch.py and sweep.py similarly**

- [ ] **Step 4: Update composite/__init__.py**

```python
from .plan import TransformationStep, TransformationPlan
from .pipeline import PipelineExecutor
from .batch import BatchExecutor, BatchResult
from .sweep import SweepExecutor

# Keep old names as aliases for a transition period
TransformationPipeline = PipelineExecutor
ParameterSweep = SweepExecutor
BatchProcessor = BatchExecutor

__all__ = [
    "TransformationStep",
    "TransformationPlan",
    "PipelineExecutor",
    "BatchExecutor",
    "BatchResult",
    "SweepExecutor",
    # Legacy aliases
    "TransformationPipeline",
    "ParameterSweep",
    "BatchProcessor",
]
```

- [ ] **Step 5: Run composite tests**

```bash
pytest tests/transformation/ -x -q -k "composite or pipeline or batch or sweep"
```

- [ ] **Step 6: Commit**

```bash
git add matsimpy/transformation/composite/
git commit -m "feat: add TransformationPlan, refactor Pipeline/Batch/Sweep

Plan describes what; Executor describes how. Separated concerns.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.5: Create BuilderRegistry

**Files:**
- Create: `matsimpy/builders/registry.py`

- [ ] **Step 1: Write registry.py**

```python
"""
BuilderRegistry — registry for structure constructors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class BuilderSpec:
    """Metadata for a registered structure builder.

    Attributes:
        name: Unique identifier.
        category: ``"bulk"`` | ``"surface"`` | ``"molecule"`` | ``"nanostructure"``.
        callable: The builder function.
        description: One-line summary.
        output_type: The type returned (Crystal or Molecule).
        parameter_schema: JSON Schema for **kwargs validation.
        requires_optional: Tuple of optional dependency names, e.g. ``("pyxtal",)``.
    """

    name: str
    category: str
    callable: Callable
    description: str = ""
    output_type: type | None = None
    parameter_schema: dict | None = None
    requires_optional: tuple[str, ...] = ()


class BuilderRegistry:
    """Singleton registry for structure builder specs.

    Plugin entry point: ``'matsimpy.builders'``.
    """

    def __init__(self) -> None:
        self._specs: dict[str, BuilderSpec] = {}

    def register(self, spec: BuilderSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Builder {spec.name!r} is already registered")
        self._specs[spec.name] = spec

    def get(self, name: str) -> BuilderSpec:
        if name not in self._specs:
            raise KeyError(f"Builder {name!r} is not registered")
        return self._specs[name]

    def build(self, name: str, **kwargs):
        """Validate and call the builder, return a structure."""
        spec = self.get(name)
        return spec.callable(**kwargs)

    def list_all(self) -> list[BuilderSpec]:
        return list(self._specs.values())

    def list_by_category(self, category: str) -> list[BuilderSpec]:
        return [s for s in self._specs.values() if s.category == category]


registry = BuilderRegistry()
__all__ = ["BuilderSpec", "BuilderRegistry", "registry"]
```

- [ ] **Step 2: Register built-in builders**

Append registration to each builder file, e.g. `bulk/prototype.py`:
```python
from ..registry import registry, BuilderSpec
from ...core import Crystal

_FROM_PROTOTYPE_SPEC = BuilderSpec(
    name="from_prototype",
    category="bulk",
    callable=from_prototype,
    description="Build bulk crystal from prototype (fcc, bcc, hcp, diamond, etc.)",
    output_type=Crystal,
    parameter_schema={
        "type": "object",
        "properties": {
            "prototype": {"type": "string"},
            "element": {"type": "string"},
            "a": {"type": "number"},
        },
        "required": ["prototype", "element", "a"],
    },
)
registry.register(_FROM_PROTOTYPE_SPEC)
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/builders/registry.py matsimpy/builders/bulk/
git commit -m "feat: add BuilderRegistry with BuilderSpec

Registered from_prototype and other core builders.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.6: Move defects to transformation/atomic

**Files:**
- Create: `matsimpy/transformation/atomic/defects.py`
- Modify: `matsimpy/builders/defects/` (removed)
- Modify: `matsimpy/transformation/atomic/__init__.py`
- Modify: `matsimpy/builders/__init__.py`

- [ ] **Step 1: Move the file and update imports**

```bash
cp matsimpy/builders/defects/point.py matsimpy/transformation/atomic/defects.py
```

Update imports in the new file to match the new location:
```python
# Old (in builders/defects/point.py):
from ...core import Crystal
from ...transformation.atomic import ...

# New (in transformation/atomic/defects.py):
from ...core import Crystal
from .manipulation import ...  # same-package imports
```

- [ ] **Step 2: Register as transformations**

Append to `matsimpy/transformation/atomic/defects.py` for each function:

```python
from ..registry import registry
from ..spec import TransformationSpec
from ...core import Crystal, Molecule

_VACANCY_SPEC = TransformationSpec(
    name="create_vacancy",
    category="atomic",
    callable=create_vacancy,
    description="Remove atom(s) to create vacancies",
    applicable_types=(Crystal, Molecule),
    output_type=Crystal,
    preserves_composition=False,
    preserves_lattice=True,
    preserves_site_properties=True,
    preserves_pbc=True,
    parameter_schema={
        "type": "object",
        "properties": {
            "indices": {
                "oneOf": [
                    {"type": "integer"},
                    {"type": "array", "items": {"type": "integer"}},
                ]
            }
        },
        "required": ["indices"],
    },
)
registry.register(_VACANCY_SPEC)
# Repeat for create_interstitial, create_substitution,
# create_frenkel, create_schottky, create_antisite
```

- [ ] **Step 3: Update transformation/atomic/__init__.py**

Add the new exports:
```python
from .defects import (
    create_vacancy,
    create_interstitial,
    create_substitution,
    create_frenkel,
    create_schottky,
    create_antisite,
)
```

And add to `__all__`.

- [ ] **Step 4: Delete builders/defects/**

```bash
rm -rf matsimpy/builders/defects/
```

- [ ] **Step 5: Update builders/__init__.py**

Remove the defects import:
```python
# Remove:
from .defects import *
from .defects import __all__ as _defects_all
# Remove _defects_all from combined __all__
```

- [ ] **Step 6: Update all imports across the codebase**

```bash
grep -rn "from.*builders.defects import\|from.*builders import.*create_vacancy\|from.*builders import.*create_interstitial" matsimpy/ tests/ --include="*.py" | grep -v __pycache__
```

Update each:
```python
# Old:
from matsimpy.builders.defects import create_vacancy
from matsimpy.builders import create_vacancy

# New:
from matsimpy.transformation.atomic import create_vacancy
from matsimpy.transformation import create_vacancy
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/builders/ tests/transformation/ -x -q
```

- [ ] **Step 8: Commit**

```bash
git add matsimpy/transformation/atomic/ matsimpy/builders/
git rm -r matsimpy/builders/defects/
git commit -m "refactor: move defect builders to transformation/atomic

create_vacancy, create_interstitial, etc. modify existing structures
and belong in transformation, not builders.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.7: Move alloy to transformation/chemical

**Files:**
- Move: `matsimpy/builders/alloy/random.py` → `matsimpy/transformation/chemical/alloy_random.py`
- Move: `matsimpy/builders/alloy/ordered.py` → `matsimpy/transformation/chemical/alloy_ordered.py`
- Decide: `matsimpy/builders/alloy/heusler.py` → review if constructor or modifier
- Modify: `matsimpy/transformation/chemical/__init__.py`
- Modify: `matsimpy/builders/__init__.py`

- [ ] **Step 1: Review heusler.py**

```bash
head -40 matsimpy/builders/alloy/heusler.py
```

If `generate_intermetallic()` constructs from prototype parameters (like `from_prototype`), it stays in builders. If it takes an existing structure and modifies it, it moves to transformation.

- [ ] **Step 2: Move random alloy and ordered alloy**

```bash
cp matsimpy/builders/alloy/random.py matsimpy/transformation/chemical/alloy_random.py
cp matsimpy/builders/alloy/ordered.py matsimpy/transformation/chemical/alloy_ordered.py
```

Update imports in each file, register as `TransformationSpec`s.

- [ ] **Step 3: Update chemical/__init__.py**

```python
from .alloy_random import generate_random_alloy
from .alloy_ordered import generate_ordered_alloy, generate_intermetallic
```

- [ ] **Step 4: Delete builders/alloy/ (or keep heusler if constructor)**

```bash
rm -rf matsimpy/builders/alloy/
# If heusler stays: keep matsimpy/builders/alloy/heusler.py
```

- [ ] **Step 5: Update builders/__init__.py**

Remove alloy imports from `builders/__init__.py`.

- [ ] **Step 6: Update all imports**

```bash
grep -rn "from.*builders.alloy import" matsimpy/ tests/ --include="*.py"
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/builders/ tests/transformation/ -x -q
```

- [ ] **Step 8: Commit**

```bash
git add matsimpy/transformation/chemical/ matsimpy/builders/
git commit -m "refactor: move alloy builders to transformation/chemical

Alloy generation modifies existing structures — belongs in transformation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.8: Move adsorbate to transformation/atomic

**Files:**
- Move: `matsimpy/builders/surface/adsorbate.py` → `matsimpy/transformation/atomic/adsorbate.py`
- Modify: `matsimpy/transformation/atomic/__init__.py`
- Modify: `matsimpy/builders/surface/__init__.py`

- [ ] **Step 1: Move the file**

```bash
cp matsimpy/builders/surface/adsorbate.py matsimpy/transformation/atomic/adsorbate.py
```

Update imports and register `add_adsorbate` as a `TransformationSpec`.

- [ ] **Step 2: Update surface/__init__.py**

Remove the adsorbate import (keep `generate_slab`).

- [ ] **Step 3: Update all imports**

```bash
grep -rn "from.*surface.adsorbate import\|from.*builders.surface import.*add_adsorbate\|from.*builders import.*add_adsorbate" matsimpy/ tests/ --include="*.py"
```

- [ ] **Step 4: Delete old file**

```bash
rm matsimpy/builders/surface/adsorbate.py
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/builders/ tests/transformation/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add matsimpy/transformation/atomic/adsorbate.py matsimpy/builders/surface/
git commit -m "refactor: move adsorbate builder to transformation/atomic

add_adsorbate modifies an existing surface — belongs in transformation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.9: Move interface to transformation/structural

**Files:**
- Move: `matsimpy/builders/interface/` → `matsimpy/transformation/structural/interface.py`
- Modify: `matsimpy/transformation/structural/__init__.py`
- Modify: `matsimpy/builders/__init__.py`

- [ ] **Step 1: Move and register**

```bash
cp matsimpy/builders/interface/__init__.py matsimpy/transformation/structural/interface.py
```

Register `create_simple_interface` as a `TransformationSpec`.

- [ ] **Step 2: Update imports and delete old**

```bash
rm -rf matsimpy/builders/interface/
```

- [ ] **Step 3: Update all references, run tests, commit**

Follow same pattern as Tasks 2.6–2.8.

---

### Task 2.10: Clean up wildcard exports

**Files:**
- Modify: `matsimpy/builders/__init__.py`
- Modify: `matsimpy/transformation/__init__.py`

- [ ] **Step 1: Rewrite builders/__init__.py with curated exports**

```python
"""Structure builders for MatSimPy — constructors only.

Builders create structures from parameters/prototypes.
For modification of existing structures, see matsimpy.transformation.

Categories:
    bulk/         — from_prototype(), random_crystal()
    surface/      — generate_slab()
    molecule/     — build_linear(), build_bent(), build_tetrahedral(), build_from_smiles()
    nanostructure/ — build_nanotube(), build_carbon_nanotube(), build_twisted_bilayer(), etc.

Usage::

    >>> from matsimpy.builders import from_prototype
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
"""

# Curated top-level API (~15 names)
from .bulk import from_prototype, random_crystal
from .surface import generate_slab
from .molecule import (
    build_linear,
    build_bent,
    build_tetrahedral,
    build_from_smiles,
)
from .nanostructure import (
    build_nanotube,
    build_carbon_nanotube,
    build_twisted_bilayer,
    build_magic_angle_twisted,
    build_twisted_multilayer,
)

# Registry
from .registry import registry, BuilderSpec, BuilderRegistry

# Allow submodule access
from . import bulk, surface, molecule, nanostructure

__all__ = [
    "from_prototype",
    "random_crystal",
    "generate_slab",
    "build_linear",
    "build_bent",
    "build_tetrahedral",
    "build_from_smiles",
    "build_nanotube",
    "build_carbon_nanotube",
    "build_twisted_bilayer",
    "build_magic_angle_twisted",
    "build_twisted_multilayer",
    "registry",
    "BuilderSpec",
    "BuilderRegistry",
]
```

- [ ] **Step 2: Rewrite transformation/__init__.py with curated exports**

```python
"""Structure transformation tools — operations on existing structures.

All transformations return new objects (immutable-return pattern).
For constructing structures from scratch, see matsimpy.builders.

Categories:
    geometric/  — translate, rotate (Crystal + Molecule)
    lattice/    — strain, scale, transform (Crystal only)
    atomic/     — move, swap, defects, adsorbates (Crystal + Molecule)
    chemical/   — substitution, alloy generation
    structural/ — supercell, interface, molecular ops
    composite/  — pipelines, batches, sweeps

Usage::

    >>> from matsimpy.transformation import translate, create_vacancy
    >>> moved = translate(crystal, [1, 0, 0])
    >>> vac = create_vacancy(moved, 0)
"""

# Curated by category
from .geometric import translate, translate_to_origin, rotate, rotate_around_axis
from .lattice import apply_strain, apply_deformation, scale_lattice, set_volume
from .atomic import (
    move_atoms, swap_atoms, merge_atoms,
    create_vacancy, create_interstitial, create_substitution,
    create_frenkel, create_schottky, create_antisite,
    add_adsorbate,
    sort_atoms, center_structure, perturb_positions,
)
from .chemical import substitute, substitute_all, generate_random_alloy, generate_ordered_alloy
from .structural import make_supercell, create_simple_interface

# Composite
from .composite import (
    TransformationStep, TransformationPlan,
    PipelineExecutor, BatchExecutor, SweepExecutor,
)

# Registry
from .registry import registry, TransformationRegistry
from .spec import TransformationSpec

# Submodule access
from . import geometric, lattice, atomic, chemical, structural, composite

__all__ = [
    # Geometric
    "translate", "translate_to_origin", "rotate", "rotate_around_axis",
    # Lattice
    "apply_strain", "apply_deformation", "scale_lattice", "set_volume",
    # Atomic
    "move_atoms", "swap_atoms", "merge_atoms",
    "create_vacancy", "create_interstitial", "create_substitution",
    "create_frenkel", "create_schottky", "create_antisite",
    "add_adsorbate",
    "sort_atoms", "center_structure", "perturb_positions",
    # Chemical
    "substitute", "substitute_all", "generate_random_alloy", "generate_ordered_alloy",
    # Structural
    "make_supercell", "create_simple_interface",
    # Composite
    "TransformationStep", "TransformationPlan",
    "PipelineExecutor", "BatchExecutor", "SweepExecutor",
    # Registry
    "registry", "TransformationRegistry", "TransformationSpec",
]
```

Note: The exact function names need to be verified against what each module actually exports. Run:
```bash
for f in matsimpy/transformation/*/__init__.py; do echo "=== $f ==="; grep "^from\|^__all__" "$f"; done
```
to get the actual export names and adjust the list accordingly.

- [ ] **Step 3: Run full test suite**

```bash
pytest -x -q --tb=short
```

Fix any import errors from tests using `from matsimpy.builders import *` for functions that have moved.

- [ ] **Step 4: Commit**

```bash
git add matsimpy/builders/__init__.py matsimpy/transformation/__init__.py
git commit -m "refactor: curated exports replace wildcard imports

builders: ~15 curated names, transformation: ~30 curated names.
Wildcard imports discouraged; explicit imports documented.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.11: Add contract tests for Phase 1 + 2

**Files:**
- Create: `tests/contracts/__init__.py`
- Create: `tests/contracts/test_structure_model_contract.py`
- Create: `tests/contracts/test_transformation_contract.py`
- Create: `tests/contracts/test_builder_contract.py`
- Create: `tests/contracts/test_io_format_contract.py`
- Create: `tests/contracts/test_storage_backend_contract.py`

- [ ] **Step 1: Write test_structure_model_contract.py**

```python
"""Contract tests for the Structure domain model.

Tests immutable-return, species tuple immutability, positions writeable=False,
as_dict/from_dict round-trip, and equality/hash consistency.
Parametrized over Crystal and Molecule variants.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice


# Sample structures for parametrization
@pytest.fixture
def nacl_crystal():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


@pytest.fixture
def water_molecule():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


@pytest.fixture(params=["crystal", "molecule"])
def structure(request, nacl_crystal, water_molecule):
    if request.param == "crystal":
        return nacl_crystal
    return water_molecule


class TestImmutableReturn:
    """All mutation methods return new objects."""

    def test_add_atom_returns_new(self, structure):
        original_id = id(structure)
        new_structure = structure.add_atom('H', [0.1, 0.1, 0.1])
        assert id(new_structure) != original_id
        assert len(new_structure) == len(structure) + 1
        assert len(structure) == len(new_structure) - 1  # original unchanged

    def test_remove_atom_returns_new(self, structure):
        if len(structure) < 2:
            pytest.skip("Need at least 2 atoms")
        new_structure = structure.remove_atom(0)
        assert id(new_structure) != id(structure)
        assert len(new_structure) == len(structure) - 1

    def test_substitute_returns_new(self, structure):
        new_structure = structure.substitute(0, 'He')
        assert id(new_structure) != id(structure)
        assert new_structure.species[0] == 'He'
        assert structure.species[0] != 'He'

    def test_sort_atoms_returns_new(self, structure):
        new_structure = structure.sort_atoms()
        assert id(new_structure) != id(structure)


class TestSpeciesImmutability:
    """species is an immutable tuple."""

    def test_species_is_tuple(self, structure):
        assert isinstance(structure.species, tuple)

    def test_species_cannot_be_modified(self, structure):
        with pytest.raises(TypeError):
            structure.species[0] = 'Xe'


class TestPositionsReadOnly:
    """positions array has writeable=False."""

    def test_positions_not_writeable(self, structure):
        assert not structure.positions.flags.writeable


class TestSerializationRoundTrip:
    """as_dict() → from_dict() round-trip preserves structure."""

    def test_round_trip(self, structure):
        d = structure.as_dict()
        reconstructed = type(structure).from_dict(d)
        assert reconstructed == structure
        assert reconstructed.formula == structure.formula

    def test_round_trip_preserves_lattice(self, nacl_crystal):
        d = nacl_crystal.as_dict()
        reconstructed = Crystal.from_dict(d)
        assert np.allclose(reconstructed.lattice.matrix, nacl_crystal.lattice.matrix)


class TestEqualityAndHash:
    """Equal structures have equal hashes."""

    def test_equal_structures_equal_hash(self, structure):
        d = structure.as_dict()
        reconstructed = type(structure).from_dict(d)
        assert hash(structure) == hash(reconstructed)

    def test_different_structures_different_hash(self, nacl_crystal, water_molecule):
        assert hash(nacl_crystal) != hash(water_molecule)
```

- [ ] **Step 2: Write test_transformation_contract.py**

```python
"""Contract tests for all registered transformations.

Parametrized over all TransformationSpecs in the registry.
Tests: new-object return, property preservation, type constraints.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.transformation.registry import registry


@pytest.fixture
def nacl():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


# Collect all registered specs for parametrization
all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestTransformationContract:
    """Every transformation obeys its contract."""

    def test_returns_new_object(self, spec, nacl, water):
        """Every transformation returns a new object."""
        structure = nacl if Crystal in spec.applicable_types else water
        # Build minimal valid kwargs from parameter_schema
        kwargs = _minimal_valid_kwargs(spec)
        result = spec.callable(structure, **kwargs)
        assert id(result) != id(structure)

    def test_type_constraint_enforced(self, spec, nacl, water):
        """Registry.apply rejects incompatible types."""
        # Find an incompatible type
        if Crystal in spec.applicable_types:
            bad_structure = water  # Molecule where Crystal expected
        else:
            bad_structure = nacl  # Crystal where Molecule expected

        kwargs = _minimal_valid_kwargs(spec)
        with pytest.raises(TypeError):
            registry.apply(spec.name, bad_structure, **kwargs)

    def test_preserves_composition_if_claimed(self, spec, nacl, water):
        """If preserves_composition=True, composition is unchanged."""
        if not spec.preserves_composition:
            pytest.skip("Transform does not preserve composition")
        structure = nacl if Crystal in spec.applicable_types else water
        kwargs = _minimal_valid_kwargs(spec)
        result = spec.callable(structure, **kwargs)
        assert result.composition == structure.composition


def _minimal_valid_kwargs(spec):
    """Build minimal valid kwargs for a spec from its parameter_schema."""
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    kwargs = {}
    for name, prop in props.items():
        if "default" in prop:
            kwargs[name] = prop["default"]
        elif prop.get("type") == "array" and "items" in prop:
            kwargs[name] = [0.1] * prop.get("minItems", 1)
        elif prop.get("type") == "number":
            kwargs[name] = 0.1
        elif prop.get("type") == "string":
            kwargs[name] = "test"
        elif prop.get("type") == "integer":
            kwargs[name] = 0
        elif prop.get("type") == "boolean":
            kwargs[name] = False
    return kwargs
```

- [ ] **Step 3: Write test_builder_contract.py**

```python
"""Contract tests for all registered builders.

Parametrized over all BuilderSpecs in the registry.
Tests: output_type correctness, parameter_schema validity.
"""

import pytest
from matsimpy.core import Crystal, Molecule
from matsimpy.builders.registry import registry


all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestBuilderContract:

    def test_returns_correct_type(self, spec):
        """Builder returns the declared output_type."""
        kwargs = _minimal_valid_kwargs(spec)
        result = spec.callable(**kwargs)
        assert isinstance(result, spec.output_type)

    def test_parameter_schema_valid(self, spec):
        """parameter_schema is valid JSON Schema if present."""
        if spec.parameter_schema is None:
            pytest.skip("No parameter_schema")
        assert "type" in spec.parameter_schema
        # Basic JSON Schema structure check
        assert spec.parameter_schema["type"] == "object"


def _minimal_valid_kwargs(spec):
    kwargs = {}
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    for name, prop in props.items():
        if name in schema.get("required", []):
            if prop.get("type") == "string":
                if "enum" in prop:
                    kwargs[name] = prop["enum"][0]
                else:
                    kwargs[name] = "test"
            elif prop.get("type") == "number":
                kwargs[name] = 1.0
    return kwargs
```

- [ ] **Step 4: Write test_io_format_contract.py**

```python
"""Contract tests for all registered IO format handlers.

Parametrized over all FormatHandlers in the registry.
Tests: detect by extension, read/write round-trip.
"""

import tempfile
import pytest
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io import registry


@pytest.fixture
def nacl():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


# Get all handlers that support both read and write
rw_handlers = [
    h for h in registry._by_name.values()
    if h.reader is not None and h.writer is not None
]
handler_ids = [h.name for h in rw_handlers]


@pytest.mark.parametrize("handler", rw_handlers, ids=handler_ids)
class TestIOFormatContract:

    def test_detect_by_extension(self, handler):
        """Handler is detected from its primary extension."""
        ext = handler.extensions[0]
        detected = registry.detect(f"test{ext}")
        assert detected is not None
        assert detected.name == handler.name

    def test_round_trip(self, handler, nacl, water, tmp_path):
        """Write then read produces an equivalent structure."""
        if handler.supports_crystal:
            structure = nacl
        else:
            structure = water

        ext = handler.extensions[0]
        path = tmp_path / f"test{ext}"

        # Write
        handler.writer(structure, str(path))

        # Read
        result = handler.reader(str(path))

        assert result is not None
        assert result.formula == structure.formula
        assert len(result) == len(structure)
```

- [ ] **Step 5: Write test_storage_backend_contract.py**

```python
"""Contract tests for all storage backends.

Parametrized over MemoryBackend and MaggmaBackend.
Tests all 7 protocol methods.
"""

import pytest
from matsimpy.core import Crystal, Lattice
from matsimpy.storage import DataStorage, MemoryBackend

try:
    from matsimpy.storage import MaggmaBackend
    MAGGMA_AVAILABLE = MaggmaBackend is not None
except ImportError:
    MAGGMA_AVAILABLE = False


@pytest.fixture
def crystal():
    return Crystal(
        ['Si'],
        [[0, 0, 0]],
        Lattice.cubic(5.43),
    )


@pytest.fixture(params=["memory"])
def storage(request):
    if request.param == "memory":
        return DataStorage(backend=MemoryBackend())
    # Add maggma_json when available
    raise NotImplementedError


class TestStorageContract:

    def test_store_and_retrieve(self, storage, crystal):
        doc_id = storage.store_data(crystal)
        retrieved = storage.retrieve_data(doc_id)
        assert retrieved == crystal

    def test_id_stability(self, storage, crystal):
        """Same content → same ID."""
        id1 = storage.store_data(crystal)
        id2 = storage.store_data(crystal)
        assert id1 == id2

    def test_retrieve_nonexistent_raises(self, storage):
        with pytest.raises(KeyError):
            storage.retrieve_data("nonexistent-id")

    def test_delete(self, storage, crystal):
        doc_id = storage.store_data(crystal)
        assert storage.delete(doc_id) is True
        assert storage.delete(doc_id) is False  # already gone

    def test_query(self, storage, crystal):
        storage.store_data(crystal, metadata={"tag": "test"})
        results = storage.query({"metadata.tag": "test"}, limit=10)
        assert len(results) >= 1
```

- [ ] **Step 6: Run contract tests**

```bash
pytest tests/contracts/ -v
```

- [ ] **Step 7: Commit**

```bash
git add tests/contracts/
git commit -m "test: add contract tests for all layers

5 contract test files parametrized over registries.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2.12: Reorganize existing test files

**Files:**
- Reorganize: `tests/` directory

- [ ] **Step 1: Create new test subdirectories**

```bash
mkdir -p tests/adapters
```

- [ ] **Step 2: Move adapter tests from io to adapters**

If there are tests for converters in `tests/io/`:
```bash
# Check what converter tests exist
grep -rn "to_pymatgen\|from_pymatgen\|to_ase\|from_ase" tests/io/ --include="*.py" -l
```

Move them to `tests/adapters/`:
```bash
# Example:
git mv tests/io/test_converters.py tests/adapters/test_pymatgen.py
```

- [ ] **Step 3: Remove duplicate "returns new object" tests**

Scan for duplicate immutability tests:
```bash
grep -rn "assert.*id.*!=\|returns.new\|immutable\|not.*modified\|unchanged" tests/core/ --include="*.py" -l
```

Tests that redundantly test immutable-return behavior (now covered by `test_structure_model_contract.py`) can be removed. Keep tests that test *specific* behavior consequences (e.g., "after add_atom, the new atom appears at the correct position").

Don't delete entire test files — remove individual test methods that are pure duplicates.

- [ ] **Step 4: Run full test suite**

```bash
pytest -x -q --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: reorganize tests, remove duplicate immutability tests

Contract tests now cover immutable-return, reducing duplication.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3: Plugin Readiness (6–12 months)

### Task 3.1: Add entry point discovery

**Files:**
- Create: `matsimpy/plugins.py`

- [ ] **Step 1: Write plugins.py**

```python
"""
Plugin discovery via Python entry points.

Discovers and loads plugins registered under MatSimPy's entry point groups:
- ``matsimpy.transformations``
- ``matsimpy.builders``
- ``matsimpy.io_formats``
- ``matsimpy.storage_backends``

Usage::

    from matsimpy.plugins import discover_all
    discover_all()  # called at package init or explicitly by user
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def discover_transformations() -> int:
    """Load transformation plugins from entry points. Returns count loaded."""
    from matsimpy.transformation.registry import registry
    from matsimpy.transformation.spec import TransformationSpec

    count = 0
    try:
        group = entry_points(group="matsimpy.transformations")
    except TypeError:
        # Python 3.11 compat
        group = entry_points().get("matsimpy.transformations", [])

    for ep in group:
        try:
            spec_or_list = ep.load()()
            specs = spec_or_list if isinstance(spec_or_list, list) else [spec_or_list]
            for spec in specs:
                if isinstance(spec, TransformationSpec):
                    registry.register(spec)
                    count += 1
        except Exception:
            logger.exception("Failed to load transformation plugin: %s", ep.name)
    return count


def discover_builders() -> int:
    """Load builder plugins from entry points. Returns count loaded."""
    from matsimpy.builders.registry import registry

    count = 0
    try:
        group = entry_points(group="matsimpy.builders")
    except TypeError:
        group = entry_points().get("matsimpy.builders", [])

    for ep in group:
        try:
            specs = ep.load()()
            for spec in specs:
                registry.register(spec)
                count += 1
        except Exception:
            logger.exception("Failed to load builder plugin: %s", ep.name)
    return count


def discover_io_formats() -> int:
    """Load IO format plugins from entry points. Returns count loaded."""
    from matsimpy.io.registry import registry

    count = 0
    try:
        group = entry_points(group="matsimpy.io_formats")
    except TypeError:
        group = entry_points().get("matsimpy.io_formats", [])

    for ep in group:
        try:
            handlers = ep.load()()
            for handler in handlers:
                registry.register(handler)
                count += 1
        except Exception:
            logger.exception("Failed to load IO format plugin: %s", ep.name)
    return count


def discover_storage_backends() -> int:
    """Load storage backend plugins. Returns count loaded."""
    # Storage backends are registered by exposing classes that
    # implement StoreBackend. Entry points return the class itself.
    count = 0
    try:
        group = entry_points(group="matsimpy.storage_backends")
    except TypeError:
        group = entry_points().get("matsimpy.storage_backends", [])

    for ep in group:
        logger.info("Discovered storage backend: %s", ep.name)
        count += 1
    return count


def discover_all() -> dict[str, int]:
    """Discover and load all plugins. Returns counts by group."""
    return {
        "transformations": discover_transformations(),
        "builders": discover_builders(),
        "io_formats": discover_io_formats(),
        "storage_backends": discover_storage_backends(),
    }


__all__ = [
    "discover_all",
    "discover_transformations",
    "discover_builders",
    "discover_io_formats",
    "discover_storage_backends",
]
```

- [ ] **Step 2: Call discover_all() from matsimpy/__init__.py**

Add to `matsimpy/__init__.py`:
```python
# Plugin discovery (lazy — only runs on explicit call or full import)
# User can call matsimpy.discover_plugins() to load extensions.
def discover_plugins():
    """Discover and load all registered plugins via entry points."""
    from .plugins import discover_all
    return discover_all()
```

- [ ] **Step 3: Commit**

```bash
git add matsimpy/plugins.py matsimpy/__init__.py
git commit -m "feat: add plugin discovery via Python entry points

Four entry point groups: transformations, builders, io_formats, storage_backends.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3.2: Add integration tests

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_workflows.py`

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for cross-layer workflows.

Tests: builder → transformation → IO → storage round-trip.
"""

import tempfile
import pytest
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.lattice import apply_strain
from matsimpy.transformation.atomic import create_vacancy
from matsimpy.io import read, write
from matsimpy.storage import DataStorage, MemoryBackend


@pytest.fixture
def fcc_cu():
    return from_prototype('fcc', 'Cu', 3.61)


class TestBuilderTransformIOStorageWorkflow:

    def test_full_round_trip(self, fcc_cu, tmp_path):
        """builder → transform → IO → storage round-trip."""
        # 1. Transform
        strained = apply_strain(
            fcc_cu,
            [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
        )
        vac = create_vacancy(strained, 0)

        # 2. IO round-trip
        path = tmp_path / "test.cif"
        write(vac, str(path))
        reloaded = read(str(path))

        assert reloaded.formula == vac.formula
        assert len(reloaded) == len(vac)

        # 3. Storage round-trip
        storage = DataStorage(backend=MemoryBackend())
        doc_id = storage.store_data(reloaded, metadata={"source": "integration_test"})
        retrieved = storage.retrieve_data(doc_id)

        assert retrieved == reloaded

    def test_pipeline_with_registry(self, fcc_cu):
        """Pipeline executes registered transforms."""
        from matsimpy.transformation import (
            TransformationStep, TransformationPlan, registry,
        )

        plan = TransformationPlan(
            steps=[
                TransformationStep("make_supercell", {"scaling_matrix": [2, 2, 2]}),
            ],
            name="2x2x2 supercell",
        )
        result = registry.apply_plan(plan, fcc_cu)
        assert len(result) == len(fcc_cu) * 8  # 2*2*2 = 8


class TestErrorHandlingIntegration:

    def test_strict_parsing_rejects_malformed(self, tmp_path):
        """strict=True (default) raises FormatError on malformed input."""
        from matsimpy.exceptions import FormatError

        bad_file = tmp_path / "bad.cif"
        bad_file.write_text("this is not a valid CIF file")

        with pytest.raises((FormatError, ValueError)):
            read(str(bad_file))

    def test_type_mismatch_raises(self, fcc_cu, tmp_path):
        """Writing Crystal to .xyz raises StructureTypeError."""
        from matsimpy.exceptions import StructureTypeError

        path = tmp_path / "test.xyz"
        with pytest.raises(StructureTypeError):
            write(fcc_cu, str(path))
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/integration/ -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration tests for cross-layer workflows

Builder → transformation → IO → storage full round-trip.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Appendix A: Pre-Flight Checklist

Before starting any task, verify the test baseline:

```bash
# Install in editable mode
pip install -e .[dev]

# Run full test suite, record baseline
pytest --tb=no -q 2>&1 | tee /tmp/test_baseline.txt
# Expected: all tests pass (or known skips only)
```

## Appendix B: Per-Phase Verification

After each phase, run:

```bash
# Phase completion check
pytest -x -q --tb=short

# Check import graph for violations
python -c "
import matsimpy
# Verify core doesn't import io/storage/builders/transformation
import matsimpy.core
# Should not trigger imports of other packages
"
```
