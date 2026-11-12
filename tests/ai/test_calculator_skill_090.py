"""The AI calculator skill uses the stateless calculator API (0.9.0)."""

from matsimpy.ai.skills.calculator import _calculate_lennard_jones, _write_calculator_input
from matsimpy.calculator import LennardJones
from matsimpy.core import Molecule


def test_lennard_jones_skill_matches_compute():
    m = Molecule(["Ar", "Ar"], [[0, 0, 0], [3.8, 0, 0]])
    out = _calculate_lennard_jones(m)
    assert out["energy"] == LennardJones().compute(m).energy
    assert len(out["forces"]) == 2 and "stress" not in out


def test_write_calculator_input_writes_files_only(tmp_path):
    m = Molecule(["Ar", "Ar"], [[0, 0, 0], [3.8, 0, 0]])
    out = _write_calculator_input("lammps", m, directory=str(tmp_path / "run"))
    assert out["run"] is False and out["directory"] == str(tmp_path / "run")
    assert sorted(p.name for p in (tmp_path / "run").iterdir()) == ["data.lammps", "in.lammps"]
    assert "energy" not in out
