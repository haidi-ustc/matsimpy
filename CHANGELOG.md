# Changelog

## Unreleased

### Added
- `HighSymmKpath` supports two-dimensional crystals (`pbc` with exactly one `False`
  axis, e.g. a monolayer in a slab cell). The layer is classified as one of the five 2D
  Bravais lattices from its in-plane symmetry, not just its cell shape: `bravais` is
  `mp`, `op`, `oc`, `tp` or `hp`, and `kpath["variant"]` is ASE's name (`OBL`, `RECT`,
  `CRECT`, `SQR`, `HEX2D`). When the atoms break the cell's symmetry, the path of the
  lower symmetry is used. The k-points are fractional coordinates of the input cell's
  reciprocal lattice, with zero along the vacuum axis.
- Crystal prototype identifiers: `matsimpy.symmetry.get_prototype(crystal)` returns an
  identifier such as `AB_cF2_Fm-3m_a_b` (rocksalt), the same for every crystal of that
  structure type, independent of the elements, atom order and supercell.
  `get_prototype_info` returns its parts as a frozen `PrototypeInfo`.
  `PrototypeDatabase` is a read-only map from identifier to structure names, with JSON
  load/save; `merge` and `with_structures` return a new database.
  `matsimpy.builders.bulk` adds `build_prototype_database(files)`,
  `structures_from_prototype(database, prototype, ...)` (new crystals by element
  substitution) and `suggest_element_substitutions`. The identifiers are the same as
  in branch1's `CrystalPrototype`, which this replaces.

### Fixed
- VASP: `Vasprun.run_type` reported HSE06 runs with `HFSCREEN=0.207` as
  "PBEO or other Hybrid Functional", because 0.2 was matched exactly. Any `HFSCREEN`
  from 0.2 to 0.21 is now HSE06. The label is stored in `ComputedEntry.parameters`.
- VASP: `Procar.get_projection_on_elements` raised `AttributeError`, because it called
  `.symbol` on species, which are plain strings. It now also raises a clear `ValueError`
  when the structure and the PROCAR have different numbers of atoms.
- VASP: packaged data files (input-set YAMLs, POTCAR hashes and statistics, vdW
  parameters) were loaded by a helper that returned `{}` on any error. A misspelled input
  set gave a set with no INCAR defaults. `POTCAR_STATS_PATH` named a file that does not
  exist (`potcar-summary-stats.json.bz2`), so POTCAR validation had no reference data.
  Loading now raises `FileNotFoundError` or `FormatError`, and `POTCAR_STATS_PATH` is
  `vasp_potcar_stats.json`.
- `calculator.utils.clean_lines` now removes `#` comments. POSCAR files with a comment
  after the scale or lattice values raised `ValueError`. LAMMPS data headers such as
  `2 atoms  # comment` were not recognised, so the file could not be read.
- Core: `add_atom` and `_construct` accepted NaN/Inf positions. Only the public
  constructor checked for them. The check now runs in `_set_state`, which every
  construction path goes through, and at the start of `add_atom`.
- Core: `==` ignored `pbc`, so a slab equalled the bulk crystal with the same cell. The
  calculator cache key already included `pbc`.
- Storage: `DataStorage.store_data` did not check plain-dict data for reserved metadata
  keys (`doc_id`, ...), which the MSONable path already rejected. Existing document IDs
  are unchanged.
- AI: the storage skill used one module-level database shared by every agent in the
  process. Each agent session (executor) now has its own database, kept in the new
  `FunctionExecutor.skill_state`. `matsimpy.ai.executor.get_active_executor()` is
  public.

- **VASP: every INCAR file was unreadable.** `calculator.utils.str_delimited` wrote
  lines like ` =  ['ENCUT', 400.0]` instead of `ENCUT = 400.0`. This affected
  `Incar.get_str`, `write_file` and `VaspCalculator.write_input`. VASP cannot parse such
  a file, and `Incar.from_file` read it back as an empty INCAR.
- VASP: the `Outcar` readers `read_pseudo_zval`, `read_igpar`, `read_lepsilon`,
  `read_lepsilon_ionic`, `read_internal_strain_tensor` and `read_lcalcpol` always failed
  with "could not be parsed". `micro_pyawk` expected a `{key: pattern}` dict, but its
  callers pass pymatgen-style `(regex, predicate, action)` records. It moved to
  `calculator.utils` and now takes those records.
