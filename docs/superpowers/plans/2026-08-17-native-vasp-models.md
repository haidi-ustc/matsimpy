# Native MatSimPy VASP Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every pymatgen dependency from MatSimPy's VASP production package and provide focused MatSimPy-native models for every VASP workflow that currently consumes pymatgen objects.

**Architecture:** Build small reusable native modules for electronic-structure results, entries, trajectories, volumetric data, Wannier data, input generation, and symmetry. Migrate `outputs.py` and `sets.py` only after those modules have focused tests, then enforce the dependency boundary with an AST contract test. Unused pymatgen-shaped APIs may be removed because backward compatibility is not required.

**Tech Stack:** Python 3.9+, NumPy, SciPy, Monty/MSONable, optional spglib, pytest; all commands run with `conda run -n pmg`.

## Global Constraints

- No runtime or `TYPE_CHECKING` import of pymatgen is allowed below `matsimpy/calculator/vasp`.
- Pymatgen may appear only in validation/reference tests guarded by `pytest.importorskip("pymatgen")` and/or `requires_pymatgen`.
- Backward compatibility with pymatgen-shaped objects, signatures, serialization, configuration names, and dead APIs is not required.
- Preserve scientific file semantics and legal attribution.
- Add no new dependency; use optional `spglib` already declared by the `analysis` extra.
- Write a failing test before each production change and observe the expected failure.
- Use `conda run -n pmg python -m pytest ...` for every test command.

---

### Task 1: Native electronic-structure primitives and unit metadata

**Files:**
- Create: `matsimpy/electronic_structure/__init__.py`
- Create: `matsimpy/electronic_structure/core.py`
- Create: `matsimpy/core/units.py`
- Modify: `matsimpy/core/__init__.py`
- Create: `tests/electronic_structure/test_core.py`
- Create: `tests/core/test_units.py`

**Interfaces:**
- Produces: `Spin(IntEnum)`, `OrbitalType(IntEnum)`, `Orbital(IntEnum)`, `Magmom`, and `unitized(unit: str)`.
- `Spin.up == 1`, `Spin.down == -1`.
- Orbital member names cover VASP XML/HDF5 parsing: `s`, `py`, `pz`, `px`, `dxy`, `dyz`, `dz2`, `dxz`, `dx2`, `f_3`, `f_2`, `f_1`, `f0`, `f1`, `f2`, `f3`.
- `unitized` leaves returned numeric values unchanged and records the unit on the decorated callable as `unit`.

- [ ] **Step 1: Write failing primitive and unit tests**

```python
from matsimpy.electronic_structure import Magmom, Orbital, OrbitalType, Spin
from matsimpy.core.units import unitized


def test_vasp_enum_values_and_names():
    assert Spin.up.value == 1
    assert Spin.down.value == -1
    assert Orbital(8) is Orbital.dx2
    assert Orbital.__members__["f_3"] is Orbital.f_3
    assert OrbitalType(2) is OrbitalType.d


def test_magmom_accepts_scalar_and_vector():
    assert Magmom(2.5).components == (2.5,)
    assert Magmom([1, 2, 3]).components == (1.0, 2.0, 3.0)


def test_unitized_preserves_value_and_exposes_unit():
    @unitized("eV")
    def energy():
        return -1.25

    assert energy() == -1.25
    assert energy.unit == "eV"
```

- [ ] **Step 2: Run tests and verify import failures**

Run: `conda run -n pmg python -m pytest tests/electronic_structure/test_core.py tests/core/test_units.py -q`

Expected: FAIL because the native modules do not exist.

- [ ] **Step 3: Implement the minimal native primitives**

```python
class Spin(IntEnum):
    down = -1
    up = 1


class OrbitalType(IntEnum):
    s = 0
    p = 1
    d = 2
    f = 3


class Magmom(MSONable):
    def __init__(self, value):
        values = value if isinstance(value, (list, tuple, np.ndarray)) else [value]
        self.components = tuple(float(component) for component in values)
```

Implement `Orbital` with the exact ordered names from the interface and export all four types. Implement `unitized` with `functools.wraps`, set `wrapper.unit = unit`, and return the wrapped value unchanged.

- [ ] **Step 4: Run focused tests**

