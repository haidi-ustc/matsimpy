# Composition Module Enhancements

**Date**: 2026-05-02
**Scope**: `matsimpy/core/composition.py` + tests

## Changes

### 1. Fix `as_dict` — use processed formula, not raw input

**Current**: `as_dict` stores `self._input_formula` (the raw string passed to `__init__`). `__str__` returns `self.formula` (processed through `_chemical_formula`). These diverge for inputs like `"OH2"`: `str(c)` = `"OH2"`, `as_dict()["formula"]` = `"OH2"` — but they diverge with `sort_by='element'`: `str(c)` = `"H2O"`, `as_dict()["formula"]` = `"OH2"`.

**Fix**: Store `self.formula` in `as_dict`. Round-trip via `from_dict(as_dict())` now produces the same formula string. The `sort_by` field is already stored separately and continues to be preserved.

**Line**: `composition.py:466` — change `"formula": self._input_formula` to `"formula": self.formula`.

### 2. Add `reduced_formula` property

Return the formula with element counts divided by their greatest common divisor.

- Compute `gcd = math.gcd(*self._composition.values())`
- Divide each count by gcd, generate formula preserving current element ordering (from `self.formula`)
- `C6H12O6` → `CH2O`, `H4O2` → `H2O`, `Fe2O3` → `Fe2O3` (already reduced), `O2` → `O`

### 3. Add `anonymous_formula` property

Return formula with element symbols replaced by A, B, C... in atomic-number order (matching pymatgen behavior).

- Sort elements by atomic number ascending
- Assign labels A, B, C, D, ... in that order
- Regenerate formula string with labels replacing symbols, preserving sorted order
- `Fe2O3` → `A2B3` (O=8→A, Fe=26→B)
- `CaTiO3` → `A3BC` (O=8→A, Ca=20→B, Ti=22→C)
- `NaCl` → `AB`
- `C` → `A`

### No Change

- `to_json` / `from_json` — both already exist. `to_json` is redundant with MSONable's inherited version but harmless.
- All existing properties and methods unchanged.

## Test Plan

- Update existing `test_composition_str` to verify `as_dict` round-trip consistency
- New tests for `reduced_formula`: basic (H4O2 → H2O), already-reduced (Fe2O3), single-element (O2), complex (C6H12O6)
- New tests for `anonymous_formula`: binary (Fe2O3 → A2B3), ternary (CaTiO3 → A3BC), single-element (C → A)
- Verify `__str__` and `repr` unchanged after as_dict fix
