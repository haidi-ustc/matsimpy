# VASP Pymatgen Independence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `matsimpy.calculator.vasp` fully functional without a runtime pymatgen installation while preserving its current VASP-facing API and validating results against `pymatgen==2025.6.14`.

**Architecture:** Introduce small MatSimPy-native packages for electronic-structure values, entries, trajectories, volumetric data, Wannier UNK files, and symmetry services. VASP parsers and input sets consume those native interfaces unconditionally; pymatgen appears only in marked parity tests as a black-box oracle.

**Tech Stack:** Python 3.9+, NumPy, SciPy, Monty/MSONable, optional spglib, optional h5py, pytest, optional `pymatgen==2025.6.14`.

## Global Constraints

- Production code in `matsimpy.calculator.vasp` must not import pymatgen directly, conditionally, lazily, or indirectly through a compatibility adapter.
- Preserve VASP-facing class names, method signatures, important attributes, enum values, array shapes/order, warnings/errors, and Monty serialization behavior.
- Newly serialized native objects use their real `matsimpy.*` module identities; compatibility readers accept legacy pymatgen-shaped dictionaries needed by existing workflows.
- `pymatgen==2025.6.14` is optional and may be imported only by tests marked `requires_pymatgen`.
- Implement from specifications, mathematics, MatSimPy conventions, and black-box observations. Do not copy pymatgen source by default.
- Any unavoidable adapted pymatgen code must identify version, source file, adapted scope, copyright, and MIT license in the source file and project documentation.
- Every supported API returns a real native object; no `None` aliases, dummy base classes, or silent partial results.

## File Structure

- `matsimpy/electronic_structure/core.py`: spin/orbital enums and magnetic moments.
- `matsimpy/electronic_structure/dos.py`: total and site/orbital projected density of states.
- `matsimpy/electronic_structure/bandstructure.py`: k-points, band structures, symmetry-line branches, reconstruction.
- `matsimpy/electronic_structure/entries.py`: computed composition/structure entries.
- `matsimpy/electronic_structure/__init__.py`: stable native exports.
- `matsimpy/core/trajectory.py`: ordered Crystal frames and Monty serialization.
- `matsimpy/io/volumetric.py`: reusable grid-data model and arithmetic.
- `matsimpy/io/wannier.py`: UNK binary writer.
- `matsimpy/symmetry/spacegroup.py`: VASP-required spglib-backed standardization interface.
- `matsimpy/symmetry/matcher.py`: lattice/species/coordinate structure matching.
- `matsimpy/symmetry/kpath.py`: native high-symmetry k-path generation.
- `tests/architecture/test_vasp_no_pymatgen.py`: static and subprocess dependency boundary.
- `tests/electronic_structure/`: native unit and optional parity tests.
- `tests/core/test_trajectory.py`: trajectory contract.
- `tests/io/test_volumetric.py`, `tests/io/test_wannier.py`: reusable IO contracts.
- `tests/symmetry/test_vasp_services.py`: symmetry/matcher/k-path native and parity tests.
- `tests/calculator/test_vasp_outputs_parity.py`: parser-result parity.
- `tests/calculator/test_vasp_sets_native.py`: pymatgen-free input-set workflows.

---

### Task 1: Lock the Runtime Boundary and Parity Oracle

**Files:**
- Create: `tests/architecture/test_vasp_no_pymatgen.py`
- Create: `tests/calculator/vasp_parity.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: current VASP modules and the existing `requires_pymatgen` marker.
- Produces: `neutral_structure()`, `neutral_array_map()`, and a hard architectural test used by every later task.

- [ ] **Step 1: Write the failing static boundary test**

```python
import ast
from pathlib import Path
import pytest


VASP_DIR = Path(__file__).parents[2] / "matsimpy" / "calculator" / "vasp"


@pytest.mark.xfail(strict=True, reason="migration characterization: remove in Task 9")
def test_vasp_production_modules_do_not_import_pymatgen():
    violations = []
    for path in VASP_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name == "pymatgen" or name.startswith("pymatgen.") for name in names):
                violations.append(f"{path.name}:{node.lineno}")
    assert violations == []
```

- [ ] **Step 2: Run the boundary test and confirm characterization failure**

Run: `pytest tests/architecture/test_vasp_no_pymatgen.py -v`

Expected: XFAIL, with the assertion listing imports in `sets.py` and `outputs.py`.

- [ ] **Step 3: Add neutral parity helpers and pin the oracle extra**

```python
# tests/calculator/vasp_parity.py
import numpy as np


def neutral_structure(structure):
    return {
        "lattice": np.asarray(structure.lattice.matrix, dtype=float),
        "species": [str(site.specie) for site in structure],
        "frac_coords": np.asarray(structure.frac_coords, dtype=float),
    }


def neutral_array_map(values):
    return {int(key): np.asarray(value) for key, value in values.items()}