- VASP: `SETTINGS` was used but never defined, so `Poscar.from_file` (with default
  arguments), `Potcar(symbols)` and `VaspInput.run_vasp` raised `NameError`. It is now a
  read-only view of the `PMG_*` environment variables (`PMG_VASP_PSP_DIR`, ...).
- VASP: reading data that a run does not contain now returns empty or `None`, as
  current pymatgen does. Before, it raised: `IndexError` from `Outcar.read_elastic_tensor`,
  `read_piezo_tensor` and the NMR readers, and `KeyError` from
  `Vasprun.optical_absorption_coeff`.
- `Magmom` is immutable. `moment` is a read-only array, attributes cannot be set, and
  NaN/Inf values are rejected. Its serialized form is unchanged.
- VASP: removed the local `get_el_sp` copy. POTCAR symbols in `Poscar.from_file` are
  resolved with the core `normalize_species`. The old `map(get_el_sp, ...)` call was
  never evaluated, so the names were never checked.
- VASP: reading any POTCAR raised `KeyError`: `Potcar.from_file`, `Potcar(symbols)`, and
  `Poscar.from_file` with a POTCAR in the same directory. The POTCAR checks looked up
  the empty reference tables by functional. A POTCAR that cannot be checked now gives
  `UnknownPotcarWarning` and is still read. Input sets warn about a POTCAR functional
  mismatch only when the reference data shows one.
- `matsimpy.io.read` now recognises files named `POSCAR` and `CONTCAR`, including
  `POSCAR.*`, `POSCAR_*` and the same CONTCAR forms. Before, it used only the file
  extension. Format handlers can declare name patterns (`FormatHandler.filename_patterns`).
- `matsimpy.io` POSCAR reader: a POSCAR with an empty first (comment) line was read
  wrongly, because the empty line was dropped and every later line shifted by one.
  A VASP 4 file, which has no element-symbol line, now raises a `ValueError` that says
  VASP 4 is not supported. Before, it raised an unrelated parse error.
- `HighSymmKpath` ignored `pbc`. A monolayer got the 3D path of its slab cell, which
  includes k-points along the vacuum axis (for graphene: A, L and H). Structures with
  fewer than two periodic axes now raise `ValueError` instead of getting a 3D path.
- `THIRD_PARTY_NOTICES.md` is back and is shipped in the sdist and the wheel.
  `symmetry/kpath.py` adapts ASE code under BSD-2-Clause, which requires the notice.
  The file had been deleted, although the source header still pointed to it.

### Known issues
- MatSimPy ships no POTCAR reference data, because POTCARs are copyrighted. The packaged
  files (`vasp_potcar_stats.json` and both hash files) are empty (`{}`). POTCARs are
  read but cannot be checked: every POTCAR gives `UnknownPotcarWarning`.
- There are two POSCAR readers: `matsimpy.io` (`matsimpy/io/vasp.py`) and
  `calculator.vasp.inputs.Poscar`. Only the second reads VASP 4 files, where species
  names follow the coordinates or come from a POTCAR.
- Prototype identifiers use spglib's Wyckoff letters without reducing them over the
  space group's Euclidean normalizer. Two descriptions of the same crystal can therefore
  differ in the letters: diamond is `a` with `to_primitive=True` and `b` with `False`,
  and zincblende is `a_c` and `a_d`. The Pearson part counts the atoms of the
  standardized cell, which is the primitive cell by default (rocksalt `cF2`; the
  crystallographic symbol is `cF8`). The default `symprec=1e-5` is too tight for
  coordinates given to 6 decimals: a real MnO POSCAR comes out as `I4mm`, and
  `symprec=1e-3` gives `Fm-3m`. All three behaviours are kept from branch1, so
  identifiers stay comparable with existing databases.

### Tests
- Restored `tests/calculator/fixtures` (VASP and Gaussian outputs), which the 0.8.5–0.9.0
  sdists did not include. 24 real-file tests that were skipped now run.
