"""Tests for script-mode classification helpers."""

from matsimpy.ai.runtime import is_long_running_script


def test_long_running_detects_external_calculator_imports():
    scripts = [
        "from matsimpy.calculator.vasp import VaspCalculator\n",
        "from matsimpy.calculator.lammps.calculator import LammpsCalculator\n",
        "import matsimpy.calculator.gaussian\n",
        "import matsimpy.calculator.mattersim.calculator as ms_calc\n",
    ]

    for script in scripts:
        assert is_long_running_script(script) is True


def test_long_running_detects_expensive_function_calls():
    scripts = [
        "relax(structure)\n",
        "calc.optimize(crystal)\n",
        "runner.md(steps=1000)\n",
        "workflow.minimize()\n",
    ]

    for script in scripts:
        assert is_long_running_script(script) is True


def test_long_running_returns_false_for_short_safe_scripts():
    script = (
        "from matsimpy.builders.bulk import from_prototype\n"
        "crystal = from_prototype('fcc', 'Cu', 3.61)\n"
        "print(crystal.formula)\n"
    )

    assert is_long_running_script(script) is False


def test_long_running_returns_false_for_invalid_python():
    assert is_long_running_script("from matsimpy.calculator.vasp import") is False