```

Add to `[project.optional-dependencies]`:

```toml
parity = [
    "pymatgen==2025.6.14",
    "spglib",
]
```

- [ ] **Step 4: Add the blocked-import subprocess test**

```python
def test_vasp_imports_when_pymatgen_is_blocked(tmp_path):
    import os
    import subprocess
    import sys

    blocker = tmp_path / "sitecustomize.py"
    blocker.write_text(
        "import builtins\n"
        "_real = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name == 'pymatgen' or name.startswith('pymatgen.'):\n"
        "        raise ImportError('blocked by architecture test')\n"
        "    return _real(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n"
    )
    code = (
        "import matsimpy.calculator.vasp.inputs; "
        "import matsimpy.calculator.vasp.outputs; "
        "import matsimpy.calculator.vasp.sets"
    )
    env = {**os.environ, "PYTHONPATH": f"{tmp_path}{os.pathsep}{os.getcwd()}"}
    result = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 5: Run characterization tests**

Run: `pytest tests/architecture/test_vasp_no_pymatgen.py tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_inputs.py -v`

Expected: the static test remains XFAIL; existing calculator tests retain their baseline result.

- [ ] **Step 6: Commit the characterization harness**

```bash
git add pyproject.toml tests/architecture/test_vasp_no_pymatgen.py tests/calculator/vasp_parity.py
git commit -m "test: define pymatgen-free VASP boundary"
```

### Task 2: Add Native Spin, Orbital, Magnetic-Moment, and Parse Types

**Files:**
- Create: `matsimpy/electronic_structure/__init__.py`
- Create: `matsimpy/electronic_structure/core.py`
- Create: `matsimpy/io/errors.py`
- Create: `tests/electronic_structure/test_core.py`
- Modify: `matsimpy/calculator/vasp/inputs.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`

**Interfaces:**
- Produces: `Spin(IntEnum)`, `OrbitalType(IntEnum)`, `Orbital(IntEnum)`, `Magmom(MSONable)`, and `ParseError(ValueError)`.
- Enum values: `Spin.up == 1`, `Spin.down == -1`; orbital values follow VASP column order used by `_parse_dos`.

- [ ] **Step 1: Write failing enum and Monty tests**

```python
import numpy as np
from monty.json import MontyDecoder

from matsimpy.electronic_structure import Magmom, Orbital, OrbitalType, Spin


def test_spin_and_orbital_values_match_vasp_conventions():
    assert int(Spin.up) == 1
    assert int(Spin.down) == -1
    assert OrbitalType(0).name == "s"
    assert Orbital(0).name == "s"
    assert Orbital(1).name == "py"


def test_magmom_scalar_vector_and_monty_roundtrip():
    assert np.allclose(Magmom(2.5).moment, [0.0, 0.0, 2.5])
    vector = Magmom([1, 2, 3])
    assert np.allclose(vector.moment, [1, 2, 3])
    restored = MontyDecoder().process_decoded(vector.as_dict())
    assert restored == vector
```

- [ ] **Step 2: Verify the tests fail**

Run: `pytest tests/electronic_structure/test_core.py -v`

Expected: FAIL because `matsimpy.electronic_structure` does not exist.

- [ ] **Step 3: Implement the native primitives**

```python
# matsimpy/electronic_structure/core.py
from enum import IntEnum
import numpy as np
from monty.json import MSONable


class Spin(IntEnum):
    up = 1
    down = -1


class OrbitalType(IntEnum):
    s = 0
    p = 1
    d = 2
    f = 3


class Orbital(IntEnum):
    s = 0
    py = 1
    pz = 2
    px = 3
    dxy = 4
    dyz = 5
    dz2 = 6
    dxz = 7
    dx2 = 8
    f_3 = 9
    f_2 = 10
    f_1 = 11
    f0 = 12
    f1 = 13
    f2 = 14
    f3 = 15


class Magmom(MSONable):
    def __init__(self, moment):
        values = np.asarray(moment if np.ndim(moment) else [0.0, 0.0, moment], dtype=float)
        if values.shape != (3,):
            raise ValueError("magnetic moment must be a scalar or length-3 vector")
        self.moment = values

    def __eq__(self, other):
        return isinstance(other, Magmom) and np.array_equal(self.moment, other.moment)

    def as_dict(self):
        return {"@module": type(self).__module__, "@class": type(self).__name__, "moment": self.moment.tolist()}

    @classmethod
    def from_dict(cls, data):
        return cls(data["moment"])
```

Define all exports in `matsimpy/electronic_structure/__init__.py`. Define `class ParseError(ValueError): pass` in `matsimpy/io/errors.py`. Replace the local VASP `Magmom` and output fallbacks with imports from these modules.

- [ ] **Step 4: Run native and affected parser tests**

Run: `pytest tests/electronic_structure/test_core.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_outputs.py -v`

Expected: PASS.

- [ ] **Step 5: Add and run optional parity assertions**

```python
@pytest.mark.requires_pymatgen
def test_enum_values_match_pymatgen_2025_6_14():
    pytest.importorskip("pymatgen")
    from pymatgen.electronic_structure.core import Orbital as POrbital, Spin as PSpin
    from matsimpy.electronic_structure import Orbital, Spin
    assert {x.name: int(x) for x in Spin} == {x.name: int(x) for x in PSpin}
    assert {x.name: int(x) for x in Orbital} == {x.name: int(x) for x in POrbital}
```

