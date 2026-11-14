# Changelog

## Unreleased

A review of every builder. Several produced wrong structures; those are fixed, and the
nanotube and twisted-layer builders are rewritten on new, general algorithms.
A second review covered `core`, `transformation` and `io`; its fixes are listed in the
same sections below.

### Breaking changes
- Builders no longer accept and silently ignore unknown keyword arguments (`**kwargs`);
  a misspelled option now raises `TypeError`. `random_crystal` still passes extra
  keywords on to PyXtal.
- `generate_slab(bulk, miller_index, min_slab_size=None, min_vacuum_size=15.0,
  layers=None, center_slab=True, primitive=True, symprec=1e-3)`: give exactly one of
  `min_slab_size` and `layers`. Slabs now use the smallest surface cell, so they
  usually have fewer atoms than before (see Fixed). `generate_symmetric_slab` takes
  the same arguments.
- Twisted builders: `build_twisted_bilayer(layer, twist_angle, layer_spacing=3.35,
  top_layer=None, vacuum=15.0, max_strain=1e-4, angle_tolerance=0.01, max_atoms=20000)`
  and `build_twisted_multilayer(layer, num_layers, twist_angles, ...)` build commensurate
  supercells and raise `ValueError` (listing nearby commensurate angles) when no
  supercell fits; `center` and the c-length default spacing are gone.
  `build_magic_angle_twisted(layer, n, m, layer_spacing=3.35, vacuum=15.0,
  max_atoms=50000)` uses the exact commensurate angle (see Fixed).
- `build_nanotube(base_2d, chirality, length=None, periodic=True, vacuum=10.0,
  max_atoms=20000)` and `build_carbon_nanotube(n, m, bond_length=1.42, length=None,
  periodic=True, vacuum=10.0)`: `length` is a minimum length in Angstrom (default one
  period) and the tube axis is at the centre of the cell; `center` is gone.
- `from_prototype(prototype, species, lattice_constant, c=None)`: a formula must match
  the prototype's composition (`'MgO2'` on rocksalt raises instead of giving MgO);
  hexagonal prototypes take `a`, `[a, c]` or `c=`, the others exactly one constant.
- `from_space_group` and `from_crystal_system` take `symprec`, `angle_tolerance` and
  `validate_sg` as named arguments; `from_crystal_system` requires exactly the lattice
  parameters of the crystal system (no invented c/a) and a space group of that system.
  An unknown crystal system raises `ValueError` instead of becoming cubic, also in
  `list_space_groups_by_system`.
- `generate_intermetallic` checks `composition` against the structure type and takes
  `c` for L1_0 as an argument. L1_0 returns the 4-atom face-centred tetragonal cell.
- Heusler builders return the conventional cubic cell: 16 atoms (12 for half-Heusler).
  `build_inverse_heusler_quaternary` is replaced by `build_quaternary_heusler(X, X2,
  Y, Z, lattice_constant)`.
- `create_frenkel` requires `interstitial_position`. `create_schottky(structure,
  indices=None, seed=None)` removes one formula unit by default; `num_vacancies` is
  gone, and explicit indices must be whole formula units. `create_antisite` rejects
  two atoms of the same species. `create_interstitial` and `create_frenkel` reject
  positions closer than 0.5 A to an atom.

- `SymmOp.from_origin_axis_angle(origin, axis, angle, angle_in_radians=False)` takes
  degrees by default (as in pymatgen) and rotates right-handed; it used radians and
  rotated the wrong way.
- Lattice deformations use the row-vector convention: `apply_strain`,
  `apply_deformation`, `transform_lattice` and `rotate_lattice` map lattice vectors by
  `A @ F.T` (they used `F @ A`). `deform_positions=False` / `rotate_atoms=False` /
  `transform_positions=False` now keep the atoms' Cartesian positions (they kept the
  fractional ones, which made the flag a no-op); `transform_lattice` moves atoms with
  the cell by default. `rotate_lattice` requires a proper rotation. `apply_strain`
  takes a 3x3 tensor or three normal strains, and rejects other shapes and
  non-positive `det(I + strain)`.
- `Crystal.wrap()` and `make_supercell` no longer wrap non-periodic axes;
  `make_supercell` raises when asked to repeat or mix a non-periodic axis.