- The VASP calculator test now checks real `vasprun.xml` values: energy, final-step forces,
  and stress converted from kBar to eV/Å³ with tension positive. A Gaussian test reads a real
  multi-step log and checks the final SCF energy in eV.
- `tests/test_sdist_contents.py` builds the sdist and fails if the test fixtures or the
  VASP package data are missing from it.
- VASP test data comes only from the pymatgen 2026.10.24 test files, unmodified. Sources
  are listed in `tests/calculator/fixtures/vasp/PROVENANCE.md`. `KPOINTS` is now the
  original file; the old copy had an extra trailing space. Tests that built VASP data by
  hand now use real files: INCAR, KPOINTS (7 styles), POSCAR, CHGCAR (no spin, spin,
  noncollinear), LOCPOT, ELFCAR, XDATCAR and charged vasprun files. Each is also compared
  against pymatgen. POTCAR tests use only pymatgen's placeholder POTCARs.
- `test_crystal_from_file_poscar` looked for a file that does not exist and silently
  passed. It now reads a real POSCAR and checks it.

## 0.9.0 — 2026-11-12

A deliberately **incompatible** refactor. Every removed or changed API, with its replacement, is
listed in [MIGRATION_0.9.md](MIGRATION_0.9.md). Readers for files written by 0.8.x are kept.

### Architecture
- `matsimpy.core` no longer imports higher layers. `tests/architecture/test_layering.py` enforces
  utils → core → analysis/symmetry/io → transformation/builders → calculator → ai.
- I/O, symmetry, supercell, perturbation and random-crystal helpers are module functions only.
  The `Crystal`/`Molecule` facade methods are removed.

### Core data model
- `Lattice.matrix` is the only matrix accessor.
- Per-frame trajectory data lives in frame `metadata`.
- `Site`/`CrystalSite` are frozen snapshots; `position` is always Cartesian.
- Structures keep one native coordinate array. A crystal also keeps its exact Cartesian rows
  through `remove_atom`, `sort_atoms`, `add_atom` and `sites`.
- `add_atom` and `__str__` each have a single implementation for Molecule and Crystal.
- `crystal.sites` is about 4.5× faster.

### Calculators
- Calculators are stateless. `compute(structure) -> Results` is the core API, and the getters
  require the structure.
- External codes subclass `FileIOCalculator`, with `write_input(structure, directory)` and
  `read_results(directory) -> Results`.
- All constructor arguments are `parameters`, so `as_dict`/`from_dict` round-trips them.

### Fixed
- VASP: forces were missing for ordinary runs. Stress is now read and converted to eV/Å³.
- Gaussian: energy was reported in Hartree and is now in eV.
- Missing Gaussian/LAMMPS output raises `FileNotFoundError` instead of returning an empty result.
- MatterSim: a missing prediction was reported as 0 and is now `None`.
- The `matsimpy-ai` terminal now shows command data (session list, skill details), not only the
  one-line hint.

### AI
- `AIEngine` is removed; use `Agent`. The CLI uses `ReplController.for_agent(agent)`.
  `/workspace`, `/model`, `/load`, `/unload`, `/memory` and `/save` are available in the terminal.

### Housekeeping
- Removed the empty `matsimpy.visualization` package.
- Untracked `__pycache__` files.

## 0.8.7 — 2026-11-12

This release unifies the data that travels alongside a structure: per-site properties,
structure-level metadata and calculator results. It is backward compatible for public APIs.

### Added
- **Per-site property column API** on `Crystal` and `Molecule`:
  - `site_property(name, default=...)` returns one value per atom (copied). It raises
    `KeyError` when a site lacks the property and no `default` is given.
  - `with_site_property(name, values)` returns a new structure. ndarray input is converted with
    `tolist()`.
  - `without_site_property(*names)`.

  The row view `site_properties` and constructor input are unchanged.
- **`metadata`**: structure-level, read-only mapping. It is set via the `metadata=` constructor
  argument, `with_metadata(**updates)` or `without_metadata(*keys)`.
  - Serialized exactly: ndarrays keep dtype and values through `as_dict`, Monty JSON, the io
    JSON format, pickle and deepcopy.
  - Kept by `copy()`, `with_*()` and `set_pbc()`. Dropped by add/remove/substitute/sort/wrap
    and transformations, because such data would no longer describe the new structure.
  - Not part of the calculator cache key.
