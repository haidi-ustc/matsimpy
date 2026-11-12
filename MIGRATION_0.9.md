# Migrating from 0.8.x to 0.9.0

0.9.0 is a deliberately incompatible release. Every removed API is listed here
together with its replacement.

## P1 — core no longer depends on higher layers

| removed | use instead |
|---|---|
| `Structure.from_file(path)` / `Crystal.from_file` / `Molecule.from_file` | `matsimpy.io.read(path)` (check the type with `isinstance` if needed) |
| `structure.to_file(path)` | `matsimpy.io.write(structure, path)` |
| `crystal.to_ase()` / `Crystal.from_ase(atoms)` (and the `Molecule` versions) | `matsimpy.io.to_ase(structure)` / `matsimpy.io.from_ase(atoms)` |
| `crystal.to_pymatgen()` / `Crystal.from_pymatgen(obj)` (and the `Molecule` versions) | `matsimpy.io.to_pymatgen(structure)` / `matsimpy.io.from_pymatgen(obj)` |
| `to_code()` / `from_code()` | none. These depended on a `matsimpy.code` module that does not exist and always raised `ModuleNotFoundError` |
| `crystal.get_symmetry_info(...)` | `matsimpy.symmetry.get_symmetry_info(crystal, ...)` |
| `crystal.get_conventional_cell(...)` | `matsimpy.symmetry.get_conventional_cell(crystal, ...)` |
| `crystal.make_supercell(m)` | `matsimpy.transformation.make_supercell(crystal, m)` |
| `crystal.perturb(a, indices=..., seed=...)` | `matsimpy.transformation.perturb_positions(structure, a, indices=..., seed=...)`; `perturb_positions` accepts an `AtomSelection` |
| `crystal.perturb(a, perturb_lattice=True, ...)` | `matsimpy.transformation.perturb_lattice(crystal, a, seed=...)` |
| `Crystal.random_crystal(...)` | `matsimpy.builders.bulk.random_crystal(...)` |
| `matsimpy.visualization` (an empty package) | none |

The layering rule is enforced by `tests/architecture/test_layering.py`:

```
utils/constants/exceptions → core → analysis, symmetry, io, electronic_structure, config
 → transformation, builders, storage → calculator → ai
```

## P2 — core data model

| removed / changed | use instead |
|---|---|
| `lattice.lattice_vectors` | `lattice.matrix` (the only accessor; the `as_dict` key is unchanged) |
| `Trajectory(frames, frame_properties=[...])`, `traj.frame_properties` | per-frame data goes in each frame's metadata: `frame.with_metadata(energy=...)`; read with `traj[i].metadata`. Files written by ≤0.8.7 are still read. |
| `site.specie = ...`, `site.position = ...`, `site.properties = ...`, `crystal_site.lattice = ...` | Sites are frozen snapshots. Change the structure instead (`substitute`, `with_site_properties`, transformations). `site.properties` returns a copy. |
| `crystal_site.position` was fractional *or* Cartesian depending on how the site was built | `position` is always Cartesian. Use `frac_position` / `cart_position`. |
| `Site.coords_are_cartesian`; `CrystalSite.as_dict()["coords_are_cartesian"]` reflecting the input | `CrystalSite.as_dict()` always writes fractional coordinates. Old dicts are still read. |
| `Molecule.add_atom` added `site_properties` to a property-less molecule silently | Molecule and Crystal share one `add_atom` and warn the same way. Duplicate and too-close checks are the same for both, using the minimum image along periodic axes only. |
| private `_positions`, `_frac_positions`, `_cart_positions`, `_filter_per_atom_data`, `_reorder_per_atom_data` | `_coords` holds native coordinates (fractional for Crystal, Cartesian for Molecule). Crystal also keeps the exact `_cart`. Subclasses override one hook, `_take_per_atom`. |

Behaviour notes:

* `remove_atom`, `sort_atoms` and `add_atom(..., coords_are_cartesian=True)` keep the crystal's Cartesian rows bit-exact; before, they were recomputed as `frac @ matrix`.
* `crystal.sites[i].cart_position` now equals `crystal.cart_positions[i]` exactly. Building the sites is about 4.5× faster.
* `str(structure)` is one implementation in `Structure`; the output format is unchanged.

## P3 — stateless calculators

A calculator holds parameters and a result cache only. `compute(structure) -> Results` is the core API.

