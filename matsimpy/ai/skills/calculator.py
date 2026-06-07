"""Calculator skill — compact wrappers for calculator setup and results."""

from __future__ import annotations

from matsimpy.ai.executor import get_last_structure
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import sig_to_schema
from matsimpy.calculator import LennardJones

SKILL_NAME = "calculator"
SKILL_DESCRIPTION = "Calculators: energies, forces, stresses, and external input preparation"
SKILL_KEYWORDS: list[str] = [
    "calculator",
    "calculate",
    "energy",
    "force",
    "forces",
    "stress",
    "lj",
    "lennard-jones",
    "vasp",
    "lammps",
    "gaussian",
    "mattersim",
]


def _list_calculators():
    from matsimpy import calculator as calculator_pkg

    names = []
    for name in getattr(calculator_pkg, "__all__", []):
        value = getattr(calculator_pkg, name, None)
        if value is not None:
            names.append(name)
    return {"calculators": names}


def _calculate_lennard_jones(structure=None, sigma: float = 3.4, epsilon: float = 0.0104):
    if structure is None:
        structure = get_last_structure()
    if structure is None:
        return {"error": "No structure available. Create or read a structure first."}

    calc = LennardJones(sigma=sigma, epsilon=epsilon)
    calc.calculate(structure)
    result = {
        "formula": structure.formula,
        "num_atoms": len(structure),
        "energy": calc.get_potential_energy(),
    }
    try:
        result["forces"] = calc.get_forces().tolist()
    except Exception:
        pass
    try:
        result["stress"] = calc.get_stress().tolist()
    except Exception:
        pass
    return result


def _write_calculator_input(calculator: str, structure=None, run: bool = False, **parameters):
    if structure is None:
        structure = get_last_structure()
    if structure is None:
        return {"error": "No structure available. Create or read a structure first."}

    from matsimpy import calculator as calculator_pkg

    calculator_map = {
        "vasp": "VaspCalculator",
        "gaussian": "GaussianCalculator",
        "lammps": "LammpsCalculator",
    }
    cls_name = calculator_map.get(calculator.lower(), calculator)
    cls = getattr(calculator_pkg, cls_name, None)
    if cls is None:
        return {"error": f"Unknown calculator: {calculator}"}

    calc = cls(run=run, **parameters)
    calc.calculate(structure)
    return {
        "calculator": cls_name,
        "formula": structure.formula,
        "num_atoms": len(structure),
        "run": run,
        "parameters": calc.get_parameters() if hasattr(calc, "get_parameters") else parameters,
    }


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="list_calculators",
            description="List available MatSimPy calculator classes",
            parameters={"type": "object", "properties": {}, "required": []},
            callable=_list_calculators,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="calculate_lennard_jones",
            description="Calculate Lennard-Jones energy and forces for a structure reference",
            parameters=sig_to_schema(_calculate_lennard_jones),
            callable=_calculate_lennard_jones,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="write_calculator_input",
            description="Write external calculator input files without running external code by default",
            parameters=sig_to_schema(_write_calculator_input),
            callable=_write_calculator_input,
            skill=SKILL_NAME,
        ),
    ]