- **`calc.compute(structure) -> Results`**: frozen dataclass with `energy`, `forces` (read-only
  array), `stress` (read-only 3x3), `stress_voigt` and `extra` (read-only mapping).
  - Exported as `matsimpy.calculator.Results`.
  - The getters (`get_potential_energy` etc.) and `get_results` are built on it.
- **LRU result cache** on calculators (`cache_size`, default 8). Switching between structures
  no longer recomputes; 0.8.5/0.8.6 cached only the last structure.
  - `set_parameters()` and `Mattersim.set_model()` clear it.
  - `read_results()` replaces the entry of the structure it belongs to.

### Changed (internal)
- **Single construction path.** `__init__` (after input conversion) and the internal
  `_construct` both assign state through `_set_state`, so the two paths cannot drift apart.
  This mismatch caused several 0.8.x bugs.
- Site-property storage, `site_properties`, and the per-atom filter/reorder logic moved from
  `Crystal`/`Molecule` into `Structure`. The dead `_extra_dict_fields` hook was removed.
  `set_pbc()` and `copy()` go through one `_replace()` helper.
- Structure side data stored in an ad-hoc `_extra_properties` attribute (which `copy()` lost)
  is now metadata: Vasprun trajectory forces, selective dynamics, Vaspout per-site moments,
  VASP input-set extras, Trajectory frames.
  - Trajectory files written by ≤0.8.6, with a separate `extra_properties` block, still load.
- `normalize_species` has a fast path for canonical symbols. `Crystal(...)` with 4 000 atoms
  takes 6.6 ms (0.8.6: 8.4 ms).
- `get_stress()` validates the stress shape. Before, an invalid shape was returned unchanged
  when `voigt=False`.

### Tests
- New `tests/core/test_core_api_087.py` (14 tests): column API, metadata propagation and
  exact round trips, `__init__`/`_construct` state equivalence, frozen `Results`, LRU eviction
  and invalidation.
- Trajectory and cache tests were migrated to `metadata` and the LRU semantics. Added a reader
  test for ≤0.8.6 trajectory files.

## 0.8.6 — 2026-11-12

This release removes legacy code. The APIs deprecated in 0.8.1 and 0.8.5 are deleted now
instead of in 0.9.0, along with code that could never run. **Breaking:** see the migration
table below.

Local verification of 0.8.5 (`verify_085.sh`, Python 3.12, NumPy 2.3.5) passed:
- full suite: 1541 passed, 0 failed;
- MatterSim: two queries on one structure ran one computation, and the new and old APIs
  gave bit-identical energy and forces (E = -5.822546005249023 eV).

### Removed (breaking)
| removed | use instead |
|---|---|
| `structure.calc = calc`, `structure.calc` | `calc.get_results(structure)` |
| `Structure.get_potential_energy()` / `get_forces()` / `Crystal.get_stress()` | `calc.get_potential_energy(structure)` / `calc.get_forces(structure)` / `calc.get_stress(structure, voigt=...)` |
| `crystal.site_properties = [...]` / `molecule.site_properties = [...]` | `new = structure.with_site_properties([...])` |
| `get_valid_magmom_struct(structure, inplace=...)` | `get_valid_magmom_struct(structure)`, which always returns a new structure |
| `Calculator.get_stress(True)` (positional bool) | `get_stress(voigt=True)`; a non-structure first argument now raises `TypeError` |
| pickle migration of ≤0.8.0 state (`lattice`, `pbc`, `lattice_vectors` keys) | re-create the object from its JSON/`as_dict` form |
| `Crystal._get_sorted_sites`, `Crystal._get_sorted_element_counts` (private, unused) | `sort_atoms()`, `Composition` |
| `lammps.utils.Polymer`, `PackmolRunner`, `BabelMolAdaptor`/`PackmolBoxGen` stubs, demo `__main__` | none: these were never ported and could not run. `LammpsRunner` stays |
| `lammps.data.Topology.from_bonding` (raised `NotImplementedError`) | `Topology(molecule, topologies={"Bonds": [...]})` |
| `scripts/cleanup_test_imports.py` (one-off migration, already applied) | none |

