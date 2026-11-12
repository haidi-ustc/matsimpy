"""Every public subpackage must import on a minimal install (0.8.2 regression).

0.8.1 required undeclared packages at import time: ``import matsimpy.builders``
needed spglib, ``matsimpy.calculator.vasp`` needed tqdm and
``matsimpy.calculator.lammps`` needed pandas.  Run this file in a clean venv
with only the core dependencies to reproduce; in a full dev environment it
still checks that every module imports and that packaged data files exist.
"""

import importlib
import pkgutil
from pathlib import Path

import pytest

import matsimpy

# Subpackages that legitimately require an optional extra.
OPTIONAL = {
    "matsimpy.ai": "ai",
    "matsimpy.calculator.mattersim": "ml",
    "matsimpy.storage.maggma_store": "storage",
}
OPTIONAL_LAMMPS_FORMATS = ("data", "inputs", "outputs", "generators", "sets", "utils")
# lammps.sets / lammps.generators subclass pymatgen.io.core classes
OPTIONAL_PYMATGEN = ("matsimpy.calculator.lammps.sets", "matsimpy.calculator.lammps.generators")


def _modules():
    for info in pkgutil.walk_packages(matsimpy.__path__, "matsimpy.", onerror=lambda name: None):
        yield info.name


def _optional_extra(name):
    extra = next((v for k, v in OPTIONAL.items() if name.startswith(k)), None)
    if extra is None and name.startswith("matsimpy.calculator.lammps.") and name.rsplit(".", 1)[1] in OPTIONAL_LAMMPS_FORMATS:
        extra = "lammps"
    if extra is None and name in OPTIONAL_PYMATGEN:
        extra = "io"
    return extra


def test_every_module_imports():
    """One test for all modules (0.8.2 parametrised this into ~180 test items)."""
    failures = []
    for name in sorted(_modules()):
        try:
            importlib.import_module(name)
        except ImportError as exc:
            if _optional_extra(name) is None:
                failures.append(f"{name}: {exc!r}")
    assert not failures, "\n".join(failures)


CORE_SUBPACKAGES = (
    "matsimpy.core",
    "matsimpy.io",
    "matsimpy.builders",
    "matsimpy.transformation",
    "matsimpy.analysis",
    "matsimpy.symmetry",
    "matsimpy.calculator",
    "matsimpy.calculator.vasp",
    "matsimpy.calculator.gaussian",
    "matsimpy.electronic_structure",
)


def test_core_subpackages_need_no_extras():
    for name in CORE_SUBPACKAGES:
        importlib.import_module(name)


def test_lammps_calculator_needs_no_extras():
    from matsimpy.calculator.lammps import LammpsCalculator  # noqa: F401


PACKAGED_DATA = (
    "core/periodic_table.json",
    "calculator/vasp/incar_parameters.json",
    "calculator/vasp/MPRelaxSet.yaml",
    "calculator/vasp/VASPIncarBase.yaml",
    "calculator/lammps/CoeffsDataType.yaml",
)


def test_packaged_data_files_present():
    root = Path(matsimpy.__file__).parent
    if not (root / "calculator/vasp/incar_parameters.json").exists():
        pytest.skip("repository VASP data files not present in this checkout")
    missing = [rel for rel in PACKAGED_DATA if not (root / rel).is_file()]
    assert not missing, missing