- `merge_molecules(..., bond_length=None)`: with the default the bond atoms are
  superposed as before, but a result with atoms closer than 0.5 A raises; pass
  `bond_length` to place the second molecule at a bond distance.
- `substitute_all` raises when the species is absent (it returned a copy);
  `substitute(c, i, [a, b])` raises instead of using the first species;
  `standardize_cell` raises when spglib is missing or fails, for non-periodic
  crystals and when site properties cannot be carried over (it returned a copy or
  dropped them); `optimize_lattice` rejects both targets and `preserve_angles=False`.
- `ParameterSweep(mode='zip')` requires parameter lists of equal length (it padded with
  the last value). `TransformationPipeline.save` rejects lambdas, closures and partials.
- Atom indices are validated: bools and floats raise `TypeError`, duplicate indices in
  `move_atoms`, `swap_atoms`, `merge_atoms`, `perturb_positions` and `substitute` raise
  `ValueError`. Bools are rejected as coordinates, lattice values, cutoffs and scale
  factors.
- `Element` objects are immutable and compare equal by symbol; `Lattice` attributes and
  `Composition.formula` can no longer be assigned; `Composition['h']` (not an element)
  raises `KeyError`.
- `Trajectory` requires every frame to have the same atoms and validates `time_step`,
  `base_positions` and the other scalars.
- io: `read_XYZ` raises on extended XYZ with a cell (read it with `format='ase'`);
  `read_CIF` raises for non-P1 space groups given only by name, CIF2/magnetic symmetry
  operations, several structure blocks and missing cell angles; `read_PDB` raises for
  several MODELs; LaTeX tables have no "Space Group"/"Point Group" columns (they were
  always "N/A") and unknown columns raise; `from_json` rejects pymatgen JSON with a
  clear message; titles with newlines raise in the POSCAR, XYZ, ASE and MOL writers;
  `write_MOL` raises above 999 atoms.

### Added
- `build_nanotube` rolls any 2D sheet whose chiral direction has a perpendicular lattice
  vector: hexagonal sheets in a 60 or 120 degree basis, square and rectangular sheets
  for every chirality, oblique sheets for commensurate directions. Atoms keep their
  height above the sheet's mid-plane, so MoS2 becomes three coaxial shells.
  `nanotube_translation` returns the translation vector.
- Twisted layers: commensurate (coincidence-lattice) supercells for any layers with a
  and b in the xy-plane, heterobilayers via `top_layer` with strain up to `max_strain`,
  and `commensurate_twist_angles(layer, max_atoms=2000, max_angle=60)`, which lists the
  exact angles and supercell sizes. Results record the realized angles, strain and
  supercell matrices in `metadata`, and a `layer` site property.
- `generate_symmetric_slab` really returns a slab whose top and bottom surfaces are
  equivalent by symmetry, or raises for polar surfaces.
- `build_quaternary_heusler` (LiMgPdSn type). `build_trigonal_planar` and
  `generate_symmetric_slab` are registered builders and AI tools.
- Space group symbols are looked up in spglib's database (`'P2_1/c'`, `'P21/c'` and
  full symbols work).
- `Lattice.get_min_image_vectors(frac_vectors, pbc=(True, True, True), cutoff=None)`
  returns the shortest Cartesian image of fractional displacements along the periodic
  axes. It is exact in any cell, however skewed: it LLL-reduces the periodic vectors
  and tries every translation that could be shorter than the rounded image.

### Fixed
- `BondAnalyzer.get_dihedral_angles()` no longer raises `ValueError` (it unpacked the
  `(i, j, distance)` bond triples as pairs). Angles are now signed (IUPAC, in
  (-180, 180]), so gauche +60 and -60 differ; anti butane gives 180. Degenerate
  three-membered rings (`l == i`) are skipped.
- `BondAnalyzer.get_bond_order()` no longer raises `AttributeError`: it read a
  non-existent `Element.covalent_radius`. It now uses `Element.atomic_radius` and
  raises `ValueError` when an element has none. The step heuristic is unchanged and
  documented; it gives 1.0 for C=O at 1.21 A, the same as a C-C single bond.