`structure.calc` is kept only as a stub that raises `AttributeError` with the migration hint.
Without it, `structure.calc = calc` in old code would silently create a plain attribute and
fail quietly.

### Kept on purpose
- Readers for existing saved data: the Trajectory direct-frame format, the storage
  `_stable_doc_id_legacy`, and the AI memory, skill and draft migrations. Deleting them would make
  existing files unreadable.
- `AIEngine` (deprecated). The `matsimpy-ai` CLI/REPL is still built on it, so removing it means
  porting the REPL onto `Agent`. That is a separate AI-layer refactor.
- The vendored `DictSet` (pymatgen deprecation, removal date 2025-12-31). Its tests are in the
  pymatgen group that is deferred by request.

### Tests
- The deprecation tests are replaced by tests that assert the old APIs are gone. Removing
  `structure.calc` must fail loudly.
- The LJ integration tests use the calculator-side API.
- Suite: 1514 passed, 0 failed, using the repository's own VASP data files.

## 0.8.5 — 2026-11-12

Calculators are decoupled from structures, and duplicated code in the core classes is removed.
Every change is backward compatible; the old patterns emit warnings.

### Added
- `Calculator.get_results(structure)`, plus an optional `structure` argument on
  `get_potential_energy`, `get_forces` and `get_stress`.
  - Results are cached **on the calculator**, keyed by the structure's exact fingerprint
    (species, coordinates, lattice, PBC, site properties).
  - One calculator can serve many structures. Several queries on the same structure compute once.
    An equal `copy()` reuses the cached result.
  - `get_results()` returns copies, so callers cannot change the cache.
  - Calls without a structure behave as before (they return the last `calculate()` result).
    `get_stress(True)` still means `voigt=True`.

### Deprecated (removal in 0.9.0)
- `structure.calc = calc` now emits a `DeprecationWarning`. `structure.get_potential_energy()`,
  `get_forces()` and `get_stress()` still work and delegate to the calculator-side cache;
  `Structure._needs_calculation` is removed. Use `calc.get_potential_energy(structure)`.
- `get_valid_magmom_struct()` called without `inplace` emits a `FutureWarning`. The default
  changes from `True` (edit the input) to `False` in 0.9.0.

### Simplified
- `Crystal.substitute` and `Molecule.substitute` were near-identical copies of
  `Structure.substitute` and have been removed; the base method has the documentation.
  The base `substitute`/`substitute_all` now clone with `_clone_kwargs()`, so a Crystal's Cartesian
  array is carried over bit-exactly. Before, `substitute_all` recomputed it and could change the
  last ulp of `coords_are_cartesian=True` input.
- `Crystal._construct` and `Molecule._construct` call `Structure._construct` for the shared core
  state (species, frozen positions, lattice, caches) instead of repeating it.
- README, examples and calculator docstrings use the new API. Nothing in the library or examples
  emits the attachment warning.

### Tests
- New `tests/calculator/test_calculator_cache_085.py` (7 tests):
  - compute counts per structure;
  - the cache key includes site properties and PBC;
  - returned results are independent copies;
  - the new API is bit-identical to the deprecated one;
  - `get_stress(True)` still works;
  - the `inplace` FutureWarning;
  - `substitute` exactness.
- The two LJ integration tests now assert the attachment warning.

## 0.8.4 — 2026-11-12

This release makes serialization lossless (the item planned as "0.8.3"; 0.8.3 became the
test cleanup) and removes deep copies that made common structure operations scale as O(N²).

### Fixed — precision
- `Lattice.as_dict()` rounded lattice vectors to 8 decimals, so every JSON or `as_dict` round trip
  of a Lattice, Crystal or Trajectory moved the cell by up to 5e-9 Å. It now writes full float64.
  `__repr__` still rounds for display.
- `Crystal.as_dict()` also stores `cart_positions` when the Cartesian array is not bit-identical
  to `frac @ matrix` (for example `coords_are_cartesian=True` input). `from_dict()` then restores
  both arrays exactly.
  Payloads written by 0.8.3 and earlier still load. Older readers ignore the extra key.
