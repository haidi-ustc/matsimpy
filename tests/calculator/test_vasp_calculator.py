"""VaspCalculator: inputs from the MP input sets, running VASP, reading results.

Uses the real fixtures in fixtures/vasp and pymatgen's placeholder POTCARs only.
"""

import shutil
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

from matsimpy.calculator.vasp import VaspCalculator
from matsimpy.calculator.vasp.inputs import Incar, Kpoints, Poscar, UnknownPotcarWarning
from matsimpy.calculator.vasp.outputs import Vasprun
from matsimpy.core import Crystal, Lattice, Molecule

VASP_DIR = Path(__file__).parent / "fixtures" / "vasp"
FAKE_POTCARS = VASP_DIR / "fake_potcars"
KBAR_TO_EV_PER_A3 = 0.1 / 160.21766208


@pytest.fixture
def fepo4():
    return Poscar.from_file(VASP_DIR / "POSCAR", check_for_potcar=False).structure


@pytest.fixture
def potcars(monkeypatch):
    monkeypatch.setenv("PMG_VASP_PSP_DIR", str(FAKE_POTCARS))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnknownPotcarWarning)  # placeholders are never verified
        yield


# --------------------------------------------------------------------------- inputs


def test_write_input_uses_mp_static_set_with_the_overrides(fepo4, potcars, tmp_path):
    calc = VaspCalculator(directory=tmp_path / "unused", incar={"ENCUT": 400}, kpoints=[4, 4, 4])
    assert calc.write_input(fepo4, tmp_path) == tmp_path
    assert not (tmp_path / "unused").exists()  # an explicit directory wins
    incar = Incar.from_file(tmp_path / "INCAR")
    assert (incar["ENCUT"], incar["NSW"], incar["ISMEAR"], incar["LORBIT"]) == (400, 0, -5, 11)
    assert incar["LDAU"] is True and incar["LDAUU"] == [5.3, 0, 0]  # MP's +U for Fe in an oxide
    assert (tmp_path / "KPOINTS").read_text().splitlines()[2:4] == ["Gamma", "4 4 4"]
    potcar = (tmp_path / "POTCAR").read_text()
    assert [line.split()[3] for line in potcar.splitlines() if "TITEL" in line] == ["Fe_pv", "P", "O"]
    assert Poscar.from_file(tmp_path / "POSCAR", check_for_potcar=False).site_symbols == ["Fe", "P", "O"]


def test_inputs_match_pymatgen(fepo4, potcars, tmp_path):
    sets = pytest.importorskip("pymatgen.io.vasp.sets")
    from matsimpy.io import to_pymatgen

    VaspCalculator(incar={"ENCUT": 400, "EDIFF": 1e-6}, copy_potcar=False).write_input(fepo4, tmp_path)
    reference = sets.MPStaticSet(to_pymatgen(fepo4), user_incar_settings={"ENCUT": 400, "EDIFF": 1e-6})
    assert dict(Incar.from_file(tmp_path / "INCAR")) == dict(reference.incar)
    kpoints = Kpoints.from_file(tmp_path / "KPOINTS")
    assert [list(k) for k in kpoints.kpts] == [list(k) for k in reference.kpoints.kpts]  # the set's density


