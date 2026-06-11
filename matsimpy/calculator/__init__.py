"""
Calculator module for MatSimPy.

Provides calculators for computing energies, forces, and other properties.
- lj: Lennard-Jones classical potential
- mattersim: MatterSim ML potential (requires torch)
- vasp: VASP DFT calculator (adapted from pymatgen)
- gaussian: Gaussian calculator (adapted from pymatgen)
- lammps: LAMMPS calculator (adapted from pymatgen)
"""

from .base import Calculator
from .lj import LennardJones

_LAZY_EXPORTS = {
    "Mattersim": (".mattersim", "Mattersim"),
    "VaspCalculator": (".vasp", "VaspCalculator"),
    "GaussianCalculator": (".gaussian", "GaussianCalculator"),
    "LammpsCalculator": (".lammps", "LammpsCalculator"),
}


def __getattr__(name):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    from importlib import import_module

    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

__all__ = [
    "Calculator",
    "LennardJones",
    "Mattersim",
    "VaspCalculator",
    "GaussianCalculator",
    "LammpsCalculator",
]