- Result: `as_dict`/`from_dict`, MontyEncoder JSON, the io JSON format, `copy()`, `pickle` and
  `deepcopy` are all bit-exact for Lattice, Crystal, Molecule and Trajectory. This is checked with
  `np.array_equal` on 200 randomly generated crystals in `tests/contracts/test_serialization_exact.py`.
  Text formats (CIF, PDB, XYZ, POSCAR) keep their format-defined precision.

### Fixed — performance
The public `site_properties` property deep-copies every site's dict on each access. Several
code paths read it inside a loop.

| operation | N | 0.8.3 | 0.8.4 |
|---|---|---|---|
| `remove_atom` / `sort_atoms` | 2 000 atoms | 4.2 s / 4.3 s | 4 ms / 7 ms |
| `make_supercell` 2×2×2 | 200 → 1 600 atoms | 690 ms | 13 ms |
| `copy` / `set_pbc` / `substitute` / `wrap` | 4 000 atoms | 31 ms | 13 ms |

- `_filter_per_atom_data` and `_reorder_per_atom_data` (Crystal, Molecule) index the private tuple.
  Before, the full deep copy was repeated once per atom.
- `make_supercell` and the lattice `_map_site_properties` helper read the property once instead of
  once per atom (per image).
- `_construct_kwargs` and `set_pbc`/`substitute` pass the private tuple; `_construct` already
  deep-copies it once.

### Tests
- New `tests/contracts/test_serialization_exact.py` (17 tests). Against the 0.8.3 code, 11 of
  them fail. It includes a deterministic O(N²) regression check: `remove_atom`/`sort_atoms` may
  read `site_properties` only a bounded number of times.

## 0.8.3 — 2026-11-12

Test-suite cleanup. There are no library changes.

### Summary
| | 0.8.2 | 0.8.3 |
|---|---|---|
| collected tests | 2401 | 1537 (−36%) |
| test files / lines | 129 / 27.4k | 126 / 20.6k (−25%) |
| serial wall time (2-core sandbox) | 23.6 s | 18.7 s (−21%) |
| branch-coverage arcs | 26 194 | 26 194 (identical set) |
| killed mutants (4 956 first-order + 500 statement-deletion) | baseline | identical on a 300-mutant re-execution |

### How tests were selected for removal
1. **Protected and untouched:**
   - pymatgen-related tests: everything under `tests/calculator/`, `tests/electronic_structure/`,
     `tests/architecture/` and `tests/symmetry/test_vasp_services.py`, plus any test whose name or body
     mentions pymatgen or parity (328 tests, deferred by request);
   - `tests/contracts/` and every `*regression*` file;
   - tests about immutability or aliasing (mutation operators cannot model these bugs);
   - subprocess tests and tests that skip in the reference environment;
   - `tests/ai`, `tests/integration`, the README and packaging tests.
2. **Evidence per remaining test:**
   - its exact set of branch-coverage arcs;
   - the mutants it kills. This is the full population of 4 956 first-order mutants (comparison,
     arithmetic, boolean, constant and return-value operators) on every covered in-function line of
     `core`, `transformation`, `builders`, `analysis`, `io`, `symmetry` and `config`, plus 500
     statement-deletion mutants.
3. **Selection:** a greedy set cover kept the smallest set of candidate tests that covers every arc
   and kills every killed mutant. Parametrised tests were kept or removed as a whole, never thinned.
4. **Validation:**
   - Held-out statement-deletion mutants were evaluated *before* they were used for selection;
     only 3/397 kills were lost, and those were then added to the evidence.
   - After the files were edited, the arc set was re-measured and is identical.
   - 300 randomly chosen killed mutants were re-executed against both trees and gave identical kill sets.
   - Removed: 679 test functions/methods and 3 emptied files (`test_hash_robustness.py`,
     `test_sort_atoms.py`, `test_structure_comprehensive.py`), together with helpers and imports
     that became unused.

### Other changes
- `tests/test_readme_examples.py` runs all README blocks in **one** child interpreter (fresh globals,
  working directory and config singleton per block) instead of one interpreter per block: 5.0 s → 0.9 s.
- `tests/test_install_smoke.py` collapsed from 186 parametrised items to 3 tests.
- `-v` removed from the default `addopts` (2 400 lines of output per run).

### Findings left for later
- Mutation score of the full suite is 66.5% (core 58%). Many removed tests asserted only `is not None`
  or `isinstance`. Quantity was not buying detection power.