Run: `pytest tests/electronic_structure/test_core.py -m requires_pymatgen -v`

Expected: PASS with pymatgen 2025.6.14; otherwise SKIP.

- [ ] **Step 6: Commit**

```bash
git add matsimpy/electronic_structure matsimpy/io/errors.py matsimpy/calculator/vasp/inputs.py matsimpy/calculator/vasp/outputs.py tests/electronic_structure/test_core.py
git commit -m "feat: add native electronic structure primitives"
```

### Task 3: Add Native DOS Objects and Switch Vasprun DOS Parsing

**Files:**
- Create: `matsimpy/electronic_structure/dos.py`
- Create: `tests/electronic_structure/test_dos.py`
- Modify: `matsimpy/electronic_structure/__init__.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Modify: `tests/calculator/test_vasp_outputs_parity.py`

**Interfaces:**
- Consumes: `Spin`, `Orbital`, `OrbitalType`, `Crystal`.
- Produces: `Dos(efermi, energies, densities)` and `CompleteDos(structure, total_dos, pdos, normalize=False)` with interpolation, gap, density, normalization, and Monty methods used by VASP.

- [ ] **Step 1: Write failing DOS contract tests**

```python
import numpy as np
from monty.json import MontyDecoder
from matsimpy.electronic_structure import Dos, Spin


def test_dos_density_interpolation_gap_and_roundtrip():
    dos = Dos(0.0, [-2, -1, 0, 1, 2], {Spin.up: [1, 0, 0, 0, 1]})
    assert dos.get_densities(Spin.up).shape == (5,)
    assert dos.get_interpolated_value(1.5)[Spin.up] == 0.5
    assert dos.get_gap(tol=1e-8) == 4.0
    restored = MontyDecoder().process_decoded(dos.as_dict())
    assert np.array_equal(restored.energies, dos.energies)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/electronic_structure/test_dos.py -v`

Expected: FAIL importing `Dos`.

- [ ] **Step 3: Implement DOS algorithms**

Implement validation that energies are one-dimensional and every density has the same length. `get_densities(None)` sums spin arrays; `get_interpolated_value()` uses `numpy.interp`; gap discovery finds the nearest density-above-tolerance samples below and above `efermi`. `CompleteDos` stores site-indexed orbital maps and divides densities by `structure.volume` only when `normalize=True`. Use explicit `as_dict()`/`from_dict()` methods with spin keys serialized as integer strings.

```python
class Dos(MSONable):
    def __init__(self, efermi, energies, densities):
        self.efermi = float(efermi)
        self.energies = np.asarray(energies, dtype=float)
        self.densities = {Spin(int(k)): np.asarray(v, dtype=float) for k, v in densities.items()}
        if self.energies.ndim != 1 or any(v.shape != self.energies.shape for v in self.densities.values()):
            raise ValueError("DOS energies and densities must be equal-length 1D arrays")

    def get_densities(self, spin=None):
        return self.densities[Spin(spin)] if spin is not None else sum(self.densities.values())

    def get_interpolated_value(self, energy):
        return {spin: float(np.interp(energy, self.energies, values)) for spin, values in self.densities.items()}
```

- [ ] **Step 4: Switch `_parse_dos` and `complete_dos` to native types**

Import `Dos` and `CompleteDos` unconditionally in `outputs.py`; remove their guarded aliases. Keep `_parse_dos` array construction unchanged so this task changes the result layer, not parsing semantics.

- [ ] **Step 5: Run native and parser tests**

Run: `pytest tests/electronic_structure/test_dos.py tests/calculator/test_vasp_outputs.py -v`

Expected: PASS.

- [ ] **Step 6: Add parity comparisons and run them**

Compare `efermi`, energies, each integer-normalized spin density, and each site/orbital projected density from the shared `vasprun.xml` fixture with `np.testing.assert_allclose(rtol=1e-10, atol=1e-10)`.

Run: `pytest tests/calculator/test_vasp_outputs_parity.py -k dos -m requires_pymatgen -v`

Expected: PASS or SKIP when the oracle extra is absent.

- [ ] **Step 7: Commit**

```bash
git add matsimpy/electronic_structure tests/electronic_structure/test_dos.py matsimpy/calculator/vasp/outputs.py tests/calculator/test_vasp_outputs_parity.py
git commit -m "feat: add native VASP DOS results"
```

### Task 4: Add Native Band Structures

**Files:**
- Create: `matsimpy/electronic_structure/bandstructure.py`
- Create: `tests/electronic_structure/test_bandstructure.py`
- Modify: `matsimpy/electronic_structure/__init__.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Modify: `tests/calculator/test_vasp_outputs_parity.py`

**Interfaces:**
- Consumes: `Spin`, `Lattice`, NumPy eigenvalue/projection arrays.
- Produces: `Kpoint`, `BandStructure`, `BandStructureSymmLine`, and `get_reconstructed_band_structure(branches, efermi=None)`.

- [ ] **Step 1: Write failing band-structure tests**

