# Builders Recovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move alloy, defects, interface, and adsorbate modules from transformation back to builders, with builders internally depending on transformation functions.

**Architecture:** Reverse the Phase 2 refactoring move. Files return to builders/ with imports pointing to transformation for shared operations (substitute, etc.). No code duplication.

**Tech Stack:** Python 3.10+, numpy, git

---

### Task 1: Move files from transformation to builders

**Files:**
- Move: `matsimpy/transformation/atomic/defects.py` → `matsimpy/builders/defects/point.py`
- Move: `matsimpy/transformation/atomic/adsorbate.py` → `matsimpy/builders/surface/adsorbate.py`
- Move: `matsimpy/transformation/chemical/alloy_random.py` → `matsimpy/builders/alloy/random.py`
- Move: `matsimpy/transformation/chemical/alloy_ordered.py` → `matsimpy/builders/alloy/ordered.py`
- Move: `matsimpy/transformation/chemical/alloy_heusler.py` → `matsimpy/builders/alloy/heusler.py`
- Move: `matsimpy/transformation/structural/interface.py` → `matsimpy/builders/interface/__init__.py`

- [ ] **Step 1: Recreate builder subpackage directories**

```bash
mkdir -p matsimpy/builders/alloy
mkdir -p matsimpy/builders/defects
mkdir -p matsimpy/builders/interface
```

- [ ] **Step 2: Move the files**

```bash
git mv matsimpy/transformation/atomic/defects.py matsimpy/builders/defects/point.py
git mv matsimpy/transformation/atomic/adsorbate.py matsimpy/builders/surface/adsorbate.py
git mv matsimpy/transformation/chemical/alloy_random.py matsimpy/builders/alloy/random.py
git mv matsimpy/transformation/chemical/alloy_ordered.py matsimpy/builders/alloy/ordered.py
git mv matsimpy/transformation/chemical/alloy_heusler.py matsimpy/builders/alloy/heusler.py
git mv matsimpy/transformation/structural/interface.py matsimpy/builders/interface/__init__.py
```

- [ ] **Step 3: Fix imports in moved files**

In `matsimpy/builders/defects/point.py`, change:
```python
from ..chemical.substitution import substitute
```
to:
```python
from ...transformation.chemical.substitution import substitute
```

In `matsimpy/builders/alloy/random.py`, change:
```python
from .substitution import substitute
```
to:
```python
from ...transformation.chemical.substitution import substitute
```

In `matsimpy/builders/alloy/ordered.py`, change:
```python
from .substitution import substitute
```
to:
```python
from ...transformation.chemical.substitution import substitute
```

In `matsimpy/builders/surface/adsorbate.py`, change:
```python
from ...core import Crystal, Molecule
```
to:
```python
from ...core import Crystal, Molecule
```
(no change needed — same depth)

In `matsimpy/builders/interface/__init__.py`, change:
```python
from ...core import Crystal, Lattice
```
to:
```python
from ...core import Crystal, Lattice
```
(no change needed — same depth)

In `matsimpy/builders/alloy/heusler.py`, change:
```python
from ...core import Crystal, Lattice
```
to:
```python
from ...core import Crystal, Lattice
```
(no change needed — same depth)

- [ ] **Step 4: Create alloy/__init__.py and defects/__init__.py**

```python
# matsimpy/builders/alloy/__init__.py
"""Alloy structure builders.

Generate alloy structures by modifying base structures using transformations.
"""
from .random import generate_random_alloy
from .ordered import generate_ordered_alloy, generate_intermetallic
from .heusler import (
    build_heusler,
    build_full_heusler,
    build_half_heusler,
    build_inverse_heusler,
)

__all__ = [
    "generate_random_alloy",
    "generate_ordered_alloy",
    "generate_intermetallic",
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
]
```

```python
# matsimpy/builders/defects/__init__.py
"""Point defect builders.

Create point defects in crystal structures using transformation operations.
"""
from .point import (
    create_vacancy,
    create_interstitial,
    create_substitution,
    create_frenkel,
    create_schottky,
    create_antisite,
)

__all__ = [
    "create_vacancy",
    "create_interstitial",
    "create_substitution",
    "create_frenkel",
    "create_schottky",
    "create_antisite",
]
```

- [ ] **Step 5: Run tests to verify moves work**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/builders/ -x -q --tb=short
```

Expected: All tests pass (or known skips for optional deps).

---

### Task 2: Clean up transformation module (remove moved exports)

**Files:**
- Modify: `matsimpy/transformation/atomic/__init__.py`
- Modify: `matsimpy/transformation/chemical/__init__.py`
- Modify: `matsimpy/transformation/structural/__init__.py`
- Modify: `matsimpy/transformation/_register.py`

- [ ] **Step 1: Clean atomic/__init__.py**

Remove the defect and adsorbate imports:

```python
# matsimpy/transformation/atomic/__init__.py
"""Atom-level operations (manipulation, organization). Works for both Crystal and Molecule."""

from .manipulation import move_atoms, swap_atoms, merge_atoms, split_atom
from .organization import sort_atoms, center_structure, perturb_positions

__all__ = [
    "move_atoms", "swap_atoms", "merge_atoms", "split_atom",
    "sort_atoms", "center_structure", "perturb_positions",
]
```

- [ ] **Step 2: Clean chemical/__init__.py**

Remove alloy imports:

```python
# matsimpy/transformation/chemical/__init__.py
"""Chemical transformations (substitution). Works for both Crystal and Molecule."""

from .substitution import substitute, substitute_all