- Of the remaining runtime, about 40% is the pymatgen-related subprocess/parity tests (deferred).

## 0.8.2 — 2026-11-11

This release fixes packaging and the code ported from pymatgen. Every public
subpackage now imports on a minimal install, the source distribution's test suite
passes, and the VASP/LAMMPS paths that broke at runtime have been fixed.

### Fixed — silently wrong results
- `LammpsCalculator` wrote every atom as type 1 with mass 1.0. Multi-element systems were
  simulated as a single component. It now writes one atom type per element (ordered as
  `structure.symbol_set`) with real masses.
- `LammpsCalculator` wrote only |a|, |b|, |c| plus the raw Cartesian positions, which is wrong for
  any non-orthogonal cell. It now writes a restricted-triclinic box (with `xy xz yz` tilt factors)
  and maps positions through fractional coordinates. Boundaries follow `pbc` (`p` or `s`).
  Coordinates are written to 12 decimals.
- `lattice_2_lmpbox`: `lattice.is_orthogonal` was used as a property, but it is a method in MatSimPy
  (always truthy), so the tilt factors were always dropped and `LammpsData` lost triclinic cells.
- VASP `Poscar` now takes `selective_dynamics`, `velocities` and `predictor_corrector` from the
  structure's site properties when they are not passed explicitly (pymatgen semantics).
  In 0.8.1, input sets and `VaspCalculator` silently dropped a slab's selective dynamics.
- `Poscar(..., selective_dynamics=...)` no longer discards the structure's other site properties
  (e.g. `magmom`).
- `Poscar(..., sort_structure=True)` keeps the selective-dynamics and velocity arrays in the
  sorted atom order.
- `ConfigManager` wrote `MATSIMPY_*` environment overrides into `~/.matsimpy/config.yaml` on
  auto-create, `set(save=True)` and `reset()`, so a temporary override became permanent.
  Overrides are now applied in memory only. `reset()` keeps them in effect.

### Fixed — crashes in the code ported from pymatgen
- `Poscar.get_str()` raised `ValueError: truth value of an array is ambiguous` whenever selective
  dynamics, velocities or predictor-corrector data were present.
- `Poscar.set_temperature()` (immutable `site_properties`) and `_get_recommended_lreal`
  (`num_sites`, hit by `auto_lreal=True`).
- `LammpsData.from_structure`, `LammpsData.structure`, `disassemble` and `Topology(...)` used
  pymatgen-only APIs (`cart_coords`, `operate_multi`, dict-of-lists site properties,
  `specie.symbol`, iteration over `Element`). They are ported, and the Crystal → LammpsData →
  Crystal round trip is tested.
- `matsimpy.calculator.lammps.sets` / `.generators` raised `NameError` on import. They now raise
  a clear `ImportError` when pymatgen is not installed.
- `Topology.from_bonding`, `Polymer` and `PackmolRunner` are not ported yet. They now raise
  `NotImplementedError` with a workaround instead of failing half-way with `AttributeError`.
- `Wavecar` (spin-orbit) used `ndarray.shape = ...`, which is deprecated since NumPy 2.5.

### Packaging
- New core dependency `spglib`: builders and VASP k-point generation need it.
- `tqdm` is optional (progress bar only).
- `pandas` and `ruamel.yaml` move to a new `lammps` extra. The LAMMPS file-format classes are
  exported lazily, so `LammpsCalculator` works without them.
- `requires-python >= 3.10`. The ported code uses `isinstance(x, A | B)` and `zip(strict=)`
  (39 sites), so 3.9 never worked.
- License uses an SPDX expression (`license = "MIT"`, `license-files`); classifiers removed.
  Builds need `setuptools >= 77`. The old form stops building after 2027-02-18.
- `MANIFEST.in` now ships the test fixtures, `docs/` and the `examples/` READMEs.

### Tests
- The suite no longer touches the developer's `~/.matsimpy`: `HOME` is redirected and
  `MATSIMPY_*` variables are cleared in `conftest.py`.
- Repository-only assets that are missing (whole directory absent) are reported as skips.
  A missing file inside a directory that exists is still a failure.