```python
def test_band_structure_edges_and_gap():
    reciprocal = Lattice.cubic(1.0)
    bands = {Spin.up: np.array([[-1.0, -0.5], [1.0, 1.5]])}
    bs = BandStructure([[0, 0, 0], [0.5, 0, 0]], bands, reciprocal, 0.0)
    assert bs.nb_bands == 2
    assert bs.is_metal() is False
    assert bs.get_band_gap()["energy"] == pytest.approx(1.5)
    assert bs.get_vbm()["energy"] == pytest.approx(-0.5)
    assert bs.get_cbm()["energy"] == pytest.approx(1.0)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/electronic_structure/test_bandstructure.py -v`

Expected: FAIL importing `BandStructure`.

- [ ] **Step 3: Implement validated band containers and edge algorithms**

Construct k-points from fractional coordinates, enforce eigenvalue shape `(nbands, nkpoints)`, and enforce projection leading dimensions `(nbands, nkpoints)`. VBM is the maximum eigenvalue `<= efermi`; CBM is the minimum eigenvalue `> efermi`; metal detection finds a band spanning the Fermi level. Symmetry-line objects additionally retain `labels_dict`, derive contiguous branches from labeled endpoints, and serialize all arrays with integer-string spin keys.

```python
def get_reconstructed_band_structure(branches, efermi=None):
    if not branches:
        raise ValueError("at least one band-structure branch is required")
    reference = branches[0]
    merged_kpoints = []
    merged = {spin: [] for spin in reference.bands}
    for branch in branches:
        if set(branch.bands) != set(reference.bands):
            raise ValueError("all branches must have identical spin channels")
        merged_kpoints.extend(k.frac_coords for k in branch.kpoints)
        for spin, values in branch.bands.items():
            merged[spin].append(values)
    merged = {spin: np.concatenate(parts, axis=1) for spin, parts in merged.items()}
    return BandStructureSymmLine(merged_kpoints, merged, reference.lattice_rec,
                                 reference.efermi if efermi is None else efermi,
                                 labels_dict={})
```

- [ ] **Step 4: Switch Vasprun band APIs to native types**

Replace guarded imports and preserve `Vasprun.get_band_structure()`, `get_band_structure_from_vasp_multiple_branches()`, and `get_adjusted_fermi_level()` signatures. Make the returned native class depend only on whether line-mode labels are present, as before.

- [ ] **Step 5: Run native and VASP tests**

Run: `pytest tests/electronic_structure/test_bandstructure.py tests/calculator/test_vasp_outputs.py -v`

Expected: PASS.

- [ ] **Step 6: Run optional parity tests**

Compare efermi, reciprocal lattice, k-point fractional coordinates, labels, branch endpoints, spin-keyed bands, VBM, CBM, and gap. Use exact comparisons for labels/shapes and `assert_allclose(atol=1e-8)` for floats.

Run: `pytest tests/calculator/test_vasp_outputs_parity.py -k band -m requires_pymatgen -v`

Expected: PASS or SKIP.

- [ ] **Step 7: Commit**

```bash
git add matsimpy/electronic_structure matsimpy/calculator/vasp/outputs.py tests/electronic_structure/test_bandstructure.py tests/calculator/test_vasp_outputs_parity.py
git commit -m "feat: add native VASP band structures"
```

### Task 5: Add Computed Entries and Trajectories

**Files:**
- Create: `matsimpy/electronic_structure/entries.py`
- Create: `matsimpy/core/trajectory.py`
- Create: `tests/electronic_structure/test_entries.py`
- Create: `tests/core/test_trajectory.py`
- Modify: `matsimpy/electronic_structure/__init__.py`
- Modify: `matsimpy/core/__init__.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`

**Interfaces:**
- Produces: `ComputedEntry(composition, energy, correction=0.0, parameters=None, data=None, entry_id=None)`, `ComputedStructureEntry(structure, ...)`, and `Trajectory.from_structures(structures, constant_lattice=False)`.

- [ ] **Step 1: Write failing entry and trajectory contracts**

```python
def test_computed_structure_entry_energy_and_roundtrip(si_crystal):
    entry = ComputedStructureEntry(si_crystal, -10.0, correction=0.25, entry_id="si")
    assert entry.energy == -9.75
    assert entry.energy_per_atom == pytest.approx(-4.875)
    assert MontyDecoder().process_decoded(entry.as_dict()).structure == si_crystal


def test_trajectory_from_structures_keeps_variable_lattices(si_crystal):
    expanded = Crystal(si_crystal.species, si_crystal.frac_positions, Lattice.cubic(6.0))
    trajectory = Trajectory.from_structures([si_crystal, expanded], constant_lattice=False)
    assert len(trajectory) == 2
    assert trajectory[1].lattice == expanded.lattice
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/electronic_structure/test_entries.py tests/core/test_trajectory.py -v`

Expected: FAIL importing the new classes.

- [ ] **Step 3: Implement entries**

Store uncorrected energy separately; expose `energy = uncorrected_energy + correction` and `energy_per_atom = energy / composition.num_atoms`. `ComputedStructureEntry` derives composition from its Crystal. Serialize nested MatSimPy objects through their dictionaries and restore through `MontyDecoder`.