- Periodic coordination numbers counted each neighbouring atom index once, so periodic
  images collapsed and an atom's own images were dropped: a primitive rocksalt cell
  gave 1 instead of 6, primitive bcc and fcc gave 0 instead of 8 and 12.
  `get_coordination_numbers`, `get_degree_distribution`, `get_graph_statistics` and
  `CrystalGraph.coordination_numbers` / `.degree_distribution` now count every
  periodic image within the cutoff (inclusive); `BondAnalyzer.get_coordination_numbers`
  does the same for periodic crystals (exclusive cutoff, as `find_bonds`). Molecules and
  `use_pbc=False` are unchanged. `adjacency_matrix` stays binary and its docstring now
  says it carries no multiplicity.
- `StructureMatcher.fit` has a docstring stating that it needs equal site counts and
  does not handle supercells or uniform rescaling.
- `generate_slab` built surface cells 2 to 26 times larger than the primitive surface
  cell, left-handed cells for some planes, did not reduce the Miller index ((2, 2, 2)
  gave a different slab from (1, 1, 1)) and did not put the normal along z. It now uses
  the bulk's full translation lattice (so a conventional cell gives the primitive
  surface cell, as in pymatgen), puts a along x and the normal along z, keeps site
  properties and cuts in the widest gap between atomic planes.
- `generate_symmetric_slab` returned an ordinary slab.
- `add_adsorbate` measured heights along c and centred molecules in xy; it now uses
  the surface normal a x b.
- `build_nanotube` dropped atoms of thick sheets (MoS2 (10, 10) gave Mo20S20 with every
  atom on one radius) and found a wrong tube axis in a 120-degree basis.
- `build_twisted_bilayer` rotated the top layer inside the unrotated cell, so the
  bilayer was not periodic; the default spacing was the input cell's c length;
  `build_magic_angle_twisted` used 360/(n^2+nm+m^2) instead of the commensurate angle
  (51.4 instead of 21.79 degrees for (1, 2)); multilayers mixed fractional and
  Cartesian coordinates.
- Heusler builders gave wrong structures: full Heusler had the inverse ordering
  (F-43m), half-Heusler three atoms in a cubic cell (R3m), inverse Heusler a Cmmm
  structure and the quaternary builder I-4m2. They now give Fm-3m and F-43m.
- `generate_intermetallic('L1_0')` put the 2-atom primitive positions in a cell with the
  conventional a, so Fe-Pt was 3.31 instead of 2.72 A; `composition` was ignored.
- `build_bent` chains of four or more atoms always turned the same way and folded onto
  themselves; they are now all-trans zigzags. NaN bond lengths and angles are rejected,
  and `build_tetrahedral` and `build_trigonal_planar` validate the bond length.
- `create_schottky` removed random, unseeded atoms (often two of one species);
  `create_frenkel` displaced the atom by a random, unseeded amount by default;
  `create_interstitial` wrapped positions along non-periodic axes;
  `create_substitution` rejected numpy integer indices.
- `generate_random_alloy` rejected concentrations summing to 1 within rounding and
  accepted NaN.
- `from_space_group` rejected numpy integers and accepted `True` as space group 1.
- `Lattice.cubic`, `tetragonal`, `orthorhombic`, `hexagonal` and `from_parameters`
  accepted negative and non-finite lengths (`Lattice.cubic(-3)` had determinant -27).
- `random_crystal` no longer falls back to reading PyXtal internals, and reports
  mismatched `species`/`num_ions`.
- core: neighbour lists missed neighbours of atoms stored outside the cell and the
  single-atom query excluded the cutoff distance; minimum-image distances in skewed
  cells (used by `add_atom`) were not minimal; `Composition` gave wrong
  `reduced_formula` with `sort_by`, wrong HTML/LaTeX for fractional amounts, and
  failed to add fractional compositions; `Fe()` and bool amounts were accepted;
  numpy site properties did not survive JSON; `Crystal.from_dict` accepted
  inconsistent Cartesian positions; `Molecule.to_crystal` dropped site properties and
  accepted negative vacuum; `Molecule.get_all_neighbor_lists` excluded the cutoff and
  accepted NaN; `Molecule.translate` broadcast short vectors; `c[True]` returned a
  site with a wrong shape; `pbc` rejected numpy bool arrays.