def test_without_copy_potcar_a_potcar_spec_names_the_potcars(fepo4, tmp_path, monkeypatch):
    monkeypatch.setenv("PMG_VASP_PSP_DIR", str(tmp_path / "none"))  # not needed, not read
    VaspCalculator(input_set="MPRelaxSet", copy_potcar=False).write_input(fepo4, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["INCAR", "KPOINTS", "POSCAR", "POTCAR.spec"]
    assert (tmp_path / "POTCAR.spec").read_text().split() == ["Fe_pv", "P", "O"]
    assert Incar.from_file(tmp_path / "INCAR")["ISIF"] == 3


def test_atoms_are_grouped_by_species_in_order_of_first_appearance(tmp_path):
    crystal = Crystal(["O", "Si", "O"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], Lattice.cubic(5))
    VaspCalculator(copy_potcar=False).write_input(crystal, tmp_path)
    poscar = Poscar.from_file(tmp_path / "POSCAR", check_for_potcar=False)
    assert poscar.site_symbols == ["O", "Si"]  # the input sets would sort Si first
    np.testing.assert_allclose(poscar.structure.frac_positions, [[0, 0, 0], [0.25] * 3, [0.5] * 3])


def test_compute_returns_forces_in_the_order_of_the_structure(tmp_path, monkeypatch):
    crystal = Crystal(["O", "Si", "O"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], Lattice.cubic(5))
    calc = VaspCalculator(directory=tmp_path, copy_potcar=False)
    monkeypatch.setattr(calc, "_execute", lambda directory: None)

    def read_results(directory=None):  # a force that names its atom: [Z, x, 0]
        from matsimpy.calculator.results import Results

        written = Poscar.from_file(Path(directory) / "POSCAR", check_for_potcar=False).structure
        return Results(energy=-1.0, forces=[[e.atomic_no, p[0], 0] for e, p in zip(written.elements,
                                                                            written.frac_positions)])

    monkeypatch.setattr(calc, "read_results", read_results)
    np.testing.assert_allclose(calc.compute(crystal).forces, [[8, 0, 0], [14, 0.5, 0], [8, 0.25, 0]])


@pytest.mark.parametrize("options, error", [
    ({"input_set": "MPMagicSet"}, "unknown VASP input set"),
    ({"input_set": "VaspInputSet"}, "unknown VASP input set"),
    ({"kpoints": [4, 4]}, "three positive integers"),
    ({"kpoints": [4, 0, 4]}, "three positive integers"),
])
def test_bad_settings_fail_on_construction(options, error):
    with pytest.raises(ValueError, match=error):
        VaspCalculator(**options)


def test_parameters_round_trip_and_molecules_are_rejected(tmp_path):
    calc = VaspCalculator(incar={"ENCUT": 400}, kpoints={"reciprocal_density": 200}, input_set="MPRelaxSet",
                          potcar_functional="PBE_64", vasp_cmd="mpirun -np 4 vasp_std", timeout=60)
    assert VaspCalculator.from_dict(calc.as_dict()).parameters == calc.parameters
    with pytest.raises(TypeError, match="needs a Crystal"):
        calc.write_input(Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]]), tmp_path)


# --------------------------------------------------------------------------- running


def _python(code: str) -> str:
    return f'{sys.executable} -c "{code}"'


def test_a_failing_run_reports_its_output(tmp_path):
    calc = VaspCalculator(directory=tmp_path, copy_potcar=False,
                          vasp_cmd=_python("import sys; print('ERROR: bad INCAR tag'); sys.exit(3)"))
    with pytest.raises(RuntimeError, match=r"exit code 3:\nERROR: bad INCAR tag"):
        calc.compute(Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43)))


def test_a_run_longer_than_the_timeout_is_stopped(tmp_path):
    import subprocess

    calc = VaspCalculator(directory=tmp_path, copy_potcar=False, timeout=0.5,
                          vasp_cmd=_python("import time; time.sleep(30)"))
    with pytest.raises(subprocess.TimeoutExpired):
        calc.compute(Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43)))


# --------------------------------------------------------------------------- results


def test_read_results_from_vasprun():
    r = VaspCalculator().read_results(VASP_DIR)
    last = Vasprun(str(VASP_DIR / "vasprun.xml")).ionic_steps[-1]
    assert r.energy == pytest.approx(-269.38319884, abs=1e-7)
    np.testing.assert_array_equal(r.forces, np.asarray(last["forces"]))  # 0.8.x gave no forces
    # kBar (pressure positive) -> eV/A^3 (tension positive)
    np.testing.assert_allclose(r.stress, -np.asarray(last["stress"]) * KBAR_TO_EV_PER_A3, rtol=1e-6)
    assert r.stress[2, 2] > 0  # raw zz = -1.159 kBar (tensile)


def test_read_results_from_outcar_matches_ase(tmp_path):
    ase_io = pytest.importorskip("ase.io")
    shutil.copy(VASP_DIR / "OUTCAR", tmp_path / "OUTCAR")
    r = VaspCalculator().read_results(tmp_path)
    atoms = ase_io.read(tmp_path / "OUTCAR", format="vasp-out")
    assert r.energy == pytest.approx(-34.007267)
    np.testing.assert_allclose(r.forces, atoms.get_forces(), atol=1e-6)  # the OUTCAR path had no forces
    np.testing.assert_allclose(r.stress, atoms.get_stress(voigt=False), atol=1e-8)


def test_read_results_from_oszicar_or_nothing(tmp_path):
    shutil.copy(VASP_DIR / "OSZICAR", tmp_path / "OSZICAR")
    r = VaspCalculator().read_results(tmp_path)
    assert r.energy == pytest.approx(-526.63928) and r.forces is None
    with pytest.raises(FileNotFoundError, match="no vasprun.xml, OUTCAR or OSZICAR"):
        VaspCalculator().read_results(tmp_path / "empty")
