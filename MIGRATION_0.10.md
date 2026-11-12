# Upgrading from 0.9.0 to 0.10.0

0.10.0 adds features and fixes bugs. It removes no API. The changes below can
still change what existing code gets back. The full list is in
[CHANGELOG.md](CHANGELOG.md).

## Results that change

| area | 0.9.0 | 0.10.0 |
|---|---|---|
| `HighSymmKpath` with one non-periodic axis | 3D path of the slab cell, with k-points along the vacuum axis (graphene: A, L, H) | 2D path of the layer (`bravais` is `mp`, `op`, `oc`, `tp` or `hp`); every k-point has zero along the vacuum axis |
| `HighSymmKpath` with fewer than two periodic axes | 3D path | `ValueError` |
| `from_prototype('wurtzite', ...)` | 2 atoms, space group P6mm | 4 atoms, P6_3mc |
| `crystal_a == crystal_b` | ignored `pbc` | a slab is no longer equal to the bulk crystal with the same cell |
| `matsimpy.io.read('POSCAR')`, `read('CONTCAR_relaxed')` | format chosen from the extension only, so these names failed | read as VASP POSCAR/CONTCAR |
| `matsimpy.io` reading a VASP 4 POSCAR (no element line) | unrelated parse error | `ValueError` that says VASP 4 is not supported; `calculator.vasp.inputs.Poscar` still reads VASP 4 files |
| `Vasprun.run_type` with `HFSCREEN = 0.207` | "PBEO or other Hybrid Functional" | "HSE06" |
| `Outcar` / `Vasprun` data the run does not contain | `IndexError` / `KeyError` | empty result or `None` |

## Errors that are now raised

- VASP data files (input sets, POTCAR hashes, vdW parameters) that are missing or
  broken raise `FileNotFoundError` or `FormatError`. In 0.9.0 they were read as
  `{}`, so a misspelled input set gave a set with no INCAR defaults.
- `Magmom` is immutable: setting an attribute or writing to `moment` raises.
  NaN and Inf moments are rejected.
- `Crystal.add_atom` and every other construction path reject NaN and Inf positions.
- `DataStorage.store_data` rejects plain-dict data with reserved metadata keys
  (`doc_id`, ...), as the MSONable path already did.

## POTCAR files

In 0.9.0 reading any POTCAR raised `KeyError`. In 0.10.0 POTCARs are read, but
MatSimPy ships no POTCAR reference data (POTCARs are copyrighted), so every
POTCAR gives `UnknownPotcarWarning`. To silence it:

```python notest
import warnings
from matsimpy.calculator.vasp.inputs import UnknownPotcarWarning

warnings.filterwarnings("ignore", category=UnknownPotcarWarning)
```

## Fixed output you may have worked around

- INCAR files written by `Incar.write_file`, `Incar.get_str` and
  `VaspCalculator.write_input` were unreadable (` =  ['ENCUT', 400.0]` lines).
  They are now `ENCUT = 400.0`. Files written by 0.9.0 must be written again.
- `Poscar.from_file` with default arguments, `Potcar(symbols)` and
  `VaspInput.run_vasp` raised `NameError` (`SETTINGS`). `SETTINGS` is now a
  read-only view of the `PMG_*` environment variables, such as `PMG_VASP_PSP_DIR`.

## New API

- `matsimpy.symmetry.get_prototype(crystal, symprec=None)` and
  `get_prototype_info(...)`: AFLOW-style identifiers such as `AB_cF8_225_a_b`.
- `matsimpy.symmetry.PrototypeDatabase`: a read-only map from identifier to
  structure names, with JSON load/save, `merge` and `with_structures`.
- `matsimpy.builders.bulk.build_prototype_database`, `structures_from_prototype`
  and `suggest_element_substitutions`. They replace the `CrystalPrototype` class of
  the 0.8.0 branch; its identifiers (`AB_cF2_Fm-3m_a_b`) differ from the new ones.
- `matsimpy.calculator.utils.micro_pyawk` takes pymatgen-style
  `(regex, predicate, action)` records.
- `matsimpy.io.FormatHandler.filename_patterns`: format handlers can match file
  names as well as extensions.
- `matsimpy.ai.executor.get_active_executor()` and `FunctionExecutor.skill_state`
  (each agent session has its own storage database).