- transformation: `align_molecules` applied the transpose of the fitted rotation;
  `merge_atoms` ignored periodic images for the midpoint; `translate_to_origin` used an
  unweighted centre for crystals; `fragment_molecule` accepted a "bond" between
  non-bonded atoms; `BatchProcessor.process_stream` re-read its input after a parallel
  failure; custom `ParameterSweep` combinations were applied in dict order; registry
  schemas lacked parameters, rejected numpy arrays/integers and lists for
  `substitute`, and had wrong `preserves_*` flags; "perturb" amplitudes are standard
  deviations (the docs said maximum).
- io POSCAR: Cartesian coordinates ignored the scale factor; species/count lines over
  several lines and POTCAR-style names (`Fe_pv`) failed; selective dynamics and
  velocities (including NPT CONTCARs) are read and written as site properties;
  `write_POSCAR` reordered atoms by species.
- io CIF: a real tokenizer (comments, CIF quoting, `;` text fields) reads files that
  failed before; type symbols with charges (`Fe3+`) work; malformed loops of unused
  data are skipped.
- io PDB: `write_PDB` wrote coordinates in the original frame instead of the CRYST1
  orientation; element guessing turned `FE`/`CL` into F/C; malformed CRYST1 records
  were ignored.
- io other: `read_ASE` failed on a blank comment line and ignored `pbc`; `write_ASE`
  did not write `pbc`; `to_ase`/`from_ase` and `to_pymatgen`/`from_pymatgen` dropped
  site properties, magnetic moments, charges, pbc and oxidation states (disordered
  pymatgen structures raise `ValueError`); `to_json` turned numpy values into strings;
  `read_XSF` rejected atomic numbers; `read_MOL` misread counts lines with 100 or more
  bonds; strict `read_XYZ_multiframe` skipped garbage lines;
  `get_integrated_diff` integrated the total charge for non-spin data; compressed
  files (`.gz`, `.bz2`, `.xz`) are read by `matsimpy.io.read`.
- Minimum-image distances were wrong in skewed cells. Rounding fractional coordinates
  plus a +/-1 cell search misses the closest image when a lattice vector is much longer
  than the plane spacing (in `[[4, 0, 0], [16, 0.4, 0], [0, 0, 4]]` the image of an atom
  at fractional (0, 0.5, 0) is 0.2 Angstrom away, two cells over). `add_atom`,
  `create_interstitial` and `create_frenkel` accepted atoms on top of existing ones;
  `merge_atoms` and `periodic_distance` used a wrong image. All now use
  `Lattice.get_min_image_vectors`.
- `analysis.pair_distance` raised `AttributeError` for every `Crystal`.
- Builder registry: the `add_adsorbate` schema accepted only an element symbol, though
  the function also takes a `Molecule` or `Crystal`; the `generate_slab` and
  `generate_symmetric_slab` schemas now state that exactly one of `layers` and
  `min_slab_size` is required (registry schemas support an object-level `oneOf`).

## 0.11.0 — 2026-11-12

The AI module (`matsimpy.ai`) is rewritten around three extension points: tools derived
from Python functions, Agent Skills, and MCP. The rest of MatSimPy is unchanged apart
from the fixes below. The guide is [docs/ai.md](docs/ai.md).

### Breaking changes
- Removed modules: `matsimpy.ai.runtime`, `executor`, `skill`, `skill_loader`, `skills`
  (package), `evolution`, `session_store`, `catalog`, `agent_skills`, `session`,
  `conversation` and `providers`. Their classes (`AgentRuntime`, `AgentSession`,
  `SkillManager`, `FunctionDef`, `FunctionExecutor`, `get_active_executor`,
  `SessionStore`, `SkillVersion`, `EvolutionManager`, `EvolutionCandidate`,
  `TaskResult` and others) have no direct replacement. Use `Agent`, `ToolCatalog`,
  `ToolExecutor` and `SkillLibrary` instead.
- `ChatMessage`, `ToolCall`, `ChatResponse` and `ChatProvider` moved to
  `matsimpy.ai.provider`.
- `AgentResult` is `(response, status, tool_calls, usage)`. `tool_calls` holds
  `ToolRecord(name, arguments, ok, result)` objects. `artifacts`, `trace_id` and
  `evolution_candidates` are gone.
- Sessions are JSON files in `<workspace>/.matsimpy/sessions/` instead of a SQLite
  database. Sessions saved by 0.10.0 cannot be resumed.
