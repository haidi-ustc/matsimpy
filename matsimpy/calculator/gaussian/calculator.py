"""Gaussian calculator — ASE-style binding.

Uses the run-mode pipeline from Calculator base class:
  run=True:  write_input → _execute → _parse_output
  run=False: write_input only → user calls read_results()
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import numpy as np

from matsimpy.calculator.base import Calculator
from matsimpy.core import Crystal, Molecule


class GaussianCalculator(Calculator):
    """Gaussian calculator with ASE-style binding.

    Usage::

        mol = Molecule(['O','H','H'], [[0,0,0],[0.96,0,0],[-0.24,0.93,0]])
        calc = GaussianCalculator(
            directory="./g09_calc",
            route="# B3LYP/6-31G(d) Opt Freq",
            charge=0, spin=1,
        )
        mol.calc = calc
        energy = mol.get_potential_energy()
    """

    def __init__(
        self,
        directory: str = "./gaussian_calc",
        route: str = "# B3LYP/6-31G(d)",
        charge: int = 0,
        spin: int = 1,
        gaussian_cmd: str = "g09",
        nproc: int = 1,
        mem: str = "1GB",
        run: bool = True,
    ):
        """Initialize Gaussian calculator.

        Args:
            directory: Working directory for Gaussian files.
            route: Gaussian route line.
            charge: Net charge of the system.
            spin: Spin multiplicity (2S+1).
            gaussian_cmd: Path or name of Gaussian executable.
            nproc: Number of processors.
            mem: Memory allocation.
            run: If True (default), execute Gaussian and parse output.
                 If False, only write input file.
        """
        super().__init__(run=run)
        self.directory = Path(directory)
        self.route = route
        self.charge = charge
        self.spin = spin
        self.gaussian_cmd = gaussian_cmd
        self.nproc = nproc
        self.mem = mem

    def write_input(self, structure: Crystal | Molecule) -> None:
        """Write Gaussian input file (.gjf)."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / "input.gjf"

        lines = [f"%NProcShared={self.nproc}", f"%Mem={self.mem}"]
        lines.append(self.route)
        lines.append("")
        lines.append("MatSimPy Gaussian calculation")
        lines.append("")
        lines.append(f"{self.charge} {self.spin}")

        for species, pos in zip(structure.species, structure.positions):
            lines.append(
                f" {species:2s}  {pos[0]:12.6f}  {pos[1]:12.6f}  {pos[2]:12.6f}"
            )

        lines.append("")
        path.write_text("\n".join(lines))

    def _execute(self) -> None:
        """Run Gaussian executable."""
        input_path = self.directory / "input.gjf"
        output_path = self.directory / "output.log"

        with open(output_path, "w") as f:
            result = subprocess.run(
                [self.gaussian_cmd, str(input_path)],
                cwd=str(self.directory),
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,
            )

        if result.returncode != 0:
            raise RuntimeError(f"Gaussian failed:\n{result.stderr[-500:]}")

    def _parse_output(self) -> None:
        """Parse Gaussian output for energy and forces."""
        path = self.directory / "output.log"
        if not path.exists():
            return

        text = path.read_text()
        import re

        # SCF Done energy
        energy_pattern = r"SCF Done:\s+E\(\w+\)\s+=\s+([-\d.]+)"
        matches = re.findall(energy_pattern, text)
        if matches:
            self.results["energy"] = float(matches[-1])
        else:
            total_pattern = r"Total Energy\s+=\s+([-\d.]+)"
            matches = re.findall(total_pattern, text)
            if matches:
                self.results["energy"] = float(matches[-1])

    def read_results(self) -> None:
        """Parse existing output files (offline mode)."""
        super().read_results()


__all__ = ["GaussianCalculator"]
