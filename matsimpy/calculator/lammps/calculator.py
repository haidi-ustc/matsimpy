"""LAMMPS calculator — ASE-style binding.

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
from matsimpy.core import Crystal, Molecule, SymmOp
from matsimpy.core.periodic_table import Element


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
        run: bool = True,
    ):
        """Initialize LAMMPS calculator.

        Args:
            directory: Working directory for LAMMPS files.
            pair_style: LAMMPS pair_style command.
            pair_coeff: LAMMPS pair_coeff command.
            lammps_cmd: Path or name of LAMMPS executable.
            units: LAMMPS units style.
            run: If True (default), execute LAMMPS and parse output.
                 If False, only write input files.
        """
        super().__init__(run=run)
        self.directory = Path(directory)
        self.pair_style = pair_style
        self.pair_coeff = pair_coeff
        self.lammps_cmd = lammps_cmd
        self.units = units

    @staticmethod
    def _atom_type_map(structure: Crystal | Molecule) -> dict[str, int]:
        """Map species symbols to stable LAMMPS atom type ids."""
        return {symbol: i for i, symbol in enumerate(structure.symbol_set, start=1)}

    @staticmethod
    def _crystal_box_and_transform(structure: Crystal) -> tuple[list[str], SymmOp]:
        matrix = structure.lattice.matrix
        a, b, c = np.linalg.norm(matrix, axis=1)
        xlo = ylo = zlo = 0.0
        xhi = a
        xy = float(np.dot(matrix[1], matrix[0] / a))
        yhi = float(np.sqrt(b**2 - xy**2))
        xz = float(np.dot(matrix[2], matrix[0] / a))
        yz = float((np.dot(matrix[1], matrix[2]) - xy * xz) / yhi)
        zhi = float(np.sqrt(c**2 - xz**2 - yz**2))

        lines = [
            f"{xlo:.6f} {xhi:.6f} xlo xhi",
            f"{ylo:.6f} {yhi:.6f} ylo yhi",
            f"{zlo:.6f} {zhi:.6f} zlo zhi",
        ]
        if not structure.lattice.is_orthogonal():
            lines.append(f"{xy:.6f} {xz:.6f} {yz:.6f} xy xz yz")

        lammps_matrix = [[xhi - xlo, 0, 0], [xy, yhi - ylo, 0], [xz, yz, zhi - zlo]]
        rot_matrix = np.linalg.solve(lammps_matrix, matrix)
        symm_op = SymmOp.from_rotation_and_translation(rot_matrix, [0, 0, 0])
        return lines, symm_op

    @staticmethod
    def _lammps_positions(structure: Crystal | Molecule) -> np.ndarray:
        if not isinstance(structure, Crystal):
            return np.asarray(structure.positions, dtype=float)

        _box_lines, symm_op = LammpsCalculator._crystal_box_and_transform(structure)
        return np.array([symm_op.operate(pos) for pos in structure.cart_positions])

    @staticmethod
    def _box_lines(structure: Crystal | Molecule) -> list[str]:
        if isinstance(structure, Crystal):
            box_lines, _symm_op = LammpsCalculator._crystal_box_and_transform(structure)
            return box_lines

        max_coord = np.max(np.abs(structure.positions)) * 2
        return [
            f"{-max_coord:.1f} {max_coord:.1f} xlo xhi",
            f"{-max_coord:.1f} {max_coord:.1f} ylo yhi",
            f"{-max_coord:.1f} {max_coord:.1f} zlo zhi",
        ]

    def write_input(self, structure: Crystal | Molecule) -> None:
        """Write LAMMPS input and data files."""
        self.directory.mkdir(parents=True, exist_ok=True)

        n_atoms = len(structure)
        is_periodic = isinstance(structure, Crystal)
        atom_types = self._atom_type_map(structure)
        positions = self._lammps_positions(structure)

        # Data file
        data_lines = [
            "LAMMPS data file — MatSimPy",
            "",
            f"{n_atoms} atoms",
            "0 bonds",
            "0 angles",
            "0 dihedrals",
            "0 impropers",
            "",
            f"{len(atom_types)} atom types",
            "",
        ]

        data_lines.extend(self._box_lines(structure))

        data_lines.extend(["", "Masses", ""])
        for symbol, type_id in atom_types.items():
            data_lines.append(f"{type_id} {Element(symbol).atomic_mass:.6g}")

        data_lines.extend(["", "Atoms", ""])
        for i, (species, pos) in enumerate(zip(structure.species, positions), 1):
            type_id = atom_types[species]
            data_lines.append(
                f"{i} {type_id} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}"
            )

        (self.directory / "data.lammps").write_text("\n".join(data_lines))

        # Input script
        boundary = "p p p" if is_periodic else "f f f"
        input_lines = [
            f"units {self.units}",
            "atom_style atomic",
            f"boundary {boundary}",
            "read_data data.lammps",
            f"pair_style {self.pair_style}",
            f"pair_coeff {self.pair_coeff}",
            "thermo 1",
            "thermo_style custom step pe ke etotal temp press",
            "run 0",
        ]
        (self.directory / "in.lammps").write_text("\n".join(input_lines))

    def _execute(self) -> None:
        """Run LAMMPS executable."""
        result = subprocess.run(
            [self.lammps_cmd, "-in", "in.lammps"],
            cwd=str(self.directory),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"LAMMPS failed:\n{result.stderr[-500:]}")

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

    def read_results(self) -> None:
        """Parse existing output files (offline mode)."""
        super().read_results()


__all__ = ["LammpsCalculator"]