- Skills use the Agent Skills format (folders with `SKILL.md`). Legacy `*.skill.md`
  files and the version/rollback lifecycle are gone. Proposed Skills are drafts that you
  approve or reject by name.
- REPL commands: `/load-skill` is `/skill`; `/trace`, `/evolve`, `/rollback`,
  `/approve-skill` and `/reject-skill` are removed; `/approve` and `/reject` take a draft
  name. The `matsimpy-ai -v` flag is replaced by `-q` (tool calls are shown by default).
- Tool names follow the functions: `read_structure`/`write_structure` (from
  `io.read`/`io.write`) and the builder and transformation function names. The result
  of `write_structure` reports `filename` instead of `saved_to`.
- `matsimpy.builders.bulk.from_space_group` now generates the structure from the
  space group's operations (see Fixed). Code that passed a complete cell and relied on
  the old behaviour gets more atoms, or an error if the result has a different group.

### Added
- `matsimpy.utils.tooling.tool`: a decorator that marks a function as an AI tool. The
  name, JSON schema and description are derived from the signature and docstring
  (Google, NumPy or Sphinx). About 80 builder, transformation, I/O, symmetry and graph
  analysis functions are marked.
- `matsimpy.ai.tools`: `Tool`, `ToolCatalog` (discovery of marked functions, search,
  reload), `ToolExecutor` (argument validation, structure references such as
  `structure:3`, workspace-confined paths) and `ToolContext`.
- `matsimpy.ai.skills.SkillLibrary`: Agent Skills with progressive loading, a
  `tools.py` per Skill, packaged/user/workspace roots, install from a folder or zip,
  remove, validate, and drafts that need approval. Packaged Skill: `vasp-inputs`. Its
  `kpoint_mesh` tool matches pymatgen's `Kpoints.automatic_density`.
- `matsimpy.ai.mcp`: an MCP client (stdio and Streamable HTTP) configured by
  `mcp.json`, and an MCP server. `matsimpy-ai mcp serve` serves every tool over stdio.
  Interoperability with the official `mcp` SDK is tested.
- `Agent` meta-tools (`search_tools`, `load_tools`, `activate_skill`,
  `read_skill_resource`, `propose_skill`). Only loaded tools' schemas are sent to the
  model.
- `matsimpy-ai` renders answers as Markdown on a terminal, in the REPL and with `-c`
  (rich), and prints the Markdown source when piped or with `--raw`.
- `matsimpy-ai` subcommands `tools list|show`, `skills list|install|remove|validate|approve|reject`
  and `mcp serve|list`; `-t` adds a module of `@tool` functions.
- `examples/ai/extending.py`: a custom tool, Skill and MCP server, offline.
  `examples/llm` gains scenarios for a Skill (16) and an MCP server (17), and a README
  per scenario.
- `docs/ai.md`.

### Fixed
- `from_space_group` read the symmetry off the input positions instead of applying
  the requested group, so an asymmetric unit was rejected. Its own docstring example
  (rocksalt NaCl in Fm-3m) raised "space group 221, not requested 225". It now applies
  the operations of the group's standard setting from spglib's database (origin choice
  2 where there are two; hexagonal axes for rhombohedral groups) and checks the result.
- `examples/builders_bulk.py` (hcp arguments, unknown `fluorite` prototype,
  `from_space_group` call) and `examples/transformation_composite.py` (lambdas cannot
  be sent to worker processes; missing `__main__` guard for the `spawn` start method)
  printed errors and warnings. `tests/test_examples.py` now runs every example and fails
  on printed errors or warnings.

### Removed
- `MIGRATION_0.10.md`. Breaking changes are listed in this changelog.
- `scripts/profile_runtime.py` and `scripts/profile_runtime_live.py`, which profiled
  the removed runtime.

## 0.10.0 — 2026-11-12

New features and bug fixes; no API is removed.

### Added
- `HighSymmKpath` supports two-dimensional crystals (`pbc` with exactly one `False`
  axis, e.g. a monolayer in a slab cell). The layer is classified as one of the five 2D
  Bravais lattices from its in-plane symmetry, not just its cell shape: `bravais` is
  `mp`, `op`, `oc`, `tp` or `hp`, and `kpath["variant"]` is ASE's name (`OBL`, `RECT`,
  `CRECT`, `SQR`, `HEX2D`). When the atoms break the cell's symmetry, the path of the
  lower symmetry is used. The k-points are fractional coordinates of the input cell's
  reciprocal lattice, with zero along the vacuum axis.
