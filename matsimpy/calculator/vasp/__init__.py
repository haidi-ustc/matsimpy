"""VASP calculator — adapted from pymatgen (https://pymatgen.org/).

Original: pymatgen.io.vasp
Copyright (c) pymatgen Development Team. MIT License.
Modifications for MatSimPy integration.

Provides:
- Input file classes: Incar, Kpoints, Poscar, Potcar
- Output file classes: Outcar, Vasprun, Oszicar, Chgcar, Locpot, etc.
- Input sets: VaspInputSet, DictSet
- Calculator driver: VaspCalculator
"""

from .inputs import Incar, Kpoints, Poscar, Potcar, PotcarSingle, VaspInput
from .outputs import Outcar, Vasprun, Oszicar, Chgcar, Locpot, Wavecar, Elfcar, Procar
from .sets import VaspInputSet, DictSet
from .calculator import VaspCalculator

__all__ = [
    "Incar", "Kpoints", "Poscar", "Potcar", "PotcarSingle",
    "Outcar", "Vasprun", "Oszicar", "Chgcar", "Locpot", "Wavecar",
    "Elfcar", "Procar", "VaspInput", "VaspInputSet", "DictSet",
    "VaspCalculator",
]
