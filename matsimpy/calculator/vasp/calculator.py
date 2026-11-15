"""VASP calculator: ``compute(structure)`` = write_input → run VASP → read_results."""

from __future__ import annotations

import re
import shlex
import subprocess
import warnings
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np

from matsimpy.calculator.base import FileIOCalculator
from matsimpy.calculator.results import Results
from matsimpy.core import Crystal

_EV_PER_A3_IN_GPA = 160.21766208  # 1 eV/Å^3 = 160.2 GPa
_KBAR_TO_EV_PER_A3 = 0.1 / _EV_PER_A3_IN_GPA

DEFAULT_INPUT_SET = "MPStaticSet"
DEFAULT_POTCAR_FUNCTIONAL = "PBE_54"


class VaspCalculator(FileIOCalculator):
    """VASP calculator built on the Materials Project input sets.

    The INCAR, KPOINTS and POTCAR choices come from an input set of
    :mod:`matsimpy.calculator.vasp.sets` (default ``MPStaticSet``, as in the Materials
    Project); ``incar`` and ``kpoints`` override them.

    Usage::

        calc = VaspCalculator(directory="si", incar={"ENCUT": 400}, kpoints=[4, 4, 4])
        r = calc.compute(crystal)                  # runs VASP
        calc.write_input(crystal, "si_offline")    # inputs only
        r = calc.read_results("si_offline")        # parse a finished run

    POTCARs are read from ``$PMG_VASP_PSP_DIR``, default ``~/.matsimpy/vasp_pp``, laid
    out as ``<dir>/POT_GGA_PAW_PBE_54/POTCAR.Si(.gz)`` or ``<dir>/POT_GGA_PAW_PBE_54/Si/POTCAR``.
    """

    def __init__(
        self,
        directory: Union[str, Path] = "./vasp_calc",
        incar: dict | None = None,
        kpoints: list[int] | dict | None = None,
        input_set: str = DEFAULT_INPUT_SET,
        potcar_functional: str | None = DEFAULT_POTCAR_FUNCTIONAL,
        vasp_cmd: str = "vasp",
        copy_potcar: bool = True,
        timeout: float | None = None,
    ):
        """
        Args:
            directory: Default working directory.
            incar: INCAR tags that override the input set's, e.g. ``{"ENCUT": 400}``.
                A value of ``None`` removes the tag.
            kpoints: A Gamma-centred mesh ``[n1, n2, n3]``, or k-point settings of the input
                set such as ``{"reciprocal_density": 200}``. Default: the input set's.
            input_set: Name of an input set class, e.g. ``"MPStaticSet"``, ``"MPRelaxSet"``,
                ``"MPScanStaticSet"``, ``"MPNonSCFSet"``.
            potcar_functional: POTCAR set, e.g. ``"PBE_54"`` (directory ``POT_GGA_PAW_PBE_54``),
                ``"PBE_64"`` or ``"PBE"`` (the legacy set the Materials Project used).
                ``None`` uses the input set's own choice.
            vasp_cmd: Command that runs VASP, e.g. ``"mpirun -np 16 vasp_std"``.
            copy_potcar: Write the POTCAR. With False, ``POTCAR.spec`` lists the POTCARs
                (e.g. ``Ga_d``) so you can add your own.
            timeout: Seconds before VASP is stopped (default: no limit).
        """
        _input_set_class(input_set)  # unknown names fail here, not at the first calculation
        if kpoints is not None and not isinstance(kpoints, dict):
            kpoints = [int(n) for n in kpoints]
            if len(kpoints) != 3 or min(kpoints) < 1:
                raise ValueError(f"kpoints must be three positive integers, got {kpoints}")
        super().__init__(
            directory,
            incar=dict(incar or {}),
            kpoints=kpoints if not isinstance(kpoints, dict) else dict(kpoints),
            input_set=input_set,
            potcar_functional=potcar_functional,
            vasp_cmd=vasp_cmd,
            copy_potcar=copy_potcar,
            timeout=timeout,
        )

    # -- input ---------------------------------------------------------------------------
    def input_set(self, structure: Crystal):
        """The input set for ``structure``, with this calculator's overrides.

        Atoms are grouped by species in order of first appearance (not sorted by
        electronegativity as the sets would), so ``compute`` can return forces in the
        order of ``structure``.
        """
        from .inputs import Kpoints

        p = self.parameters
        kpoints = p["kpoints"]
        if isinstance(kpoints, list):
            kpoints = Kpoints.gamma_automatic(tuple(kpoints))
        options: dict[str, Any] = {"user_incar_settings": p["incar"], "user_kpoints_settings": kpoints,
                                   "sort_structure": False}
        if p["potcar_functional"]:
            options["user_potcar_functional"] = p["potcar_functional"]
        grouped, _ = _group_by_species(structure)
        with warnings.catch_warnings():
            # choosing the POTCAR set is what ``potcar_functional`` is for; do not warn each time
            warnings.filterwarnings("ignore", "Overriding the POTCAR functional")
            return _input_set_class(p["input_set"])(grouped, **options)

    def write_input(self, structure: Crystal, directory: Optional[Union[str, Path]] = None) -> Path:
        """Write INCAR, KPOINTS, POSCAR and POTCAR (``POTCAR.spec`` if not ``copy_potcar``)."""
        if not isinstance(structure, Crystal):
            raise TypeError(f"VASP needs a Crystal, got {type(structure).__name__}")
        directory = self._dir(directory)
        self.input_set(structure).write_input(directory, potcar_spec=not self.parameters["copy_potcar"])
        return directory

    # -- run -----------------------------------------------------------------------------
    def _calculate(self, structure: Crystal) -> Results:
        directory = self.write_input(structure)
        self._execute(directory)
        results = self.read_results(directory)
        _, order = _group_by_species(structure)
        if results.forces is None or list(order) == list(range(len(order))):
            return results
        forces = np.empty_like(results.forces)
        forces[order] = results.forces  # back to the atom order of ``structure``
        return Results(energy=results.energy, forces=forces, stress=results.stress)

    def _execute(self, directory: Path) -> None:
        command = shlex.split(self.parameters["vasp_cmd"])
        result = subprocess.run(command, cwd=str(directory), capture_output=True, text=True,
                                timeout=self.parameters.get("timeout"))
        if result.returncode != 0:
            output = (result.stdout[-1000:] + "\n" + result.stderr[-1000:]).strip()
            raise RuntimeError(f"VASP failed with exit code {result.returncode}:\n{output}")

    # -- output --------------------------------------------------------------------------
    def read_results(self, directory: Optional[Union[str, Path]] = None) -> Results:
        """Energy, forces and stress from vasprun.xml, else OUTCAR; energy only from OSZICAR.

        Stress is converted from VASP's kBar (pressure positive) to eV/Å^3 (tension
        positive). Forces follow the atom order of the POSCAR in ``directory``.

        Raises:
            FileNotFoundError: If none of the three files is in ``directory``.
        """
        from .outputs import Outcar, Oszicar, Vasprun

        directory = self.directory if directory is None else Path(directory)
        vasprun_xml, outcar_path, oszicar_path = (directory / name for name in ("vasprun.xml", "OUTCAR", "OSZICAR"))

        if vasprun_xml.exists():
            vasprun = Vasprun(str(vasprun_xml))
            if not vasprun.converged_electronic:
                warnings.warn(f"{vasprun_xml}: the last electronic step did not converge (NELM reached)",
                              stacklevel=2)
            last = vasprun.ionic_steps[-1]
            stress = last.get("stress")
            return Results(energy=vasprun.final_energy, forces=last.get("forces"),
                           stress=None if stress is None else -_KBAR_TO_EV_PER_A3 * np.asarray(stress, dtype=float))
        if outcar_path.exists():
            forces, stress = _outcar_forces_and_stress(outcar_path)
            return Results(energy=Outcar(str(outcar_path)).final_energy, forces=forces,
                           stress=None if stress is None else -_KBAR_TO_EV_PER_A3 * stress)
        if oszicar_path.exists():
            return Results(energy=Oszicar(str(oszicar_path)).final_energy)
        raise FileNotFoundError(f"no vasprun.xml, OUTCAR or OSZICAR in {directory}")


