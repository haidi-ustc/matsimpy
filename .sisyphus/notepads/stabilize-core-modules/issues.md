# Issues

## Calculator integration broken by Phase 4 (__hash__ = None)
- `matsimpy/calculator/base.py:107` calls `hash(structure)` which now raises TypeError
- The `_needs_calculation()` method in structure.py was updated to use `_structural_hash()` instead
- But calculator/base.py is outside matsimpy/core/ scope per task constraints
- 29 calculator tests in tests/calculator/ fail as a result
- Fix: update calculator/base.py:107 to use `structure._structural_hash()` instead of `hash(structure)`
