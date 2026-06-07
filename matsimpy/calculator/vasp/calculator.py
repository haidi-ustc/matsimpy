"""VASP calculator — ASE-style binding.

Uses the run-mode pipeline from Calculator base class:
  run=True:  write_input → _execute → _parse_output
  run=False: write_input only → user calls read_results()
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np

from matsimpy.calculator.base import Calculator
from matsimpy.core import Crystal


class VaspCalculator(Calculator):
    """VASP calculator with ASE-style binding.

    Usage::

        crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        calc = VaspCalculator(
            directory="./si_calc",
            incar={"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05},
        )
        crystal.calc = calc
        energy = crystal.get_potential_energy()
        forces = crystal.get_forces()
    """

    def __init__(
        self,
        directory: str = "./vasp_calc",
        incar: dict | None = None,
        kpoints: list[int] | None = None,
        vasp_cmd: str = "vasp",
        copy_potcar: bool = True,
        run: bool = True,
    ):
        """Initialize VASP calculator.

        Args:
            directory: Working directory for VASP files.
            incar: INCAR parameters dict. Defaults: ENCUT=400, ISMEAR=0.
            kpoints: K-point mesh [nx, ny, nz]. Default: [1, 1, 1].
            vasp_cmd: Path or name of VASP executable.
            copy_potcar: If True, copy POTCAR from VASP_PP_PATH env var.
            run: If True (default), execute VASP and parse output.
                 If False, only write input files.
        """
        super().__init__(run=run)
        self.directory = Path(directory)
        self.incar_params = incar or {"ENCUT": 400, "ISMEAR": 0, "SIGMA": 0.05}
        self.kpoints_grid = kpoints or [1, 1, 1]
        self.vasp_cmd = vasp_cmd
        self.copy_potcar = copy_potcar

    def write_input(self, structure: Crystal) -> None:
        """Write VASP input files (INCAR, KPOINTS, POSCAR, POTCAR) to directory."""
        self.directory.mkdir(parents=True, exist_ok=True)

        from .inputs import Incar, Kpoints, Poscar

        # INCAR
        incar = Incar(self.incar_params)
        incar.write_file(self.directory / "INCAR")

        # KPOINTS
        if isinstance(self.kpoints_grid, list) and len(self.kpoints_grid) == 3:
            kpt = Kpoints.automatic(self.kpoints_grid)
        else:
            kpt = Kpoints.gamma_automatic(self.kpoints_grid)
        kpt.write_file(self.directory / "KPOINTS")

        # POSCAR
        poscar = Poscar(structure)
        poscar.write_file(self.directory / "POSCAR")

        # POTCAR — requires VASP_PP_PATH env var
        if self.copy_potcar and self.run:
            self._write_potcar(poscar)

    def _write_potcar(self, poscar) -> None:
        """Write POTCAR by concatenating element POTCARs."""
        from .inputs import Potcar

        pp_path = os.getenv("VASP_PP_PATH")
        if not pp_path:
            raise RuntimeError(
                "VASP_PP_PATH not set. Set it to your VASP pseudopotential directory, "
                "or use copy_potcar=False."
            )

        species = list(set(poscar.site_symbols))
        potcar_symbols = [f"{s}" for s in species]
        potcar = Potcar(potcar_symbols, functional="PBE")
        potcar.write_file(self.directory / "POTCAR")

    def _execute(self) -> None:
        """Run VASP executable."""
        result = subprocess.run(
            [self.vasp_cmd],
            cwd=str(self.directory),
            capture_output=True,
            text=True,
            timeout=3600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"VASP failed:\n{result.stderr[-500:]}")

    def _parse_output(self) -> None:
        """Parse VASP output files for energy, forces, stress."""
        from .outputs import Outcar, Oszicar, Vasprun

        energy = forces = stress = None

        vasprun_xml = self.directory / "vasprun.xml"
        outcar_path = self.directory / "OUTCAR"
        oszicar_path = self.directory / "OSZICAR"

        if vasprun_xml.exists():
            vasprun = Vasprun(str(vasprun_xml))
            energy = vasprun.final_energy
            if hasattr(vasprun, "force_constants") and vasprun.force_constants is not None and len(vasprun.ionic_steps) > 0:
                forces = vasprun.ionic_steps[-1].get("forces", None)
        elif outcar_path.exists():
            outcar = Outcar(str(outcar_path))
            energy = outcar.final_energy
            forces = outcar.data.get("forces", {}).get(-1, None)
        elif oszicar_path.exists():
            oszicar = Oszicar(str(oszicar_path))
            if oszicar.ionic_steps:
                energy = oszicar.ionic_steps[-1].get("E0", 0.0)

        if energy is not None:
            self.results["energy"] = float(energy)
        if forces is not None:
            self.results["forces"] = np.array(forces)
        if stress is not None:
            self.results["stress"] = np.array(stress)

    def read_results(self) -> None:
        """Parse existing output files (offline mode)."""
        super().read_results()


__all__ = ["VaspCalculator"]
