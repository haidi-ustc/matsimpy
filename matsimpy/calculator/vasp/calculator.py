"""VASP calculator: ``compute(structure)`` = write_input → run VASP → read_results."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Union

import numpy as np

from matsimpy.calculator.base import FileIOCalculator
from matsimpy.calculator.results import Results
from matsimpy.core import Crystal

_EV_PER_A3_IN_GPA = 160.21766208  # 1 eV/Å^3 = 160.2 GPa


class VaspCalculator(FileIOCalculator):
    """VASP calculator.

    Usage::

        calc = VaspCalculator(directory="./si", incar={"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05})
        r = calc.compute(crystal)                 # runs VASP
        calc.write_input(crystal, "./si_offline") # inputs only
        r = calc.read_results("./si_offline")     # parse a finished run
    """

    def __init__(
        self,
        directory: Union[str, Path] = "./vasp_calc",
        incar: dict | None = None,
        kpoints: list[int] | None = None,
        vasp_cmd: str = "vasp",
        copy_potcar: bool = True,
    ):
        """
        Args:
            directory: Default working directory.
            incar: INCAR parameters. Default: ENCUT=400, ISMEAR=0, SIGMA=0.05.
            kpoints: Monkhorst-Pack mesh [nx, ny, nz]. Default: [1, 1, 1].
            vasp_cmd: VASP executable.
            copy_potcar: Write POTCAR from ``$VASP_PP_PATH`` (set False to skip).
        """
        super().__init__(
            directory,
            incar=dict(incar or {"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05}),
            kpoints=list(kpoints or [1, 1, 1]),
            vasp_cmd=vasp_cmd,
            copy_potcar=copy_potcar,
        )

    def write_input(self, structure: Crystal, directory: Optional[Union[str, Path]] = None) -> Path:
        """Write INCAR, KPOINTS, POSCAR (and POTCAR if ``copy_potcar``)."""
        from .inputs import Incar, Kpoints, Poscar

        directory = self._dir(directory)
        p = self.parameters
        Incar(p["incar"]).write_file(directory / "INCAR")
        mesh = p["kpoints"]
        kpt = Kpoints.automatic(mesh) if isinstance(mesh, list) and len(mesh) == 3 else Kpoints.gamma_automatic(mesh)
        kpt.write_file(directory / "KPOINTS")
        poscar = Poscar(structure)
        poscar.write_file(directory / "POSCAR")
        if p["copy_potcar"]:
            self._write_potcar(poscar, directory)
        return directory

    @staticmethod
    def _write_potcar(poscar, directory: Path) -> None:
        """Write POTCAR by concatenating element POTCARs."""
        from .inputs import Potcar

        if not os.getenv("VASP_PP_PATH"):
            raise RuntimeError(
                "VASP_PP_PATH not set. Set it to your VASP pseudopotential directory, "
                "or use copy_potcar=False."
            )
        Potcar([f"{s}" for s in poscar.site_symbols], functional="PBE").write_file(directory / "POTCAR")

    def _execute(self, directory: Path) -> None:
        result = subprocess.run(
            [self.parameters["vasp_cmd"]], cwd=str(directory),
            capture_output=True, text=True, timeout=3600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"VASP failed:\n{result.stderr[-500:]}")

    def read_results(self, directory: Optional[Union[str, Path]] = None) -> Results:
        """Energy and forces from vasprun.xml, else OUTCAR, else OSZICAR."""
        from .outputs import Outcar, Oszicar, Vasprun

        directory = self.directory if directory is None else Path(directory)
        energy = forces = stress = None

        vasprun_xml = directory / "vasprun.xml"
        outcar_path = directory / "OUTCAR"
        oszicar_path = directory / "OSZICAR"

        if vasprun_xml.exists():
            vasprun = Vasprun(str(vasprun_xml))
            energy = vasprun.final_energy
            if vasprun.ionic_steps:
                # 0.8.x only read forces when force_constants existed (IBRION=5-8),
                # so ordinary static/relax runs returned no forces.
                last = vasprun.ionic_steps[-1]
                forces = last.get("forces")
                if last.get("stress") is not None:
                    # VASP prints stress in kBar with pressure positive; MatSimPy
                    # (like ASE) uses eV/Å^3 with tension positive.
                    stress = -0.1 * np.asarray(last["stress"], dtype=float) / _EV_PER_A3_IN_GPA
        elif outcar_path.exists():
            outcar = Outcar(str(outcar_path))
            energy = outcar.final_energy
            forces = outcar.data.get("forces", {}).get(-1, None)
        elif oszicar_path.exists():
            oszicar = Oszicar(str(oszicar_path))
            if oszicar.ionic_steps:
                energy = oszicar.ionic_steps[-1].get("E0", 0.0)

        return Results(energy=energy, forces=forces, stress=stress)


__all__ = ["VaspCalculator"]