Run: `conda run -n pmg python -m pytest tests/electronic_structure/test_core.py tests/core/test_units.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit the six files with a Lore message whose intent is “Own VASP electronic primitives inside MatSimPy” and record the focused pytest command in `Tested:`.

---

### Task 2: Native computed entries and trajectories

**Files:**
- Create: `matsimpy/core/entries.py`
- Create: `matsimpy/core/trajectory.py`
- Modify: `matsimpy/core/__init__.py`
- Create: `tests/core/test_entries.py`
- Create: `tests/core/test_trajectory.py`

**Interfaces:**
- Produces: `ComputedEntry(composition, energy, parameters=None, data=None, entry_id=None)`.
- Produces: `ComputedStructureEntry(structure, energy, parameters=None, data=None, entry_id=None)` with `.structure` and derived `.composition`.
- Produces: `Trajectory.from_structures(structures, constant_lattice=True)` supporting `len()`, iteration, indexing, `as_dict()`, and `from_dict()`.
- Consumes: MatSimPy `Composition`, `Crystal`, and MSONable serialization.

- [ ] **Step 1: Write failing entry and trajectory tests**

```python
def test_computed_structure_entry_uses_native_crystal(si_crystal):
    entry = ComputedStructureEntry(si_crystal, -5.0, parameters={"run_type": "GGA"})
    assert entry.structure is si_crystal
    assert entry.composition == si_crystal.composition
    assert entry.energy == -5.0
    assert entry.parameters == {"run_type": "GGA"}


def test_trajectory_roundtrip_preserves_native_structures(si_crystal):
    trajectory = Trajectory.from_structures([si_crystal, si_crystal.copy()], constant_lattice=False)
    restored = Trajectory.from_dict(trajectory.as_dict())
    assert len(restored) == 2
    assert all(isinstance(frame, Crystal) for frame in restored)
    assert restored.constant_lattice is False
```

- [ ] **Step 2: Run tests and verify import failures**

Run: `conda run -n pmg python -m pytest tests/core/test_entries.py tests/core/test_trajectory.py -q`

Expected: FAIL because the native models do not exist.

- [ ] **Step 3: Implement immutable-by-convention MSONable containers**

Use explicit constructors that defensively copy `parameters` and `data`. Serialize structures with `structure.as_dict()` and reconstruct them with `Crystal.from_dict()`. Reject an empty trajectory with `ValueError("Trajectory requires at least one structure")`.

```python
class ComputedStructureEntry(ComputedEntry):
    def __init__(self, structure, energy, parameters=None, data=None, entry_id=None):
        self.structure = structure
        super().__init__(structure.composition, energy, parameters, data, entry_id)


class Trajectory(MSONable):
    @classmethod
    def from_structures(cls, structures, constant_lattice=True):
        return cls(list(structures), constant_lattice=constant_lattice)
```

- [ ] **Step 4: Run focused tests**

Run: `conda run -n pmg python -m pytest tests/core/test_entries.py tests/core/test_trajectory.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit with Lore intent “Represent parsed VASP entries and trajectories without external models”.

---

### Task 3: Native DOS and band-structure result models

**Files:**
- Create: `matsimpy/electronic_structure/dos.py`
- Create: `matsimpy/electronic_structure/bandstructure.py`
- Modify: `matsimpy/electronic_structure/__init__.py`
- Create: `tests/electronic_structure/test_dos.py`
- Create: `tests/electronic_structure/test_bandstructure.py`

**Interfaces:**
- Produces: `Dos(efermi, energies, densities)` with NumPy arrays, spin-keyed densities, `as_dict()`, and `from_dict()`.
- Produces: `CompleteDos(structure, total_dos, pdos, normalize=False)`; normalization divides total/projected densities by `structure.volume` and rejects non-positive volume.
- Produces: `BandStructure(kpoints, eigenvalues, lattice, efermi, structure=None, projections=None)`.
- Both band classes expose `.bands`, `.efermi`, `is_metal(tol=1e-4)`, and `get_band_gap()` returning at least `{"energy": float}` for the `sets.py` consumer.
- Produces: `BandStructureSymmLine(..., labels_dict, ...)` with `as_dict()` and `from_dict()`.
- Produces: `get_reconstructed_band_structure(branches, efermi=None)` that validates shared lattice/spin/band dimensions and concatenates k-points, eigenvalues, and projections.

- [ ] **Step 1: Write failing numerical-container tests**

