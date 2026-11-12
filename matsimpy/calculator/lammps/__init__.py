"""LAMMPS calculator — adapted from pymatgen (https://pymatgen.org/).

``LammpsCalculator`` has no third-party requirements.  The file-format classes
(LammpsData, LammpsDump, ...) need the optional ``lammps`` extra
(pandas, ruamel.yaml) and are imported lazily, so ``LammpsCalculator`` keeps
working on a minimal install.
"""
from importlib import import_module

from .calculator import LammpsCalculator

_LAZY_EXPORTS = {
    "LammpsInputFile": ".inputs",
    "LammpsRun": ".inputs",
    "LammpsData": ".data",
    "LammpsBox": ".data",
    "CombinedData": ".data",
    "ForceField": ".data",
    "LammpsDump": ".outputs",
    "parse_lammps_dumps": ".outputs",
    "parse_lammps_log": ".outputs",
}


def __getattr__(name):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        module = import_module(_LAZY_EXPORTS[name], __name__)
    except ImportError as exc:
        raise ImportError(
            f"matsimpy.calculator.lammps.{name} requires the optional 'lammps' extra: "
            "pip install 'MatSimPy[lammps]'"
        ) from exc
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = ["LammpsInputFile", "LammpsRun", "LammpsData", "LammpsBox",
           "CombinedData", "ForceField", "LammpsDump",
           "parse_lammps_dumps", "parse_lammps_log", "LammpsCalculator"]
