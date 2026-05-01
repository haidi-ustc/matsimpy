# Composition Module Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `reduced_formula` and `anonymous_formula` properties to Composition, and fix `as_dict` to store the processed formula instead of raw input.

**Architecture:** Three independent changes in `matsimpy/core/composition.py`: a one-line `as_dict` fix, plus two new `@property` methods. All use existing internal helpers (`_composition`, `_chemical_formula`, `_get_sorted_element_counts`). No new files, no API breakage.

**Tech Stack:** Python stdlib (`math.gcd`, `string.ascii_uppercase`), existing `Element` lookups

---

### Task 1: Fix `as_dict` to store processed formula

**Files:**
- Modify: `matsimpy/core/composition.py:466`
- Modify: `tests/test_composition_comprehensive.py` (add test)

- [ ] **Step 1: Add failing test for as_dict round-trip with non-trivial sort_by**

In `tests/test_composition_comprehensive.py`, add this method to `TestCompositionComprehensive` after the existing `test_composition_as_dict` (line 140):

```python
def test_composition_as_dict_uses_processed_formula(self):
    """as_dict stores the processed formula, not raw input."""
    # Input "OH2" with element sorting produces "H2O"
    comp = Composition("OH2", sort_by="element")
    d = comp.as_dict()
    self.assertEqual(d["formula"], "H2O")  # processed, not raw "OH2"
    # Round-trip: from_dict(as_dict()) preserves the formula
    comp2 = Composition.from_dict(d)
    self.assertEqual(comp2.formula, "H2O")
    self.assertEqual(str(comp2), "H2O")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_composition_comprehensive.py::TestCompositionComprehensive::test_composition_as_dict_uses_processed_formula -v`

Expected: FAIL — `AssertionError: 'OH2' != 'H2O'`

- [ ] **Step 3: Fix `as_dict` — one-line change**

In `matsimpy/core/composition.py`, line 466, change:

```python
# Before:
"formula": self._input_formula,

# After:
"formula": self.formula,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_composition_comprehensive.py::TestCompositionComprehensive::test_composition_as_dict_uses_processed_formula -v`

Expected: PASS

- [ ] **Step 5: Run full composition test suite to check for regressions**

Run: `pytest tests/test_composition*.py -v`

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add matsimpy/core/composition.py tests/test_composition_comprehensive.py
git commit -m "fix: store processed formula in Composition.as_dict instead of raw input

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Add `reduced_formula` property

**Files:**
- Modify: `matsimpy/core/composition.py` (add `import math`, add property)
- Modify: `tests/test_composition_comprehensive.py` (add tests)

- [ ] **Step 1: Add `import math` to composition.py**

In `matsimpy/core/composition.py`, add `import math` after the existing `import functools` on line 26:

```python
import re
import json
import math
import functools
```

- [ ] **Step 2: Write failing tests for `reduced_formula`**

In `tests/test_composition_comprehensive.py`, add to `TestCompositionComprehensive`:

```python
def test_reduced_formula_basic(self):
    """GCD reduction: H4O2 -> H2O."""
    comp = Composition("H4O2")
    self.assertEqual(comp.reduced_formula, "H2O")

def test_reduced_formula_already_reduced(self):
    """Already reduced: Fe2O3 stays Fe2O3."""
    comp = Composition("Fe2O3")
    self.assertEqual(comp.reduced_formula, "Fe2O3")

def test_reduced_formula_single_element(self):
    """Single element: O2 -> O."""
    comp = Composition("O2")
    self.assertEqual(comp.reduced_formula, "O")

def test_reduced_formula_complex(self):
    """Complex: C6H12O6 -> CH2O."""
    comp = Composition("C6H12O6")
    self.assertEqual(comp.reduced_formula, "CH2O")

def test_reduced_formula_ternary(self):
    """Ternary: Ca2Mg2Si4O12 -> CaMgSi2O6 (GCD=2)."""
    comp = Composition("Ca2Mg2Si4O12")
    self.assertEqual(comp.reduced_formula, "CaMgSi2O6")

def test_reduced_formula_preserves_ordering(self):
    """Reduced formula preserves element ordering from self.formula."""
    comp = Composition("O2H4", sort_by=None)
    # formula = 'O2H4' with sort_by=None; reduced: gcd(2,4)=2 -> OH2
    self.assertEqual(comp.reduced_formula, "OH2")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_composition_comprehensive.py -k "test_reduced_formula" -v`

Expected: all FAIL — `AttributeError: 'Composition' object has no attribute 'reduced_formula'`

- [ ] **Step 4: Implement `reduced_formula` property**

In `matsimpy/core/composition.py`, add after the `canonical_formula` property (line 313):

