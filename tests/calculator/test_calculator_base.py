"""Contract tests for the stateless Calculator / FileIOCalculator base classes (0.9.0)."""

import json

import numpy as np
import pytest

from matsimpy.calculator.base import Calculator, FileIOCalculator
from matsimpy.calculator.results import Results
from matsimpy.core import Crystal, Lattice, Molecule


class MockCalculator(Calculator):
    def __init__(self, **parameters):
        super().__init__(**parameters)
        self.calls = 0

    def _calculate(self, structure):
        self.calls += 1
        n = len(structure)
        return {"energy": float(n), "forces": np.arange(3 * n, dtype=float).reshape(n, 3),
                "stress": np.eye(3), "tag": "x"}


class EnergyOnly(Calculator):
    def _calculate(self, structure):
        return Results(energy=-1.0)


class DummyFileCalculator(FileIOCalculator):
    def __init__(self, directory="dummy", scale=1.0):
        super().__init__(directory, scale=scale)
        self.executed = []

    def write_input(self, structure, directory=None):
        directory = self._dir(directory)
        (directory / "in.json").write_text(json.dumps({"n": len(structure)}))
        return directory

    def _execute(self, directory):
        self.executed.append(directory)
        n = json.loads((directory / "in.json").read_text())["n"]
        (directory / "out.json").write_text(json.dumps({"energy": -n * self.parameters["scale"]}))

    def read_results(self, directory=None):
        directory = self.directory if directory is None else directory
        return Results(energy=json.loads((directory / "out.json").read_text())["energy"])


@pytest.fixture
def crystal():
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.43))


def test_compute_returns_frozen_results(crystal):
    r = MockCalculator().compute(crystal)
    assert r.energy == 2.0 and r.forces.shape == (2, 3)
    assert r.extra["tag"] == "x"
    with pytest.raises(ValueError):
        r.forces[0, 0] = 1.0


def test_calculator_keeps_no_structure_state():
    calc = MockCalculator()
    for gone in ("results", "structure", "calculate", "get_result", "run", "_calculation_performed",
                 "read_results", "write_input", "update_parameters"):
        assert not hasattr(calc, gone), gone


def test_compute_caches_by_structure_and_parameters_invalidate(crystal):
    calc = MockCalculator(sigma=1.0)
    calc.compute(crystal)
    calc.compute(crystal.copy())
    assert calc.calls == 1
    calc.compute(Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]]))
    assert calc.calls == 2
    calc.set_parameters(sigma=2.0)
    calc.compute(crystal)
    assert calc.calls == 3
    assert calc.get_parameters() == {"sigma": 2.0}


def test_compute_rejects_non_structures():
    with pytest.raises(TypeError):
        MockCalculator().compute("not a structure")


def test_getters_require_structure_and_report_missing_quantities(crystal):
    calc = MockCalculator()
    assert calc.get_potential_energy(crystal) == 2.0
    forces = calc.get_forces(crystal)
    forces[0, 0] = 99.0  # writable copy, cache untouched
    assert calc.compute(crystal).forces[0, 0] == 0.0
    assert calc.get_stress(crystal).shape == (3, 3)
    assert calc.get_stress(crystal, voigt=True).tolist() == [1, 1, 1, 0, 0, 0]
    with pytest.raises(TypeError):
        calc.get_stress(crystal, True)  # voigt is keyword-only
    with pytest.raises(TypeError):
        calc.get_potential_energy()  # no "last structure" any more
    with pytest.raises(ValueError, match="Forces"):
        EnergyOnly().get_forces(crystal)
    with pytest.raises(ValueError, match="Stress"):
        EnergyOnly().get_stress(crystal)


def test_serialization_is_parameters_only(crystal):
    calc = MockCalculator(sigma=3.4, epsilon=0.01)
    calc.compute(crystal)
    d = calc.as_dict()
    assert d["parameters"] == {"sigma": 3.4, "epsilon": 0.01} and "results" not in d
    assert MockCalculator.from_dict(d).parameters == calc.parameters
    assert repr(calc) == "MockCalculator(sigma=3.4, epsilon=0.01)"


def test_file_calculator_pipeline_and_offline_steps(crystal, tmp_path):
    calc = DummyFileCalculator(directory=tmp_path / "run", scale=2.0)
    assert calc.compute(crystal).energy == -4.0
    assert calc.executed == [tmp_path / "run"]

    offline = tmp_path / "offline"
    assert calc.write_input(crystal, offline) == offline
    assert not (offline / "out.json").exists()  # nothing executed
    (offline / "out.json").write_text(json.dumps({"energy": -7.0}))
    assert calc.read_results(offline).energy == -7.0
    assert len(calc.executed) == 1


def test_file_calculator_roundtrips_its_configuration(tmp_path):
    calc = DummyFileCalculator(directory=tmp_path / "x", scale=3.0)
    clone = DummyFileCalculator.from_dict(calc.as_dict())
    assert clone.directory == calc.directory and clone.parameters == calc.parameters


def test_compute_cache_is_least_recently_used(crystal):
    calc = MockCalculator()
    calc.cache_size = 2
    a, b, c = (crystal.set_pbc(p) for p in ([True] * 3, [True, True, False], [True, False, False]))
    r = calc.compute(a)
    calc.compute(b)
    assert calc.compute(a) is r and calc.calls == 2  # hit
    calc.compute(c)                                   # evicts b
    calc.compute(b)
    assert calc.calls == 4
    calc.set_parameters(sigma=2.0)                    # a parameter change clears the cache
    assert calc.compute(a) is not r and calc.calls == 5


def test_results_as_dict_returns_independent_copies(crystal):
    calc = MockCalculator()
    d = calc.compute(crystal).as_dict()
    d["forces"][0, 0] = 1e9
    d["energy"] = 0.0
    assert calc.compute(crystal).forces[0, 0] != 1e9
    assert calc.get_potential_energy(crystal) != 0.0


def test_structures_do_not_carry_calculators(crystal):
    for name in ("calc", "get_potential_energy", "get_forces", "get_stress"):
        assert not hasattr(crystal, name)
    with pytest.raises(AttributeError, match="calc.get_potential_energy"):
        crystal.calc = MockCalculator()  # fails loudly instead of adding an attribute
