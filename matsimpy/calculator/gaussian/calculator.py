"""Gaussian calculator — ASE-style binding."""

from __future__ import annotations
import os, subprocess
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
    ):
        super().__init__()
        self.directory = Path(directory)
        self.route = route
        self.charge = charge
        self.spin = spin
        self.gaussian_cmd = gaussian_cmd
        self.nproc = nproc
        self.mem = mem

    def write_input(self, structure: Crystal | Molecule) -> str:
        """Write Gaussian input file (.gjf). Returns path."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / "input.gjf"

        lines = [f"%NProcShared={self.nproc}", f"%Mem={self.mem}"]
        lines.append(self.route)
        lines.append("")
        lines.append(f"MatSimPy Gaussian calculation")
        lines.append("")
        lines.append(f"{self.charge} {self.spin}")

        for species, pos in zip(structure.species, structure.positions):
            lines.append(f" {species:2s}  {pos[0]:12.6f}  {pos[1]:12.6f}  {pos[2]:12.6f}")

        lines.append("")
        path.write_text("\n".join(lines))
        return str(path)

    def _compute(self) -> None:
        """Run Gaussian: write input → execute → parse output."""
        input_path = self.write_input(self.structure)
        output_path = self.directory / "output.log"

        with open(output_path, "w") as f:
            result = subprocess.run(
                [self.gaussian_cmd, input_path],
                cwd=str(self.directory),
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,
            )

        if result.returncode != 0:
            raise RuntimeError(f"Gaussian failed:\n{result.stderr[-500:]}")

        self._parse_output(output_path)

    def _parse_output(self, path: Path) -> None:
        """Parse Gaussian output for energy and forces."""
        text = path.read_text()
        import re
        energy_pattern = r"SCF Done:\s+E\(\w+\)\s+=\s+([-\d.]+)"
        matches = re.findall(energy_pattern, text)
        if matches:
            self.results["energy"] = float(matches[-1])
        else:
            total_pattern = r"Total Energy\s+=\s+([-\d.]+)"
            matches = re.findall(total_pattern, text)
            if matches:
                self.results["energy"] = float(matches[-1])

    def get_potential_energy(self) -> float:
        return self.results.get("energy", None)

    def get_forces(self) -> np.ndarray:
        return self.results.get("forces", None)


__all__ = ["GaussianCalculator"]
