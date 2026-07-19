"""Native VASP input-set workflows that must not depend on pymatgen."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.calculator.vasp.inputs import Kpoints
from matsimpy.calculator.vasp.sets import (
    DictSet,
    MITRelaxSet,
    MPNMRSet,
    MPNonSCFSet,
    MPRelaxSet,
    MPStaticSet,
    NEBSet,
    batch_write_input,
    get_structure_from_prev_run,
    standardize_structure,
)
from matsimpy.core import Crystal, Lattice


@pytest.fixture
def si_crystal() -> Crystal:
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.43))


def test_sets_module_has_no_pymatgen_imports() -> None:
    path = Path(__file__).parents[2] / "matsimpy/calculator/vasp/sets.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert not [name for name in imports if name == "pymatgen" or name.startswith("pymatgen.")]


def test_dict_set_workflow_when_pymatgen_is_blocked(tmp_path: Path) -> None:
    blocker = tmp_path / "sitecustomize.py"
    blocker.write_text(
        "import builtins\n"
        "real_import = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name == 'pymatgen' or name.startswith('pymatgen.'):\n"
        "        raise ImportError('pymatgen blocked by test')\n"
        "    return real_import(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n"
    )
    code = (
        "from matsimpy.core import Crystal, Lattice; "
        "from matsimpy.calculator.vasp.sets import MPRelaxSet; "
        "s=Crystal(['Si','Si'],[[0,0,0],[.25,.25,.25]],Lattice.cubic(5.43)); "
        "v=MPRelaxSet(s).get_input_set(potcar_spec=True); "
        "assert v['INCAR']['ENCUT'] == 520"
    )
    repo_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": f"{tmp_path}{os.pathsep}{repo_root}"}
    result = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_dict_set_generates_native_inputs(si_crystal: Crystal) -> None:
    input_set = DictSet(
        si_crystal,
        {"INCAR": {"ENCUT": 400}, "KPOINTS": {"grid_density": 1000}, "POTCAR": {"Si": "Si"}},
    )
    result = input_set.get_input_set(potcar_spec=True)
    assert result["INCAR"]["ENCUT"] == 400
    assert result["POSCAR"].structure == si_crystal
    assert type(input_set).__mro__[1].__module__.startswith("matsimpy")


def test_standardize_structure_returns_crystal(si_crystal: Crystal) -> None:
    standardized = standardize_structure(si_crystal, sym_prec=1e-3, international_monoclinic=True)
    assert isinstance(standardized, Crystal)


def test_standardize_structure_rejects_unsupported_monoclinic_convention(si_crystal: Crystal) -> None:
    with pytest.raises(NotImplementedError, match="international_monoclinic=False"):
        standardize_structure(si_crystal, international_monoclinic=False)


@pytest.mark.parametrize(
    ("lattice", "densities", "expected_grid", "expected_style"),
    [
        (Lattice.cubic(4), [16, 16, 16], (4, 4, 4), "Monkhorst"),
        (Lattice.hexagonal(3, 5), [12, 12, 20], (4, 4, 4), "Gamma"),
    ],
)
def test_automatic_density_by_lengths_uses_native_crystals(
    lattice: Lattice,
    densities: list[float],
    expected_grid: tuple[int, int, int],
    expected_style: str,
) -> None:
    structure = Crystal(["Si"], [[0, 0, 0]], lattice)
    kpoints = Kpoints.automatic_density_by_lengths(structure, densities)
    assert kpoints.kpts == [expected_grid]
    assert kpoints.style.name == expected_style


@pytest.mark.requires_pymatgen
@pytest.mark.parametrize("lattice", [Lattice.cubic(4), Lattice.hexagonal(3, 5)])
def test_optional_automatic_density_by_lengths_parity(lattice: Lattice) -> None:
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure as PmgStructure
    from pymatgen.io.vasp.inputs import Kpoints as PmgKpoints

    native_structure = Crystal(["Si"], [[0, 0, 0]], lattice)
    reference_structure = PmgStructure(PmgLattice(lattice.matrix), ["Si"], [[0, 0, 0]])
    native = Kpoints.automatic_density_by_lengths(native_structure, [16, 16, 20])
    reference = PmgKpoints.automatic_density_by_lengths(reference_structure, [16, 16, 20])
    assert native.kpts == reference.kpts
    assert native.style.name == reference.style.name


def test_explicit_reciprocal_density_mesh_is_symmetry_reduced(si_crystal: Crystal) -> None:
    input_set = DictSet(
        si_crystal,
        {
            "INCAR": {},
            "KPOINTS": {"reciprocal_density": 100, "explicit": True},
            "POTCAR": {"Si": "Si"},
        },
    )
    kpoints = input_set.kpoints
    full_mesh_size = int(np.prod(Kpoints.automatic_density_by_vol(si_crystal, 100).kpts[0]))
    assert kpoints.num_kpts < full_mesh_size
    assert sum(kpoints.kpts_weights) == full_mesh_size


def test_line_mode_kpoints_use_native_kpath(si_crystal: Crystal) -> None:
    input_set = DictSet(si_crystal, {"INCAR": {}, "KPOINTS": {"line_density": 10}, "POTCAR": {"Si": "Si"}})
    kpoints = input_set.kpoints
    assert kpoints.style.name == "Reciprocal"
    assert kpoints.num_kpts > 2
    assert any(kpoints.labels)


def test_input_set_monty_round_trip(si_crystal: Crystal) -> None:
    original = MPRelaxSet(si_crystal, user_incar_settings={"ENCUT": 321})
    restored = MontyDecoder().process_decoded(original.as_dict())
    assert isinstance(restored, MPRelaxSet)
    assert restored.structure == si_crystal
    assert restored.user_incar_settings["ENCUT"] == 321


def test_stateless_input_set_monty_round_trip() -> None:
    original = MPRelaxSet()
    restored = MontyDecoder().process_decoded(original.as_dict())
    assert isinstance(restored, MPRelaxSet)
    assert restored.structure is None


def test_nmr_efg_uses_native_isotope_data() -> None:
    aluminum = Crystal(["Al"], [[0, 0, 0]], Lattice.cubic(4.05))
    nmr_set = MPNMRSet(aluminum, mode="efg", isotopes=["Al-27"])
    assert nmr_set.incar_updates["QUAD_EFG"] == pytest.approx([146.6])


def test_nmr_efg_uses_pinned_default_isotope() -> None:
    boron = Crystal(["B"], [[0, 0, 0]], Lattice.cubic(4))
    assert MPNMRSet(boron, mode="efg").incar_updates["QUAD_EFG"] == pytest.approx([84.59])
    assert MPNMRSet(boron, mode="efg", isotopes=["B-11"]).incar_updates["QUAD_EFG"] == pytest.approx([40.59])


@pytest.mark.requires_pymatgen
def test_optional_nmr_boron_isotope_parity() -> None:
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure as PmgStructure
    from pymatgen.io.vasp.sets import MPNMRSet as PmgMPNMRSet

    native_structure = Crystal(["B"], [[0, 0, 0]], Lattice.cubic(4))
    reference_structure = PmgStructure(PmgLattice.cubic(4), ["B"], [[0, 0, 0]])
    for isotopes in ([], ["B-11"]):
        native = MPNMRSet(native_structure, mode="efg", isotopes=isotopes)
        reference = PmgMPNMRSet(reference_structure, mode="efg", isotopes=isotopes)
        assert native.incar_updates["QUAD_EFG"] == pytest.approx(reference.incar_updates["QUAD_EFG"])


def test_nmr_efg_reports_missing_isotope_data() -> None:
    helium = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(4))
    with pytest.raises(ValueError, match="quadrupole moment.*He"):
        MPNMRSet(helium, mode="efg").incar_updates


def test_neb_processes_periodic_image_crossing(si_crystal: Crystal) -> None:
    middle = Crystal(["Si", "Si"], [[0, 0, 0], [0.99, 0.25, 0.25]], si_crystal.lattice)
    final = Crystal(["Si", "Si"], [[0, 0, 0], [0.01, 0.25, 0.25]], si_crystal.lattice)
    neb = NEBSet([si_crystal, middle, final])
    assert len(neb.poscars) == 3
    step = neb.structures[2].frac_positions[1] - neb.structures[1].frac_positions[1]
    assert abs(step[0]) < 0.5


@pytest.mark.parametrize("set_type", [MITRelaxSet, MPRelaxSet, MPStaticSet, MPNonSCFSet])
def test_derived_sets_generate_native_inputs(set_type, si_crystal: Crystal) -> None:
    result = set_type(si_crystal).get_input_set(potcar_spec=True)
    assert result["INCAR"]
    assert result["KPOINTS"]
    assert result["POSCAR"].structure == si_crystal
    assert result["POTCAR.spec"]


@pytest.mark.requires_pymatgen
@pytest.mark.parametrize(
    ("native_type", "reference_name"),
    [
        (MITRelaxSet, "MITRelaxSet"),
        (MPRelaxSet, "MPRelaxSet"),
        (MPStaticSet, "MPStaticSet"),
        (MPNonSCFSet, "MPNonSCFSet"),
    ],
)
def test_optional_derived_set_parity(native_type, reference_name: str, si_crystal: Crystal) -> None:
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure as PmgStructure
    from pymatgen.io.vasp import sets as pmg_sets

    reference_structure = PmgStructure(
        PmgLattice(si_crystal.lattice.matrix), si_crystal.species, si_crystal.frac_positions
    )
    native = native_type(si_crystal)
    reference = getattr(pmg_sets, reference_name)(reference_structure)

    assert dict(native.incar) == dict(reference.incar)
    assert native.kpoints.style.name == reference.kpoints.style.name
    assert np.allclose(native.kpoints.kpts, reference.kpoints.kpts)
    assert native.kpoints.kpts_weights == reference.kpoints.kpts_weights
    assert native.kpoints.labels == reference.kpoints.labels
    assert native.poscar.site_symbols == reference.poscar.site_symbols
    assert np.allclose(native.poscar.structure.frac_positions, reference.poscar.structure.frac_coords)
    assert native.potcar_symbols == reference.potcar_symbols


@pytest.mark.requires_pymatgen
def test_optional_neb_set_parity(si_crystal: Crystal) -> None:
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PmgLattice
    from pymatgen.core import Structure as PmgStructure
    from pymatgen.io.vasp.sets import NEBSet as PmgNEBSet

    images = [si_crystal, si_crystal.copy(), si_crystal.copy()]
    reference_images = [
        PmgStructure(PmgLattice(image.lattice.matrix), image.species, image.frac_positions) for image in images
    ]
    native = NEBSet(images)
    reference = PmgNEBSet(reference_images)
    assert dict(native.incar) == dict(reference.incar)
    assert native.kpoints.style.name == reference.kpoints.style.name
    assert np.allclose(native.kpoints.kpts, reference.kpoints.kpts)
    assert native.potcar_symbols == reference.potcar_symbols


def test_previous_run_structure_properties_are_native(si_crystal: Crystal) -> None:
    vasprun = SimpleNamespace(
        final_structure=si_crystal,
        is_spin=True,
        parameters={"MAGMOM": [1.0, -1.0], "LDAU": False},
    )
    restored = get_structure_from_prev_run(vasprun)
    assert isinstance(restored, Crystal)
    assert [site.properties["magmom"] for site in restored] == [1.0, -1.0]


@pytest.mark.parametrize("algorithm", ["niggli", "LLL"])
def test_structure_reduction_options_remain_supported(si_crystal: Crystal, algorithm: str) -> None:
    reduced = MPRelaxSet(si_crystal, reduce_structure=algorithm).structure
    assert isinstance(reduced, Crystal)
    assert reduced.volume == pytest.approx(si_crystal.volume)


def test_batch_write_native_inputs(tmp_path: Path, si_crystal: Crystal) -> None:
    batch_write_input([si_crystal], output_dir=tmp_path, sanitize=True, potcar_spec=True)
    output = next(tmp_path.iterdir())
    assert (output / "INCAR").is_file()
    assert (output / "KPOINTS").is_file()
    assert (output / "POSCAR").is_file()
    assert (output / "POTCAR.spec").is_file()