- [ ] **Step 4: Implement trajectory**

Store immutable frame copies, implement `__len__`, integer/slice `__getitem__`, iteration, `from_structures`, `as_dict`, and `from_dict`. With `constant_lattice=True`, reject differing lattices with `ValueError`.

- [ ] **Step 5: Switch Vasprun entry and trajectory methods**

Import the native classes unconditionally and preserve current argument forwarding in `get_computed_entry()` and `get_trajectory()`.

- [ ] **Step 6: Run native, parser, and Monty tests**

Run: `pytest tests/electronic_structure/test_entries.py tests/core/test_trajectory.py tests/calculator/test_vasp_outputs.py -v`

Expected: PASS.

- [ ] **Step 7: Add optional parity comparisons**

Compare entry composition dictionaries, corrected/uncorrected energy, parameters, data, entry ID, trajectory length, lattices, species, and coordinates against pymatgen 2025.6.14.

Run: `pytest tests/calculator/test_vasp_outputs_parity.py -k 'entry or trajectory' -m requires_pymatgen -v`

Expected: PASS or SKIP.

- [ ] **Step 8: Commit**

```bash
git add matsimpy/electronic_structure matsimpy/core/trajectory.py matsimpy/core/__init__.py matsimpy/calculator/vasp/outputs.py tests/electronic_structure/test_entries.py tests/core/test_trajectory.py tests/calculator/test_vasp_outputs_parity.py
git commit -m "feat: add native entries and trajectories"
```

### Task 6: Add Native Volumetric Data and Wannier UNK Writing

**Files:**
- Create: `matsimpy/io/volumetric.py`
- Create: `matsimpy/io/wannier.py`
- Create: `tests/io/test_volumetric.py`
- Create: `tests/io/test_wannier.py`
- Modify: `matsimpy/calculator/vasp/outputs.py`

**Interfaces:**
- Produces: `VolumetricData(structure, data, distance_matrix=None, data_aug=None)` and `Unk(ik, data).write_file(filename)`.

- [ ] **Step 1: Write failing volumetric contracts**

```python
def test_volumetric_arithmetic_integral_and_roundtrip(si_crystal):
    grid = np.arange(8.0).reshape(2, 2, 2)
    volume = VolumetricData(si_crystal, {"total": grid})
    assert volume.dim == (2, 2, 2)
    assert volume.ngridpts == 8
    assert volume.value_at(1, 1, 1) == 7.0
    assert (volume + volume).data["total"][1, 1, 1] == 14.0
    assert volume.get_integrated_diff(0, 1.0).shape[1] == 2
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/io/test_volumetric.py tests/io/test_wannier.py -v`

Expected: FAIL importing the native support types.

- [ ] **Step 3: Implement volumetric validation and operations**

Require non-empty same-shaped 3D arrays. Expose `dim`, `ngridpts`, `value_at`, linear interpolation on fractional grid positions, scalar/grid arithmetic, spin data, axis averages, and radial integrated differences using minimum-image distances from the selected site. Preserve `data_aug` and Monty round trips.

- [ ] **Step 4: Implement UNK writer from the published Wannier90 record layout**

Write Fortran unformatted records with grid dimensions, k-point index, band count, and complex128 band grids in Fortran order. Validate data shape as `(nbands, nx, ny, nz)` or `(nbands, 2, nx, ny, nz)` and emit the noncollinear filename content without importing pymatgen.

- [ ] **Step 5: Rebase VASP `VolumetricData` and `Wavecar.write_unks`**

Subclass/import the native volumetric base and native `Unk` unconditionally. Keep VASP file parsing and formatting in `outputs.py`.

- [ ] **Step 6: Run native and affected parser tests**

Run: `pytest tests/io/test_volumetric.py tests/io/test_wannier.py tests/calculator/test_vasp_outputs.py -v`

Expected: PASS.

- [ ] **Step 7: Run optional parity tests**

Compare grid keys/shapes/values, axis averages, integrated differences, arithmetic results, and byte-level UNK output for deterministic small arrays.

Run: `pytest tests/calculator/test_vasp_outputs_parity.py -k 'volumetric or unk' -m requires_pymatgen -v`

Expected: PASS or SKIP.

- [ ] **Step 8: Commit**

```bash
git add matsimpy/io/volumetric.py matsimpy/io/wannier.py matsimpy/calculator/vasp/outputs.py tests/io/test_volumetric.py tests/io/test_wannier.py tests/calculator/test_vasp_outputs_parity.py
git commit -m "feat: add native volumetric and Wannier support"
```

### Task 7: Extend MatSimPy Symmetry Services