```python
def test_complete_dos_normalizes_by_native_volume(si_crystal):
    total = Dos(0.0, [-1.0, 1.0], {Spin.up: [2.0, 4.0]})
    complete = CompleteDos(si_crystal, total, {}, normalize=True)
    assert complete.total_dos.densities[Spin.up] == pytest.approx(
        np.array([2.0, 4.0]) / si_crystal.volume
    )


def test_band_structure_detects_crossing_band(si_crystal):
    bands = {Spin.up: np.array([[-1.0, 1.0]])}
    bs = BandStructure([[0, 0, 0], [0.5, 0, 0]], bands,
                       si_crystal.lattice.reciprocal_lattice, 0.0,
                       structure=si_crystal)
    assert bs.is_metal()


def test_reconstruct_concatenates_branch_kpoints(two_band_branches):
    result = get_reconstructed_band_structure(two_band_branches, efermi=0.25)
    assert len(result.kpoints) == sum(len(branch.kpoints) for branch in two_band_branches)
    assert result.efermi == 0.25
```

- [ ] **Step 2: Run tests and verify import failures**

Run: `conda run -n pmg python -m pytest tests/electronic_structure/test_dos.py tests/electronic_structure/test_bandstructure.py -q`

Expected: FAIL because DOS and band-structure modules do not exist.

- [ ] **Step 3: Implement only VASP-consumed behavior**

Convert numeric inputs with `np.asarray(..., dtype=float)`, validate energy/density lengths and eigenvalue shape `(nbands, nkpoints)`, and serialize enum dictionary keys by name. Implement `is_metal` by detecting any band whose minimum is at or below `efermi + tol` and maximum is at or above `efermi - tol`.
Implement `get_band_gap` by finding the highest eigenvalue at or below the Fermi level and the lowest eigenvalue above it across every spin channel; metallic structures return zero energy.

```python
def get_reconstructed_band_structure(branches, efermi=None):
    if not branches:
        raise ValueError("At least one band-structure branch is required")
    reference = branches[0]
    merged = {
        spin: np.concatenate([branch.bands[spin] for branch in branches], axis=1)
        for spin in reference.bands
    }
    cls = BandStructureSymmLine if all(isinstance(b, BandStructureSymmLine) for b in branches) else BandStructure
    return cls.from_branches(branches, merged, reference.efermi if efermi is None else efermi)
```

- [ ] **Step 4: Run focused tests**

Run: `conda run -n pmg python -m pytest tests/electronic_structure/test_dos.py tests/electronic_structure/test_bandstructure.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit with Lore intent “Keep VASP DOS and band results native and numerically explicit”.

---

### Task 4: Native volumetric and Wannier data support

**Files:**
- Create: `matsimpy/io/common.py`
- Create: `matsimpy/io/wannier90.py`
- Modify: `matsimpy/io/__init__.py`
- Create: `tests/io/test_volumetric_data.py`
- Create: `tests/io/test_wannier90.py`

**Interfaces:**
- Produces: `VolumetricData(structure, data, data_aug=None)` with `.dim`, `.ngridpts`, `.is_spin_polarized`, `.is_soc`, `.spin_data`, `get_axis_grid(ind)`, `value_at(x, y, z)`, and linear addition/subtraction.
- Produces: `Unk(ik, data)` with validated complex array dimensions and `write_file(filename)` using SciPy `FortranFile`, matching the VASP caller in `Wavecar.write_unks`.

- [ ] **Step 1: Write failing data-model tests**

```python
def test_volumetric_data_derives_grid_and_spin(si_crystal):
    total = np.arange(8, dtype=float).reshape(2, 2, 2)
    diff = np.ones((2, 2, 2))
    volume = VolumetricData(si_crystal, {"total": total, "diff": diff})
    assert volume.dim == (2, 2, 2)
    assert volume.ngridpts == 8
    assert volume.is_spin_polarized
    assert volume.spin_data[Spin.up] == pytest.approx((total + diff) / 2)


def test_unk_writes_fortran_records(tmp_path):
    data = np.ones((1, 2, 2, 2), dtype=np.complex128)
    path = tmp_path / "UNK00001.1"
    Unk(1, data).write_file(path)
    assert path.stat().st_size > data.nbytes
```

- [ ] **Step 2: Run tests and verify import failures**

Run: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py tests/io/test_wannier90.py -q`

Expected: FAIL because the native modules do not exist.

- [ ] **Step 3: Implement validated native containers**

Require all volumetric arrays to share one three-dimensional shape. Implement periodic trilinear sampling in fractional coordinates for `value_at`. Require `Unk.data` shape `(nbands, ngx, ngy, ngz)` for collinear data or `(nbands, 2, ngx, ngy, ngz)` for noncollinear data; reject other ranks with `ValueError`.

- [ ] **Step 4: Run focused tests**

