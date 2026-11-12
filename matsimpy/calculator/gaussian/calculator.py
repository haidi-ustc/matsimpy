"""Gaussian calculator: ``compute(structure)`` = write_input → run Gaussian → read_results."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional, Union

from matsimpy.calculator.base import FileIOCalculator
from matsimpy.calculator.results import Results
from matsimpy.core import Crystal, Molecule

_HARTREE_TO_EV = 27.211386245988


class GaussianCalculator(FileIOCalculator):
    """Gaussian calculator (writes ``input.gjf``, reads ``output.log``).

    Usage::

        calc = GaussianCalculator(directory="./h2o", route="# B3LYP/6-31G(d)", charge=0, spin=1)
        r = calc.compute(molecule)
        calc.write_input(molecule, "./offline"); r = calc.read_results("./offline")
    """

    def __init__(
        self,
        directory: Union[str, Path] = "./gaussian_calc",
        route: str = "# B3LYP/6-31G(d)",
        charge: int = 0,
        spin: int = 1,
        gaussian_cmd: str = "g09",
        nproc: int = 1,
        mem: str = "1GB",
    ):
        """
        Args:
            directory: Default working directory.
            route: Gaussian route line.
            charge: Net charge.
            spin: Spin multiplicity (2S+1).
            gaussian_cmd: Gaussian executable.
            nproc: ``%NProcShared``.
            mem: ``%Mem``.
        """
        super().__init__(directory, route=route, charge=charge, spin=spin,
                         gaussian_cmd=gaussian_cmd, nproc=nproc, mem=mem)

    def write_input(self, structure: Crystal | Molecule, directory: Optional[Union[str, Path]] = None) -> Path:
        """Write ``input.gjf`` (Cartesian coordinates)."""
        directory = self._dir(directory)
        p = self.parameters
        lines = [f"%NProcShared={p['nproc']}", f"%Mem={p['mem']}", p["route"], "",
                 "MatSimPy Gaussian calculation", "", f"{p['charge']} {p['spin']}"]
        for species, pos in zip(structure.species, structure.positions):
            lines.append(f" {species:2s}  {pos[0]:12.6f}  {pos[1]:12.6f}  {pos[2]:12.6f}")
        lines.append("")
        (directory / "input.gjf").write_text("\n".join(lines))
        return directory

    def _execute(self, directory: Path) -> None:
        with open(directory / "output.log", "w") as f:
            result = subprocess.run(
                [self.parameters["gaussian_cmd"], str(directory / "input.gjf")],
                cwd=str(directory), stdout=f, stderr=subprocess.PIPE, text=True, timeout=3600,
            )
        if result.returncode != 0:
            raise RuntimeError(f"Gaussian failed:\n{result.stderr[-500:]}")

    def read_results(self, directory: Optional[Union[str, Path]] = None) -> Results:
        """Last ``SCF Done`` energy (else ``Total Energy``) from ``output.log``, in eV."""
        path = (self.directory if directory is None else Path(directory)) / "output.log"
        if not path.exists():
            raise FileNotFoundError(f"Gaussian output not found: {path}")
        text = path.read_text()
        matches = re.findall(r"SCF Done:\s+E\(\w+\)\s+=\s+([-\d.]+)", text) or re.findall(
            r"Total Energy\s+=\s+([-\d.]+)", text
        )
        energy = float(matches[-1]) * _HARTREE_TO_EV if matches else None
        return Results(energy=energy, extra={"energy_hartree": float(matches[-1])} if matches else {})


__all__ = ["GaussianCalculator"]