**Files:**
- Create: `matsimpy/symmetry/spacegroup.py`
- Create: `matsimpy/symmetry/matcher.py`
- Create: `matsimpy/symmetry/kpath.py`
- Create: `tests/symmetry/test_vasp_services.py`
- Modify: `matsimpy/symmetry/__init__.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `SpacegroupAnalyzer(structure, symprec=0.01, angle_tolerance=5.0)`, `StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5)`, and `HighSymmKpath(structure, symprec=0.01, angle_tolerance=5.0)`.
- Required methods: `get_primitive_standard_structure()`, `get_conventional_standard_structure()`, `get_ir_reciprocal_mesh(mesh, is_shift=(0,0,0))`, `fit(a,b)`, and `get_kpoints(line_density=20, coords_are_cartesian=False)`.

- [ ] **Step 1: Write failing symmetry service tests**

```python
@pytest.mark.requires_spglib
def test_spacegroup_standardization_and_ir_mesh(si_crystal):
    analyzer = SpacegroupAnalyzer(si_crystal, symprec=1e-3)
    primitive = analyzer.get_primitive_standard_structure()
    conventional = analyzer.get_conventional_standard_structure()
    points, weights = analyzer.get_ir_reciprocal_mesh((4, 4, 4))
    assert len(primitive) <= len(conventional)
    assert sum(weights) == 64
    assert np.asarray(points).shape[1] == 3


def test_structure_matcher_handles_permutation_and_translation(si_crystal):
    moved = Crystal(si_crystal.species[::-1], (si_crystal.frac_positions[::-1] + 0.2) % 1,
                    si_crystal.lattice)
    assert StructureMatcher().fit(si_crystal, moved)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/symmetry/test_vasp_services.py -v`

Expected: FAIL importing `SpacegroupAnalyzer`, `StructureMatcher`, and `HighSymmKpath` from `matsimpy.symmetry`.

- [ ] **Step 3: Implement space-group services on spglib**

Convert `Crystal` to `(lattice.matrix, frac_positions, atomic_numbers)`. Use `spglib.standardize_cell(..., to_primitive=True/False, no_idealize=False)` and reconstruct `Crystal` with symbols mapped from atomic numbers. Use `spglib.get_ir_reciprocal_mesh`; group mapping indices into representatives and weights. Raise the existing targeted spglib installation error when unavailable.

- [ ] **Step 4: Implement deterministic structure matching**

Reject differing compositions. Compare lattice lengths/angles under `ltol`/`angle_tol`; group sites by element; for each trial translation aligning the first site of the least-common element, build periodic fractional-distance cost matrices and use `scipy.optimize.linear_sum_assignment`. Return true only when every matched Cartesian distance divided by the free length per atom is at most `stol`.

- [ ] **Step 5: Implement high-symmetry paths**

Use standardized reciprocal lattices and the crystallographic path tables stored in a new data constant inside `kpath.py`. Cover the Bravais lattices exercised by MatSimPy VASP sets (cubic P/F/I, tetragonal P/I, orthorhombic P/F/I/C, hexagonal, rhombohedral, monoclinic P/C, triclinic). Interpolate each labeled segment at `ceil(line_density * reciprocal_distance)` points and return coordinates plus a same-length label list whose interior entries are empty strings.

- [ ] **Step 6: Run native symmetry tests**

Add `"requires_spglib: marks tests that require spglib"` to the pytest marker list in `pyproject.toml`, then run:

Run: `pytest tests/symmetry/test_vasp_services.py -v`

Expected: PASS; spglib-only tests SKIP if spglib is absent.

- [ ] **Step 7: Add optional parity matrix**

Parametrize representative structures for every supported Bravais class. Compare standardized composition/lattice/coordinates, match decisions, irreducible-mesh weights, k-point coordinates, and labels against pymatgen 2025.6.14 using `atol=1e-7` after deterministic coordinate sorting.

Run: `pytest tests/symmetry/test_vasp_services.py -m requires_pymatgen -v`

Expected: PASS with both optional dependencies or SKIP.

- [ ] **Step 8: Commit**

```bash
git add matsimpy/symmetry tests/symmetry/test_vasp_services.py pyproject.toml
git commit -m "feat: add native VASP symmetry services"
```

### Task 8: Remove Pymatgen from VASP Input Sets

**Files:**
- Modify: `matsimpy/calculator/vasp/sets.py`
- Create: `tests/calculator/test_vasp_sets_native.py`
- Modify: `tests/calculator/test_vasp_inputs.py`

**Interfaces:**
- Consumes: native `SpacegroupAnalyzer`, `StructureMatcher`, `HighSymmKpath`, `Crystal`, and `Element`.
- Produces: unchanged `VaspInputSet`, `DictSet`, derived-set, previous-run, standardization, NEB, and batch APIs.

- [ ] **Step 1: Write blocked-import input-set workflows**

```python
def test_dict_set_generates_native_inputs(si_crystal):
    input_set = DictSet(si_crystal, {"INCAR": {"ENCUT": 400}, "KPOINTS": {"grid_density": 1000}})
    result = input_set.get_input_set(potcar_spec=True)
    assert result["INCAR"]["ENCUT"] == 400
    assert result["POSCAR"].structure == si_crystal
    assert type(input_set).__mro__[1].__module__.startswith("matsimpy")


def test_standardize_structure_returns_crystal(si_crystal):
    standardized = standardize_structure(si_crystal, sym_prec=1e-3, international_monoclinic=True)
    assert isinstance(standardized, Crystal)