Run: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py tests/io/test_wannier90.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit with Lore intent “Own VASP grid and Wannier data formats inside MatSimPy”.

---

### Task 5: Native input-generator and symmetry services

**Files:**
- Create: `matsimpy/calculator/input_generator.py`
- Create: `matsimpy/symmetry/matcher.py`
- Create: `matsimpy/symmetry/kpath.py`
- Modify: `matsimpy/symmetry/analyzer.py`
- Modify: `matsimpy/symmetry/__init__.py`
- Create: `tests/calculator/test_input_generator.py`
- Create: `tests/symmetry/test_matcher.py`
- Create: `tests/symmetry/test_kpath.py`
- Modify: `tests/symmetry/test_symmetry.py`

**Interfaces:**
- Produces: `InputGenerator(MSONable, abc.ABC)` as the native base for VASP input sets.
- Produces: `StructureMatcher.fit(first: Crystal, second: Crystal) -> bool`, comparing composition, lattice within tolerances, and periodic fractional sites independent of site order.
- Extends: `SymmetryAnalyzer(crystal, symprec=..., angle_tolerance=...)` convenience methods `get_ir_reciprocal_mesh`, `get_primitive_standard_structure`, and `get_conventional_standard_structure`, backed by optional spglib.
- Produces: `HighSymmetryKpath(crystal, symprec=...)` with `get_kpoints(line_density, coords_are_cartesian=False)` and a `kpath` dictionary consumed by VASP sets.
- Missing spglib raises `ImportError("spglib is required; install MatSimPy[analysis]")` only when a symmetry operation is invoked.

- [ ] **Step 1: Confirm spglib contracts from its official API documentation**

Record the exact input/output shapes for `get_ir_reciprocal_mesh`, `standardize_cell`, and `get_symmetry_dataset` in the task notes before writing code. Do not use pymatgen source as production implementation.

- [ ] **Step 2: Write failing service tests**

```python
def test_structure_matcher_ignores_site_order(si_two_site_crystal):
    reversed_crystal = Crystal(
        list(reversed(si_two_site_crystal.species)),
        list(reversed(si_two_site_crystal.positions)),
        si_two_site_crystal.lattice,
    )
    assert StructureMatcher(stol=1e-5).fit(si_two_site_crystal, reversed_crystal)


def test_input_generator_is_native_msonable_base():
    assert issubclass(InputGenerator, MSONable)
    assert inspect.isabstract(InputGenerator)


def test_ir_mesh_returns_native_kpoints_and_weights(si_crystal):
    analyzer = SymmetryAnalyzer(si_crystal, symprec=1e-5)
    mesh = analyzer.get_ir_reciprocal_mesh((2, 2, 2))
    assert sum(weight for _, weight in mesh) == 8
    assert all(len(kpoint) == 3 for kpoint, _ in mesh)


def test_high_symmetry_path_has_labeled_endpoints(si_crystal):
    path = HighSymmetryKpath(si_crystal)
    kpoints, labels = path.get_kpoints(line_density=8)
    assert len(kpoints) == len(labels)
    assert any(label for label in labels)
```

- [ ] **Step 3: Run tests and verify failures**

Run: `conda run -n pmg python -m pytest tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py -q`

Expected: FAIL because the native services or required methods do not exist.

- [ ] **Step 4: Implement the smallest scientific services required by VASP**

Use spglib cells `(lattice_matrix, fractional_positions, atomic_numbers)`. Convert standardized cells back to `Crystal` with `Lattice`. Implement matcher periodic distances by wrapping fractional deltas with `delta -= np.round(delta)`. Keep k-path tables/data and interpolation inside `matsimpy.symmetry.kpath`; do not expose pymatgen naming.

- [ ] **Step 5: Run focused tests**

Run: `conda run -n pmg python -m pytest tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit with Lore intent “Provide native symmetry services for VASP input generation” and cite the official spglib operations checked in the body or trailers.

---

### Task 6: Cut VASP outputs over to native result models

**Files:**
- Modify: `matsimpy/calculator/vasp/outputs.py`
- Modify: `tests/calculator/test_vasp_outputs.py`
- Create: `tests/calculator/test_vasp_native_outputs.py`

**Interfaces:**
- Consumes: Tasks 1–4 native classes.
- Produces: native return values from `Vasprun.complete_dos`, `complete_dos_normalized`, `get_computed_entry`, `get_band_structure`, and `get_trajectory`.
- Produces: native `VolumetricData` inheritance and native `Unk` writes.
- Removes: `_HAS_PYMATGEN_ES`, dummy `None` symbols, dummy base classes, and every pymatgen import in `outputs.py`.

- [ ] **Step 1: Write failing VASP-native integration tests**

```python
def test_vasprun_advanced_results_are_native():
    run = Vasprun(VASP_FIXTURES / "vasprun.xml")
    assert isinstance(run.get_computed_entry(), ComputedStructureEntry)
    assert isinstance(run.get_trajectory(), Trajectory)
    assert isinstance(run.complete_dos, CompleteDos)