__all__ = ["substitute", "substitute_all"]
```

- [ ] **Step 3: Clean structural/__init__.py**

Remove interface import:

```python
# matsimpy/transformation/structural/__init__.py
"""Structural operations (supercell, molecular operations)."""

from .supercell import make_supercell
from .molecular import (
    fragment_molecule, align_molecules, generate_conformers, merge_molecules,
)

__all__ = [
    "make_supercell",
    "fragment_molecule", "align_molecules",
    "generate_conformers", "merge_molecules",
]
```

- [ ] **Step 4: Clean _register.py**

Remove the alloy, defects, adsorbate, interface spec registrations. Change the file:

Remove these imports:
```python
from .atomic.defects import (create_vacancy, create_interstitial, create_substitution,
    create_frenkel, create_schottky, create_antisite)
from .atomic.adsorbate import add_adsorbate
from .chemical.alloy_random import generate_random_alloy
from .chemical.alloy_ordered import generate_ordered_alloy, generate_intermetallic
from .chemical.alloy_heusler import (build_heusler, build_full_heusler,
    build_half_heusler, build_inverse_heusler)
from .structural.interface import create_simple_interface
```

Remove their corresponding registry.register() calls.

- [ ] **Step 5: Run transformation tests**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/transformation/ -x -q --tb=short
```

---

### Task 3: Update builders/__init__.py and _register.py

**Files:**
- Modify: `matsimpy/builders/__init__.py`
- Modify: `matsimpy/builders/_register.py`

- [ ] **Step 1: Update builders/__init__.py**

Add back alloy, defects, interface subpackage imports and exports:

```python
# In the docstring, add back descriptions for alloy/, defects/, interface/
# In the imports section, add:
from .alloy import (
    generate_random_alloy, generate_ordered_alloy, generate_intermetallic,
    build_heusler, build_full_heusler, build_half_heusler, build_inverse_heusler,
)
from .defects import (
    create_vacancy, create_interstitial, create_substitution,
    create_frenkel, create_schottky, create_antisite,
)
from .interface import create_simple_interface
from .surface import add_adsorbate

# In the submodule imports section:
from . import alloy
from . import defects
from . import interface
```

- [ ] **Step 2: Update builders/_register.py**

Register the recovered builder functions with BuilderRegistry:

```python
# Recover alloy from subpackage import
try:
    from .alloy.random import generate_random_alloy
    from .alloy.ordered import generate_ordered_alloy, generate_intermetallic
    for fn, name in [
        (generate_random_alloy, "generate_random_alloy"),
        (generate_ordered_alloy, "generate_ordered_alloy"),
        (generate_intermetallic, "generate_intermetallic"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="alloy", callable=fn,
            description=f"Generate {name.replace('generate_', '').replace('_', ' ')}",
            output_type=Crystal,
        ))
except ImportError:
    pass
# (Do similar for heusler, defects, adsorbate, interface functions)
```

- [ ] **Step 3: Run full test suite**

```bash
/opt/miniconda3/envs/pmg/bin/pytest --tb=no -q
```

---

### Task 4: Update test imports

**Files:**
- Modify: `tests/builders/test_builders_alloy.py`
- Modify: `tests/builders/test_builders_defects.py`
- Modify: `tests/builders/test_builders_interface.py`
- Modify: `tests/builders/test_heusler.py`
- Modify: `tests/builders/test_builders_surface.py`
- Modify: `tests/contracts/test_transformation_contract.py`

- [ ] **Step 1: Revert test imports from transformation back to builders**

In `tests/builders/test_builders_alloy.py`:
```python
# Change:
from matsimpy.transformation.chemical import (...)
# To:
from matsimpy.builders.alloy import (...)
```

In `tests/builders/test_builders_defects.py`:
```python
# Change:
from matsimpy.transformation.atomic import (...)
# To:
from matsimpy.builders.defects import (...)
```

In `tests/builders/test_builders_interface.py`:
```python
# Change:
from matsimpy.transformation.structural import create_simple_interface
# To:
from matsimpy.builders.interface import create_simple_interface
```

In `tests/builders/test_heusler.py`:
```python
# Change:
from matsimpy.transformation.chemical.alloy_heusler import (...)
# To:
from matsimpy.builders.alloy.heusler import (...)
```

In `tests/builders/test_builders_surface.py`:
```python
# Change:
from matsimpy.transformation.atomic import add_adsorbate
# To:
from matsimpy.builders.surface import add_adsorbate
```

In `tests/contracts/test_transformation_contract.py` — no change needed since it parametrizes over the registry; the registry will automatically pick up the new set of transforms.

- [ ] **Step 2: Run full test suite**

```bash
/opt/miniconda3/envs/pmg/bin/pytest --tb=no -q
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add matsimpy/builders/ matsimpy/transformation/ tests/
git commit -m "refactor: move alloy/defects/interface/adsorbate back to builders

Builders internally depend on transformation functions (substitute, etc.).
No code duplication. Builders have canonical implementations.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Run full test suite and verify

- [ ] **Step 1: Full test suite**

```bash
/opt/miniconda3/envs/pmg/bin/pytest --tb=no -q
```

Expected: All tests pass (same count as baseline).

- [ ] **Step 2: Verify import paths**

```bash
/opt/miniconda3/envs/pmg/bin/python -c "
from matsimpy.builders.alloy import generate_random_alloy, build_heusler
from matsimpy.builders.defects import create_vacancy
from matsimpy.builders.interface import create_simple_interface
from matsimpy.builders.surface import add_adsorbate
print('All builder imports OK')
"
```

- [ ] **Step 3: Commit any final fixes**

```bash
git add -A && git commit -m "chore: final test fixes after builders recovery"
```