| removed / changed | use instead |
|---|---|
| `calc.calculate(s)` followed by `calc.get_potential_energy()` (no argument) | `calc.compute(s).energy` or `calc.get_potential_energy(s)`. The getters now **require** the structure. |
| `calc.results`, `calc.structure`, `calc.get_result(key)`, `calc._calculation_performed` | `r = calc.compute(s)`: `r.energy`, `r.forces`, `r.stress`, and `r.extra[key]` for anything else |
| `calc.get_results(s)` | `calc.compute(s).as_dict()` |
| `calc.update_parameters(...)` (same as `set_parameters`) | `calc.set_parameters(...)` |
| `get_stress(s, True)` | `get_stress(s, voigt=True)` (`voigt` is keyword-only) |
| `Calculator(run=False)` then `calculate(s)` and later `read_results()` | `calc.write_input(s, directory)` → run the program yourself → `r = calc.read_results(directory)` (returns `Results`) |
| custom calculators override `_compute()` and fill `self.results` | override `_calculate(self, structure)` and return `Results` or a raw `{"energy": ..., "forces": ...}` dict |
| external-code calculators override `write_input` / `_execute` / `_parse_output` | subclass `FileIOCalculator`: `write_input(structure, directory=None) -> Path`, `_execute(directory)`, `read_results(directory=None) -> Results` |
| `vasp.incar_params`, `.kpoints_grid`, `gaussian.route`, `lammps.pair_style`, and similar | `calc.parameters["incar"]`, `["kpoints"]`, `["route"]`, `["pair_style"]`, and so on. All constructor arguments, including `directory`, are parameters, so `from_dict(as_dict())` rebuilds the same calculator. |
| `as_dict()` included the last results | parameters only. Results are never serialized. |

Bugs fixed while touching this code:

* **VASP**: forces were read from `vasprun.xml` only when force constants existed (IBRION 5–8), so normal static and relax runs returned no forces. Forces are now always read. Stress is now read too: VASP gives kBar with pressure positive, and it is converted to eV/Å³ with tension positive (the ASE convention).
* **Gaussian**: `energy` was returned in Hartree although `Results` documents eV. It is now in eV. The raw Hartree value is in `r.extra["energy_hartree"]`.
* **Gaussian / LAMMPS**: a missing output file silently gave an empty result. It now raises `FileNotFoundError`.
* **LAMMPS**: the energy is the `pe` column. It was `etotal`, which is the same value only because `run 0` has no velocities.
* **MatterSim**: a missing prediction was reported as energy 0.0 and zero forces. It is now `None`.

## P4 — `AIEngine` removed

`Agent` is the only entry point. The terminal is `ReplController` + `create_terminal`.

| removed | use instead |
|---|---|
| `AIEngine(api_key=..., model=..., workspace_path=...)` | `Agent(workspace=..., provider=DeepSeekProvider(api_key, model))`, or `matsimpy.ai.cli.build_agent(...)` for the same setup as the `matsimpy-ai` CLI (all builtin tools, `core` loaded, `soul.md` appended to the prompt) |
| `engine.chat(text)` | `agent.run(text).response` (`AgentResult` also has `tools`, `artifacts`, `trace_id`, `usage`) |
| `engine.conversation` (a mutable list) | `agent.conversation_messages()`; add context with `agent.add_context(msg)` |
| `engine.repl()` / `engine._handle_command(cmd)` | `create_terminal(ReplController.for_agent(agent)).run()` / `ReplController.for_agent(agent).execute(cmd)` |
| `engine.repl_controller`, `engine.agent`, `engine.runtime`, and similar | `ReplController.for_agent(agent)`, `agent`, `agent.runtime` |
| `AIEngine._render_command_result` | `matsimpy.ai.terminal.format_command_result(result) -> str`. The terminal now shows the command data (session list, skill details, ...), not only the one-line hint. |

REPL commands: `/workspace`, `/model`, `/load`, `/unload`, `/memory` and `/save` were only reachable through the deprecated `engine.repl()`. They are now `ReplController.for_agent` commands and work in the `matsimpy-ai` terminal.

Dropped commands:

* `/clear`: use `/new`.
* `/plan`: use `/trace`.
* `/history`, `/system` and `/reload`: no longer offered.
* `/save-storage` and `/load-storage`: they used an in-memory backend, so a saved conversation could never be loaded again.