def test_outputs_source_has_no_pymatgen_imports():
    path = Path(outputs.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name == "pymatgen" or name.startswith("pymatgen.") for name in imported)
```

- [ ] **Step 2: Run tests and verify the expected dependency failure**

Run: `conda run -n pmg python -m pytest tests/calculator/test_vasp_native_outputs.py -q`

Expected: FAIL because `outputs.py` still imports and returns pymatgen models in the `pmg` environment.

- [ ] **Step 3: Replace the guarded import block with native imports**

Import from `matsimpy.core.entries`, `matsimpy.core.trajectory`, `matsimpy.core.units`, `matsimpy.electronic_structure`, `matsimpy.io.common`, and `matsimpy.io.wannier90`. Define `VaspParseError(FormatError)` using `matsimpy.exceptions.FormatError`. Rename `vasp_to_pmg_orb` to `vasp_orbital_names`. Remove inherited advanced methods that have no caller in the package or tests.

- [ ] **Step 4: Adapt native construction and serialization calls**

Make branch reconstruction, adjusted-Fermi copying, DOS normalization, volumetric subclasses, and UNK writing use the Task 1–4 contracts. Do not add compatibility aliases.

- [ ] **Step 5: Run focused and existing VASP output tests**

Run: `conda run -n pmg python -m pytest tests/calculator/test_vasp_native_outputs.py tests/calculator/test_vasp_outputs.py -q`

Expected: PASS, including the optional pymatgen scientific reference test when pymatgen is installed in `pmg`.

- [ ] **Step 6: Commit**

Commit with Lore intent “Make VASP output parsing return only MatSimPy models”.

---

### Task 7: Cut VASP input sets over to native symmetry and core models

**Files:**
- Modify: `matsimpy/calculator/vasp/sets.py`
- Modify: `matsimpy/calculator/vasp/inputs.py`
- Modify: `matsimpy/core/periodic_table.py`
- Modify: `tests/calculator/test_vasp_sets.py`
- Modify: `tests/calculator/test_vasp_inputs.py`
- Modify: `tests/core/test_periodic_table_comprehensive.py`

**Interfaces:**
- Consumes: native `InputGenerator`, `StructureMatcher`, `SymmetryAnalyzer`, `HighSymmetryKpath`, `Crystal`, `CrystalSite`, and `Element`.
- Removes: `StructureMatcher`, `InputGenerator`, `SpacegroupAnalyzer`, `HighSymmKpath`, `PeriodicSite`, `SiteCollection`, `Species`, `IStructure`, typing aliases, and `due`/`Doi` imports from pymatgen.
- Removes: citation-only decorators from executable classes; retain citations in docstrings or attribution comments.
- Produces: `Element.get_nmr_quadrupole_moment(isotope=None) -> float`, reading the existing `"NMR Quadrupole Moment"` values in `periodic_table.json` and selecting an explicit isotope or the sole/default entry.

- [ ] **Step 1: Replace permissive tests with failing behavioral tests**

```python
def test_dictset_builds_native_inputs_without_skip(si_crystal):
    vset = DictSet(si_crystal, config_dict={"INCAR": {"ENCUT": 400, "ISMEAR": 0}})
    assert vset.incar["ENCUT"] == 400
    assert isinstance(vset.poscar.structure, Crystal)


def test_automatic_ir_mesh_uses_native_symmetry(si_crystal):
    vset = DictSet(si_crystal, config_dict={
        "INCAR": {"ENCUT": 400},
        "KPOINTS": {"reciprocal_density": 100, "force_gamma": True},
    })
    assert isinstance(vset.kpoints, Kpoints)


def test_element_reads_existing_quadrupole_data():
    assert Element("Al").get_nmr_quadrupole_moment("Al-27") != 0.0


def test_sets_source_has_no_pymatgen_imports():
    tree = ast.parse(Path(sets.__file__).read_text(encoding="utf-8"))
    modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name == "pymatgen" or name.startswith("pymatgen.") for name in modules)
