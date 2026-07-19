# Final whole-branch review fix report

## Scope

- Replaced stale per-site pymatgen coordinate access in volumetric and XDATCAR writers with native `Crystal.frac_positions` iteration.
- Made volumetric noncollinear output depend on a complete `diff_x`/`diff_y`/`diff_z` set; partial component sets raise a clear `ValueError`, scalar `diff` output remains unchanged.
- Made XDATCAR species/count and lattice serialization native-compatible while preserving order and coordinate formatting.
- Added native scalar CHGCAR/LOCPOT/ELFCAR, noncollinear CHGCAR, partial-component validation, and XDATCAR string/file roundtrip regressions.

## RED

Command:

```text
pytest -q tests/calculator/test_vasp_outputs.py -k 'scalar_volumetric_native_write_and_read or noncollinear_chgcar_native_write_and_read or xdatcar_native_get_str_write_and_roundtrip'
```

Result: **5 failed, 12 deselected**. Scalar and noncollinear volumetric cases failed on `CrystalSite.frac_coords`; XDATCAR failed on the pymatgen-style species assumption. After the coordinate/species fix, the XDATCAR test continued to fail because native `Lattice.__str__` is descriptive rather than POSCAR matrix text, exposing the final native serialization incompatibility.

## GREEN

Initial focused regression command after the production fix:

```text
pytest -q tests/calculator/test_vasp_outputs.py -k 'scalar_volumetric_native_write_and_read or noncollinear_chgcar_native_write_and_read or xdatcar_native_get_str_write_and_roundtrip'
```

Result: **5 passed, 12 deselected**.

Fresh final focused outputs/volumetric verification:

```text
pytest -q tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_outputs_parity.py tests/io/test_volumetric.py
```

Result: **37 passed, 23 warnings**.

Architecture boundary verification:

```text
pytest -q tests/architecture/test_vasp_no_pymatgen.py
```

Result: **3 passed**.

Full calculator VASP suite:

```text
pytest -q $(rg --files tests/calculator | rg '/test_vasp')
```

Result: **101 passed, 34 warnings**.

Additional hygiene in the final chained verification:

```text
git diff --check
```

Result: exit code 0, no output. Earlier in the cycle, `python -m compileall -q matsimpy/calculator/vasp/outputs.py tests/calculator/test_vasp_outputs.py` also exited 0.

Warnings were pre-existing POTCAR lookup, deprecation/future, and optional pinned-pymatgen oracle warnings; no test failures occurred. Production VASP modules remain free of pymatgen imports.