def _input_set_class(name: str):
    from . import sets

    cls = getattr(sets, name, None)
    if not (isinstance(cls, type) and issubclass(cls, sets.VaspInputSet)) or cls is sets.VaspInputSet:
        raise ValueError(f"unknown VASP input set {name!r}; e.g. MPStaticSet, MPRelaxSet, MPScanStaticSet")
    return cls


def _group_by_species(structure: Crystal) -> tuple[Crystal, list[int]]:
    """``structure`` with each species' atoms together (first-appearance order), and the order used."""
    from matsimpy.transformation.atomic import sort_atoms

    first: dict[str, int] = {}
    for symbol in structure.species:
        first.setdefault(symbol, len(first))
    order = sorted(range(len(structure)), key=lambda i: first[structure.species[i]])  # stable
    return sort_atoms(structure, key=lambda s, i: first[s.species[i]]), order


_FORCE_HEADER = re.compile(r"POSITION\s+TOTAL-FORCE")
_STRESS_LINE = re.compile(r"^\s*in kB((?:\s+-?\d+\.\d+){6})", re.M)


def _outcar_forces_and_stress(path: Path) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Forces (eV/Å) and stress (kBar, 3x3) of the last ionic step in an OUTCAR."""
    text = Path(path).read_text(errors="replace")
    forces = None
    headers = list(_FORCE_HEADER.finditer(text))
    if headers:
        rows = []
        for line in text[headers[-1].end():].splitlines()[2:]:  # skip the rest of the header and a dash line
            if line.strip().startswith("---"):
                break
            rows.append([float(value) for value in line.split()[3:6]])
        forces = np.array(rows)
    stress = None
    lines = _STRESS_LINE.findall(text)
    if lines:
        xx, yy, zz, xy, yz, zx = (float(value) for value in lines[-1].split())
        stress = np.array([[xx, xy, zx], [xy, yy, yz], [zx, yz, zz]])
    return forces, stress


__all__ = ["VaspCalculator"]