```

Delete the `try/except ... pytest.skip` from the current DictSet instantiation test so known porting gaps become failures.

- [ ] **Step 2: Run tests and verify failures**

Run: `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py -q`

Expected: FAIL in native symmetry/input-set paths and the import contract.

- [ ] **Step 3: Replace pymatgen-shaped branches**

Make the structure setter accept `Crystal` only. Replace `PeriodicSite` construction with `CrystalSite`. Add `Element.get_nmr_quadrupole_moment()` over the already bundled periodic-table data and call it from `MPNMRSet`. Use `SymmetryAnalyzer` standardization and irreducible mesh methods and `HighSymmetryKpath` path generation. Remove citation decorators and `TYPE_CHECKING` pymatgen aliases.

- [ ] **Step 4: Rename native-facing symbols where clarity improves**

Use `HighSymmetryKpath` in annotations and code. Remove `VaspInputGenerator` or other compatibility aliases when repository search shows no internal consumer. Rename pymatgen-specific local variables/messages that no longer describe the implementation, while retaining legal attribution and hash provenance.

- [ ] **Step 5: Run VASP input and set tests**

Run: `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_imports.py tests/core/test_periodic_table_comprehensive.py -q`

Expected: PASS without skips for known porting gaps.

- [ ] **Step 6: Commit**

Commit with Lore intent “Generate VASP inputs through MatSimPy symmetry and core models”.

---

### Task 8: Enforce the package boundary and run adversarial validation

**Files:**
- Modify: `tests/calculator/test_vasp_imports.py`
- Modify: `tests/test_packaging_runtime_contracts.py`
- Modify: VASP/native files only for failures exposed by this validation.

**Interfaces:**
- Produces: one AST contract covering every `*.py` file under `matsimpy/calculator/vasp`.
- Produces: a subprocess import test that blocks `pymatgen` and imports `matsimpy.calculator.vasp`, `inputs`, `outputs`, and `sets` successfully.
- Preserves: optional reference-oracle tests under `requires_pymatgen`.

- [ ] **Step 1: Write the package-wide failing dependency contract**

```python
def imported_modules(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    return {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }


def test_vasp_package_never_imports_pymatgen():
    vasp_root = Path(vasp.__file__).parent
    violations = []
    for source in vasp_root.glob("*.py"):
        for module in imported_modules(source):
            if module == "pymatgen" or module.startswith("pymatgen."):
                violations.append(f"{source.name}: {module}")
    assert violations == []
```

Extend the existing blocked-import subprocess test so `blocked = {"ase", "pymatgen"}` and all VASP modules import in a fresh interpreter.

- [ ] **Step 2: Run the dependency contracts**

Run: `conda run -n pmg python -m pytest tests/calculator/test_vasp_imports.py tests/test_packaging_runtime_contracts.py -q`

Expected before final cleanup: FAIL with exact remaining import locations, or PASS if Tasks 6–7 removed all imports.

- [ ] **Step 3: Remove every remaining executable dependency or dead surface**

Use `rg -n "(^|[[:space:]])(from|import)[[:space:]]+pymatgen" matsimpy/calculator/vasp` and remove each match. Do not suppress or weaken the AST test. Keep pymatgen reference comparisons only under `tests/`.

- [ ] **Step 4: Run focused VASP and native-model suites**

Run: `conda run -n pmg python -m pytest tests/calculator/test_vasp_imports.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_native_outputs.py tests/electronic_structure tests/symmetry tests/core/test_entries.py tests/core/test_trajectory.py tests/core/test_units.py tests/io/test_volumetric_data.py tests/io/test_wannier90.py tests/test_packaging_runtime_contracts.py -q`

Expected: PASS with zero known-gap skips in the migrated VASP paths.

- [ ] **Step 5: Run static and full-suite verification**

Run: `conda run -n pmg python -m compileall -q matsimpy`

Run: `conda run -n pmg python -m pytest -q`

Run: `conda run -n pmg python -m ruff check matsimpy tests`

Expected: pytest and compileall PASS. Ruff passes when installed; if the command reports `No module named ruff`, record that exact gap in `Not-tested:` rather than installing a dependency.

- [ ] **Step 6: Review the final diff and commit**

Run: `git diff --check` and `git status --short`. Review that production pymatgen imports are absent, validation imports remain test-only, new modules are exported intentionally, and no unrelated files changed.

Commit with Lore intent “Enforce a permanently self-supported VASP package”, `Scope-risk: broad`, the full validation commands in `Tested:`, and any unavailable check in `Not-tested:`.
