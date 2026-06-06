# Builders Recovery — Design Spec

Date: 2026-06-06
Status: Design approved
Context: Reverses the Phase 2 move of alloy, defects, interface, adsorbate from transformation back to builders.

## Summary

Move alloy, defects, interface, and adsorbate modules back to `builders/`. Builders internally depend on transformation functions (`substitute`, etc.) — no code duplication. Keep transformation clean (only pure operations).

## Moves

| File | From | To |
|---|---|---|
| `defects.py` | `transformation/atomic/` | `builders/defects/` |
| `adsorbate.py` | `transformation/atomic/` | `builders/surface/` |
| `alloy_random.py` | `transformation/chemical/` | `builders/alloy/` |
| `alloy_ordered.py` | `transformation/chemical/` | `builders/alloy/` |
| `alloy_heusler.py` | `transformation/chemical/` | `builders/alloy/` |
| `interface.py` | `transformation/structural/` | `builders/interface/` |

## Import Pattern

Builder files import transformation functions internally:

- `builders/defects/point.py` → `from ...transformation.chemical.substitution import substitute`
- `builders/alloy/random.py` → `from ...transformation.chemical.substitution import substitute`
- `builders/alloy/ordered.py` → `from ...transformation.chemical.substitution import substitute`
- `builders/alloy/heusler.py` → self-contained constructor
- `builders/surface/adsorbate.py` → self-contained
- `builders/interface/__init__.py` → self-contained

## Cleanup

- **Transformation `__init__.py`**: remove alloy/defects/adsorbate/interface exports
- **Transformation `_register.py`**: remove alloy/defects/adsorbate/interface specs
- **Transformation atomic/chemical/structural `__init__.py`**: remove re-exports of moved functions
- **Builders `__init__.py`**: add back alloy, defects, interface subpackage imports + curated exports
- **Builders `_register.py`**: register recovered builder functions
- **Tests**: update imports from `matsimpy.transformation.*` back to `matsimpy.builders.*`

## Non-Goals

- No changes to function implementations
- No changes to core, IO, storage, or other modules
- Transformation keeps `substitute` and other pure operations
