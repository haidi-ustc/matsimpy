# Utils Reorganization — Design Spec

Date: 2026-06-06
Status: Design approved

## Summary

Consolidate general-purpose utility functions scattered across domain modules into `matsimpy/utils/`. Move `selection.py` to `analysis/`.

## Target Structure

```
matsimpy/utils/
├── __init__.py          # re-exports: validation, dict_utils, path_utils
├── validation.py        # validate_vector3, validate_positive_scalar, validate_integer_matrix3
├── dict_utils.py        # get_nested_value, set_nested_value, copy_properties
└── path_utils.py        # expand_path

matsimpy/analysis/
└── selection.py         # ← moved from utils/ (AtomSelection + 9 selection functions)

matsimpy/core/_validation.py       # keeps: normalize_species, validate_lattice, validate_pbc
                                    # loses: copy_properties → utils/dict_utils.py
matsimpy/transformation/_helpers.py # keeps: site_properties, rebuild_structure
                                    # loses: validate_* → utils/validation.py
matsimpy/config/utils.py           # loses: expand_path, get/set_nested_value → utils/
matsimpy/io/utils.py               # cleaned up: remove registry-replaced functions
```

## Implementation Steps

1. Create `utils/validation.py`, `utils/dict_utils.py`, `utils/path_utils.py`
2. Move `validate_*` from `transformation/_helpers.py` → `utils/validation.py`
3. Move `get_nested_value`, `set_nested_value` from `config/utils.py` → `utils/dict_utils.py`
4. Move `expand_path` from `config/utils.py` → `utils/path_utils.py`
5. Move `copy_properties` from `core/_validation.py` → `utils/dict_utils.py`
6. Move `selection.py` from `utils/` → `analysis/`
7. Update `utils/__init__.py` with curated re-exports
8. Update `analysis/__init__.py` with selection exports
9. Update `io/utils.py` — remove unused registry-replaced functions
10. Update all imports across codebase (~20 import sites)
11. Run full test suite