```

- [ ] **Step 2: Verify failures with pymatgen blocked**

Run: `pytest tests/calculator/test_vasp_sets_native.py -v`

Expected: FAIL because `VaspInputSet` still inherits pymatgen's `InputGenerator` when pymatgen is installed, or because the native symmetry path is not wired when it is absent.

- [ ] **Step 3: Replace framework and structural type dependencies**

Define a native `InputGenerator(MSONable)` base with no behavior beyond serialization, or inherit `MSONable` directly if no inherited method is used. Replace `SiteCollection` checks with `isinstance(value, (Crystal, Molecule))`; replace `PeriodicSite` construction with direct fractional-coordinate arrays; replace `Species(...).get_nmr_quadrupole_moment()` with an `Element` data lookup that raises a precise `ValueError` when isotope data is unavailable.

- [ ] **Step 4: Replace symmetry imports and remove all guards**

Import the Task 7 services unconditionally. Remove `_HAS_SYMMETRY`, dummy `InputGenerator`, `None` aliases, pymatgen-only `TYPE_CHECKING` imports, and all fallback branches. Feature calls requiring spglib rely on the native service's targeted error.

- [ ] **Step 5: Test every affected call site**

Add focused tests for line-mode `kpoints`, reciprocal-density reduction, `standardize_structure`, previous-run structure matching, NMR quadrupole lookup behavior, NEB structure interpolation checks, and `as_dict()`/`from_dict()` of a stateless and stateful input set.

Run: `pytest tests/calculator/test_vasp_sets_native.py tests/calculator/test_vasp_inputs.py -v`

Expected: PASS without importing pymatgen.

- [ ] **Step 6: Run optional input-set parity**

For `MITRelaxSet`, `MPRelaxSet`, `MPStaticSet`, `MPNonSCFSet`, and one NEB set, compare neutral INCAR dictionaries, KPOINTS styles/grids/weights/labels, POSCAR species and coordinates, and POTCAR symbols against pymatgen 2025.6.14.

Run: `pytest tests/calculator/test_vasp_sets_native.py -m requires_pymatgen -v`

Expected: PASS or SKIP.

- [ ] **Step 7: Run the static boundary test**

Run: `pytest tests/architecture/test_vasp_no_pymatgen.py::test_vasp_production_modules_do_not_import_pymatgen -v`

Expected: XFAIL; inspecting the assertion detail shows only `outputs.py` violations and none from `sets.py`.

- [ ] **Step 8: Commit**

```bash
git add matsimpy/calculator/vasp/sets.py tests/calculator/test_vasp_sets_native.py tests/calculator/test_vasp_inputs.py
git commit -m "refactor: make VASP input sets pymatgen independent"
```

### Task 9: Complete VASP Output Migration and Legacy Monty Decoding

**Files:**
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Modify: `matsimpy/calculator/vasp/__init__.py`
- Create: `matsimpy/electronic_structure/legacy.py`
- Create: `tests/electronic_structure/test_legacy_monty.py`
- Modify: `tests/calculator/test_vasp_outputs_parity.py`

**Interfaces:**
- Consumes: all native result types from Tasks 2–6.
- Produces: a VASP output module with no pymatgen guards and `decode_legacy_pymatgen_dict(data)` for supported result dictionaries.

- [ ] **Step 1: Write failing full output and legacy-decoding tests**

```python
def test_supported_vasprun_results_are_native(vasprun):
    assert isinstance(vasprun.tdos, Dos)
    assert isinstance(vasprun.complete_dos, CompleteDos)
    assert isinstance(vasprun.get_computed_entry(), ComputedStructureEntry)
    assert isinstance(vasprun.get_trajectory(), Trajectory)


