"""LAMMPS calculator — ASE-style binding."""

from __future__ import annotations
import os, subprocess
from pathlib import Path
from typing import Optional

import numpy as np

from matsimpy.calculator.base import Calculator
from matsimpy.core import Crystal, Molecule


class LammpsCalculator(Calculator):
    """LAMMPS calculator with ASE-style binding.

    Usage::

        crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.26))
        calc = LammpsCalculator(
            directory="./lammps_calc",
            pair_style="lj/cut 10.0",
            pair_coeff="* * 0.0103 3.40",
        )
        crystal.calc = calc
        energy = crystal.get_potential_energy()
    """

    def __init__(
        self,
        directory: str = "./lammps_calc",
        pair_style: str = "lj/cut 10.0",
        pair_coeff: str = "* * 1.0 1.0",
        lammps_cmd: str = "lmp_serial",
        units: str = "metal",
    ):
        super().__init__()
        self.directory = Path(directory)
        self.pair_style = pair_style
        self.pair_coeff = pair_coeff
        self.lammps_cmd = lammps_cmd
        self.units = units

    def write_input(self, structure: Crystal | Molecule) -> None:
        """Write LAMMPS input and data files."""
        self.directory.mkdir(parents=True, exist_ok=True)

        n_atoms = len(structure)
        is_periodic = isinstance(structure, Crystal)

        # Data file
        data_lines = [f"LAMMPS data file — MatSimPy", f"", f"{n_atoms} atoms", f"0 bonds", f"0 angles",
                      f"0 dihedrals", f"0 impropers", f"", f"1 atom types", f""]

        if is_periodic:
            data_lines.append(f"0.0 {structure.lattice.a:.6f} xlo xhi")
            data_lines.append(f"0.0 {structure.lattice.b:.6f} ylo yhi")
            data_lines.append(f"0.0 {structure.lattice.c:.6f} zlo zhi")
        else:
            max_coord = np.max(np.abs(structure.positions)) * 2
            data_lines.extend([f"{-max_coord:.1f} {max_coord:.1f} xlo xhi",
                               f"{-max_coord:.1f} {max_coord:.1f} ylo yhi",
                               f"{-max_coord:.1f} {max_coord:.1f} zlo zhi"])

        data_lines.extend(["", "Masses", "", "1 1.0", "", "Atoms", ""])
        for i, (species, pos) in enumerate(zip(structure.species, structure.positions), 1):
            data_lines.append(f"{i} 1 {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}")

        (self.directory / "data.lammps").write_text("\n".join(data_lines))

        # Input script
        boundary = "p p p" if is_periodic else "f f f"
        input_lines = [
            f"units {self.units}",
            f"atom_style atomic",
            f"boundary {boundary}",
            f"read_data data.lammps",
            f"pair_style {self.pair_style}",
            f"pair_coeff {self.pair_coeff}",
            f"thermo 1",
            f"thermo_style custom step pe ke etotal temp press",
            f"run 0",
        ]
        (self.directory / "in.lammps").write_text("\n".join(input_lines))

    def _compute(self) -> None:
        """Run LAMMPS: write input → execute → parse output."""
        self.write_input(self.structure)

        result = subprocess.run(
            [self.lammps_cmd, "-in", "in.lammps"],
            cwd=str(self.directory),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"LAMMPS failed:\n{result.stderr[-500:]}")

        self._parse_output()

    def _parse_output(self) -> None:
        """Parse LAMMPS log for energy."""
        log_path = self.directory / "log.lammps"
        if not log_path.exists():
            return

        text = log_path.read_text()
        import re
        pattern = r"^\s*\d+\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)"
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        if matches:
            last = matches[-1].groups()
            self.results["energy"] = float(last[2])  # etotal column

    def get_potential_energy(self) -> float:
        return self.results.get("energy", None)

    def get_forces(self) -> np.ndarray:
        return self.results.get("forces", None)


__all__ = ["LammpsCalculator"]