```python
@property
def reduced_formula(self) -> str:
    """
    Formula with element counts divided by their greatest common divisor.

    Returns the formula with each element count divided by the GCD of all
    counts. Element ordering is preserved from the current formula.

    Returns:
        str: Reduced chemical formula.

    Examples:
        >>> Composition('H4O2').reduced_formula
        'H2O'
        >>> Composition('Fe2O3').reduced_formula
        'Fe2O3'
        >>> Composition('C6H12O6').reduced_formula
        'CH2O'
    """
    counts = list(self._composition.values())
    gcd = counts[0]
    for c in counts[1:]:
        gcd = math.gcd(gcd, c)
    if gcd <= 1:
        return self.formula
    # Build formula preserving current element ordering
    seen = set()
    parts = []
    for element in self._element_order:
        if element in self._composition and element not in seen:
            reduced_count = self._composition[element] // gcd
            parts.append(f"{element}{reduced_count if reduced_count > 1 else ''}")
            seen.add(element)
    for element in self._composition:
        if element not in seen:
            reduced_count = self._composition[element] // gcd
            parts.append(f"{element}{reduced_count if reduced_count > 1 else ''}")
            seen.add(element)
    return "".join(parts)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_composition_comprehensive.py -k "test_reduced_formula" -v`

Expected: all PASS

- [ ] **Step 6: Run full composition test suite for regressions**

Run: `pytest tests/test_composition*.py -v`

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add matsimpy/core/composition.py tests/test_composition_comprehensive.py
git commit -m "feat: add Composition.reduced_formula property

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Add `anonymous_formula` property

**Files:**
- Modify: `matsimpy/core/composition.py` (add property)
- Modify: `tests/test_composition_comprehensive.py` (add tests)

- [ ] **Step 1: Write failing tests for `anonymous_formula`**

In `tests/test_composition_comprehensive.py`, add to `TestCompositionComprehensive`:

```python
def test_anonymous_formula_binary(self):
    """Fe2O3 -> A2B3 (O=8->A, Fe=26->B)."""
    comp = Composition("Fe2O3")
    self.assertEqual(comp.anonymous_formula, "A2B3")

def test_anonymous_formula_ternary(self):
    """CaTiO3 -> A3BC (O=8->A, Ca=20->B, Ti=22->C)."""
    comp = Composition("CaTiO3")
    self.assertEqual(comp.anonymous_formula, "A3BC")

def test_anonymous_formula_single_element(self):
    """C -> A."""
    comp = Composition("C")
    self.assertEqual(comp.anonymous_formula, "A")

def test_anonymous_formula_single_element_with_count(self):
    """O2 -> A2."""
    comp = Composition("O2")
    self.assertEqual(comp.anonymous_formula, "A2")

def test_anonymous_formula_same_atomic_number(self):
    """Elements with distinct atomic numbers but same stoichiometry."""
    comp = Composition("NaCl")
    # Na=11->A, Cl=17->B (sorted by atomic_no ascending: Na first, Cl second)
    self.assertEqual(comp.anonymous_formula, "AB")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_composition_comprehensive.py -k "test_anonymous_formula" -v`

Expected: all FAIL — `AttributeError: 'Composition' object has no attribute 'anonymous_formula'`

- [ ] **Step 3: Implement `anonymous_formula` property**

In `matsimpy/core/composition.py`, add after the `reduced_formula` property:

```python
@property
def anonymous_formula(self) -> str:
    """
    Formula with element symbols replaced by A, B, C... in atomic number order.

    Elements are sorted by atomic number ascending, then assigned labels
    A, B, C, ... following pymatgen convention.

    Returns:
        str: Anonymized chemical formula.

    Examples:
        >>> Composition('Fe2O3').anonymous_formula
        'A2B3'
        >>> Composition('CaTiO3').anonymous_formula
        'A3BC'
        >>> Composition('NaCl').anonymous_formula
        'AB'
    """
    import string

    # Sort by atomic number ascending
    sorted_elements = sorted(
        self._composition.items(),
        key=lambda x: Element.get_element(x[0]).atomic_no,
    )
    # Assign labels A, B, C, ...
    labels = {}
    for i, (element, _) in enumerate(sorted_elements):
        labels[element] = string.ascii_uppercase[i]

    # Build formula in sorted (atomic number) order
    parts = []
    for element, count in sorted_elements:
        label = labels[element]
        parts.append(f"{label}{count if count > 1 else ''}")
    return "".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_composition_comprehensive.py -k "test_anonymous_formula" -v`

Expected: all PASS

- [ ] **Step 5: Run full composition test suite for regressions**

Run: `pytest tests/test_composition*.py -v`

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add matsimpy/core/composition.py tests/test_composition_comprehensive.py
git commit -m "feat: add Composition.anonymous_formula property

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Run full test suite (final verification)

- [ ] **Step 1: Run all core tests**

Run: `pytest tests/test_core*.py tests/test_composition*.py -v`

Expected: all pass

- [ ] **Step 2: Final commit (if any cleanup needed)**

```bash
git status
```