- Tests that depended on the machine's environment (RDKit, a pinned pymatgen version,
  `DEEPSEEK_API_KEY`) now skip when it is unavailable. The README's live-LLM example is marked
  `python notest`.
- New tests: `tests/test_install_smoke.py` (every module imports, core subpackages need no extras)
  and `tests/calculator/test_regressions_082.py`, plus a config env-persistence regression test.
- `examples/config_basic.py` no longer overwrites the user's real config file.
- `tests/ai/test_skill_loader.py` wrote temporary `zztmp_*.py` skills into the installed
  `matsimpy/ai/skills/` package. Under pytest-xdist this intermittently failed
  `tests/contracts/test_agent_skill_contract.py`, and an interrupted run left the files in the source tree.
  The temporary skills now go to a per-test directory.

### Added
- `SymmOp.operate_multi(points)`. The `translation` argument of
  `SymmOp.from_rotation_and_translation` now defaults to zero.
- `matsimpy.calculator.utils.site_property_column(structure, key)`: adapter for ported code
  that expected pymatgen's dict-of-lists site properties.

## 0.8.1 — 2026-11-11

Patch release: closes every mutation path that could desynchronise the
"immutable" core objects from their derived state. No public read API changed.

### Fixed — mutability
- `Lattice.lattice_vectors` is a read-only property backed by a frozen private array.
  0.8.0 allowed `lat.lattice_vectors = ...` (no validation) and
  `lat.lattice_vectors.flags.writeable = True`, both leaving `inv_matrix` stale.
- `Lattice.inv_matrix` returns a read-only view; 0.8.0 returned the cache owner, which could be re-opened for writing.
- `Structure.lattice` and `Crystal.pbc` are read-only properties. Reassigning them in 0.8.0
  left `cart_positions`, the KD-tree neighbour cache and the sites out of date.
- `site_properties = ...` on `Crystal`/`Molecule` is **deprecated** (DeprecationWarning; removal in 0.9.0).
  It no longer leaves `sites` / `structure[i]` / iteration stale. Use the new `with_site_properties()`.
- Sites are built on demand from the backing arrays, so there is no `_sites` cache to go stale.
  `structure[i]` is O(1), and `Crystal(...)` no longer builds N site objects eagerly.
- `copy()` is bit-exact. 0.8.0 round-tripped through `as_dict()`, which rounded the lattice to 1e-8 and
  recomputed Cartesian coordinates.
- `pickle` and `copy.deepcopy` re-freeze every ndarray, and states pickled by 0.8.0 are migrated.
- `Trajectory` is immutable. `__iter__` yields copies. `frame_properties` returns deep copies.
  `base_positions` is read-only, and attribute assignment after `__init__` raises.
- `CrystalSite.lattice` setter keeps the inherited Cartesian `_position` in sync.
- The VASP input sets (`validate_magmom`) no longer edit the caller's structure in place. In 0.8.0 the
  user's Crystal was mutated whenever `sort_structure=False`.
- `get_valid_magmom_struct`: the int→float MAGMOM coercion was written to a detached snapshot and lost. It now applies.
- The calculator staleness fingerprint is exact (no 7-d.p. rounding) and includes PBC and site properties (MAGMOM).
  A shared calculator no longer returns stale results for a different magnetic configuration.

### Fixed — other
- `remove_atom()` / `sort_atoms()` raised `TypeError: multiple values for keyword argument
  'site_properties'` on any structure that carried site properties.
- Packaging: the VASP/LAMMPS runtime data files (`incar_parameters.json`, `*Set.yaml`, templates) are now
  in `package-data`. `orjson` is a declared dependency. `MANIFEST.in` excludes bytecode.
- Mutable default arguments in `build_linear`, `build_bent` and `PotcarSingle.compare_potcar_stats`.

### Performance (N = 4000 atoms with site properties)
| operation | 0.8.0 | 0.8.1 |
|---|---|---|
| `Crystal(...)` | 77 ms | 8 ms |
| `copy()` | 85 ms | 15 ms |
| `remove_atom(1000 indices)` | 40 ms | 2 ms |
| `_structural_hash()` | 4.1 ms | 1.1 ms |

### Added
- `Structure.with_site_properties(site_properties)` returns a new structure.