def test_decode_legacy_spin_dos_dictionary():
    data = {"@module": "pymatgen.electronic_structure.dos", "@class": "Dos",
            "efermi": 0.0, "energies": [-1, 1], "densities": {"1": [2, 3]}}
    decoded = decode_legacy_pymatgen_dict(data)
    assert isinstance(decoded, Dos)
    assert np.array_equal(decoded.densities[Spin.up], [2, 3])
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/electronic_structure/test_legacy_monty.py tests/calculator/test_vasp_outputs_parity.py -k native -v`

Expected: FAIL because legacy decoding and some native results are absent.

- [ ] **Step 3: Remove the advanced pymatgen import block**

Import `ComputedEntry`, `ComputedStructureEntry`, `Trajectory`, band classes, enums, DOS classes, native volumetric base, `ParseError`, and `Unk` directly from MatSimPy. Delete `_HAS_PYMATGEN_ES`, every dummy alias, and pymatgen `TYPE_CHECKING` imports. Replace the no-op `unitized` dependency with a local decorator that records `__unit__` on the wrapped property getter without changing values.

- [ ] **Step 4: Implement explicit legacy dictionary dispatch**

Map only supported pairs: DOS/CompleteDos, BandStructure/BandStructureSymmLine, ComputedEntry/ComputedStructureEntry, Trajectory, and VASP volumetric classes. Reject other pymatgen module/class pairs with `NotImplementedError("unsupported legacy pymatgen object: <module>.<class>")`; never import pymatgen during decoding.

- [ ] **Step 5: Exercise all advanced parser paths without pymatgen**

Add fixture-driven checks for DOS, eigenvalues, projected eigenvalues, computed entries, trajectories, PROCAR spin/orbital keys, OUTCAR magnetization and onsite matrices, volumetric data, band reconstruction, and Monty serialization.

Run: `pytest tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_outputs_parity.py tests/electronic_structure/test_legacy_monty.py -m 'not requires_pymatgen' -v`

Expected: PASS.

- [ ] **Step 6: Run all output parity tests**

Run: `pytest tests/calculator/test_vasp_outputs_parity.py -m requires_pymatgen -v`

Expected: PASS with pymatgen 2025.6.14 or SKIP.

- [ ] **Step 7: Make the runtime boundary green**

Remove the temporary `pytest.mark.xfail` decorator and its reason from the static boundary test, then run:

Run: `pytest tests/architecture/test_vasp_no_pymatgen.py -v`

Expected: PASS for both static and subprocess tests.

- [ ] **Step 8: Commit**

```bash
git add matsimpy/calculator/vasp/outputs.py matsimpy/calculator/vasp/__init__.py matsimpy/electronic_structure/legacy.py tests/electronic_structure/test_legacy_monty.py tests/calculator/test_vasp_outputs_parity.py
git commit -m "refactor: complete pymatgen-free VASP outputs"
```

### Task 10: Dependency Metadata, Documentation, Attribution Audit, and Full Verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/installation.rst`
- Modify: `docs/api_reference/index.rst`
- Create: `docs/api_reference/electronic_structure.rst`
- Create: `docs/development/vasp-parity.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: completed native runtime and all test suites.
- Produces: accurate dependency declarations, API docs, reproducible parity instructions, and final evidence.

- [ ] **Step 1: Write the metadata assertion**

```python
def test_vasp_runtime_does_not_require_pymatgen():
    import tomllib
    data = tomllib.loads(Path("pyproject.toml").read_text())
    assert not any(dep.lower().startswith("pymatgen") for dep in data["project"]["dependencies"])
    assert data["project"]["optional-dependencies"]["parity"] == [
        "pymatgen==2025.6.14", "spglib"
    ]
```

- [ ] **Step 2: Update dependency and API documentation**

Document that VASP runtime is native, `spglib` is required only for symmetry-derived input features, `h5py` is required only for VASP HDF5, and `[parity]` installs the pinned oracle. Add API pages for electronic-structure objects and examples showing `Vasprun.complete_dos`, `get_band_structure`, entries, and trajectories.

- [ ] **Step 3: Document parity reproduction and copying policy**

In `docs/development/vasp-parity.md`, record:

```text
Oracle: pymatgen==2025.6.14
Install: python -m pip install -e '.[dev,parity]'
Run: pytest -m requires_pymatgen tests/calculator/test_vasp_outputs_parity.py tests/symmetry/test_vasp_services.py
Policy: pymatgen is a black-box behavioral oracle. Production implementations are original unless a source file contains an explicit adaptation notice with source path, version, scope, copyright, and license.
```

- [ ] **Step 4: Run the attribution audit**

Run: `rg -n 'pymatgen|Materials Project' matsimpy/calculator/vasp matsimpy/electronic_structure matsimpy/symmetry matsimpy/io`

Expected: references are documentation/history/license notices only; no import statements. Inspect every “adapted” notice and ensure it either predates this work or includes the required version/source/scope/license record.

- [ ] **Step 5: Run focused pymatgen-free verification**

Run: `pytest tests/architecture/test_vasp_no_pymatgen.py tests/electronic_structure tests/core/test_trajectory.py tests/io/test_volumetric.py tests/io/test_wannier.py tests/symmetry/test_vasp_services.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_sets_native.py -m 'not requires_pymatgen' -v`

Expected: PASS, with only tests for unavailable optional backends skipped.

- [ ] **Step 6: Run pinned parity verification**

Run: `python -c "import pymatgen.core; from importlib.metadata import version; assert version('pymatgen') == '2025.6.14'" && pytest tests/electronic_structure tests/symmetry/test_vasp_services.py tests/calculator/test_vasp_outputs_parity.py tests/calculator/test_vasp_sets_native.py -m requires_pymatgen -v`

Expected: version assertion and parity tests PASS.

- [ ] **Step 7: Run full feasible regression suite**

Run: `pytest -m 'not requires_torch and not requires_ase' -v`

Expected: PASS. Record any environment-only skips; investigate every failure before completion.

- [ ] **Step 8: Check formatting and repository state**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only intended documentation/metadata changes remain uncommitted.

- [ ] **Step 9: Commit final documentation and metadata**

```bash
git add pyproject.toml README.md docs/installation.rst docs/api_reference docs/development/vasp-parity.md CLAUDE.md tests/architecture/test_vasp_no_pymatgen.py
git commit -m "docs: document native VASP compatibility layer"
```

- [ ] **Step 10: Capture final verification evidence**

Run: `git status --short && git log -10 --oneline`

Expected: clean worktree and eleven focused commits: the design plus ten implementation-task commits.