- Crystal prototype identifiers in the style of AFLOW labels:
  `matsimpy.symmetry.get_prototype(crystal)` returns e.g. `AB_cF8_225_a_b` for rocksalt
  (anonymized formula, Pearson symbol, space-group number, Wyckoff letters). The
  identifier is the same for every description of a crystal: any cell, origin, axis
  order, atom order or supercell. It is also the same for every crystal of that
  structure type, independent of the elements.
  - Wyckoff letters are canonical. As in AFLOW, every axis permutation and origin
    shift that keeps the space-group setting is tried, and the description with the
    smallest letter sum (a=1, b=2, ...) wins; ties go to the lexicographically
    smallest letter sequence. YBa2Cu3O7 gives AFLOW's `k_cj_aijl_f` letters,
    diamond is `a` and zincblende `a_c` from any cell.
  - The Pearson symbol counts the conventional cell (rocksalt `cF8` also from a
    primitive input; rhombohedral lattices count the rhombohedral cell, corundum `hR10`).
  - The symmetry tolerance is chosen per crystal by default (`symprec=None`): it starts
    at 1/100 of the shortest interatomic distance and is halved until the symmetry is
    consistent with the crystal. A real MnO POSCAR with 6-decimal coordinates is
    `Fm-3m`, where a fixed 1e-5 gives `I4mm`. An explicit `symprec` is used as given.
    A value above a quarter of the shortest distance is rejected, because spglib 2.8
    crashes the interpreter from about 0.45 of it.
  - Unlike AFLOW, elements are named A, B, ... by count, not alphabetically, so the
    identifier does not change when elements are substituted.

  `get_prototype_info` returns the parts as a frozen `PrototypeInfo`, including the
  tolerance used. `PrototypeDatabase` is a read-only map from identifier to structure
  names, with JSON load/save; `merge` and `with_structures` return a new database.
  `matsimpy.builders.bulk` adds `build_prototype_database(files)`,
  `structures_from_prototype(database, prototype, ...)` (new crystals by element
  substitution) and `suggest_element_substitutions`. This replaces branch1's
  `CrystalPrototype`. Its identifiers (`AB_cF2_Fm-3m_a_b`, space-group symbol,
  primitive-cell count, setting-dependent letters, fixed 1e-5 tolerance) are not
  compatible with the new ones.

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
- Builders: the `wurtzite` prototype had one formula unit, which made it a P6mm
  structure, not wurtzite. It now has two (P6_3mc, both species on 2b).

### Known issues
- MatSimPy ships no POTCAR reference data, because POTCARs are copyrighted. The packaged
  files (`vasp_potcar_stats.json` and both hash files) are empty (`{}`). POTCARs are
  read but cannot be checked: every POTCAR gives `UnknownPotcarWarning`.
- There are two POSCAR readers: `matsimpy.io` (`matsimpy/io/vasp.py`) and
  `calculator.vasp.inputs.Poscar`. Only the second reads VASP 4 files, where species
  names follow the coordinates or come from a POTCAR.

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
- Removed `tests/POSCAR-cart.vasp` and `tests/POSCAR-frac.vasp`. No test used them.
- Removed tests that repeated other tests (INCAR parsing and round trip, KPOINTS and POSCAR
  file reads), merged the 2D k-path checks, and parse each volumetric fixture once.
  `test_core_integrity_091.py` is now `test_core_integrity.py`.

### Documentation
- Removed `MIGRATION_0.9.md` (the 0.8.x → 0.9.0 guide).
- README: symmetry section with 2D k-path and prototype examples (run by the test suite),
  corrected prototype list, test commands and documentation links (it pointed to
  `AIdocs/` and `docs/user_guide/`, which do not exist).
- `CLAUDE.md` describes the layout, layering, test command and test-data rules for
  contributors and coding agents.

## 0.9.0 — 2026-11-12

A deliberately **incompatible** refactor of 0.8.x. Readers for files written by 0.8.x are kept.

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
