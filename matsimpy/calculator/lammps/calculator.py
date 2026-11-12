"""LAMMPS calculator: ``compute(structure)`` = write_input → run LAMMPS (``run 0``) → read_results."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional, Union

import numpy as np

from matsimpy.calculator.base import FileIOCalculator
from matsimpy.calculator.results import Results
from matsimpy.core import Crystal, Element, Molecule


class LammpsCalculator(FileIOCalculator):
    """LAMMPS single-point calculator (writes ``data.lammps`` + ``in.lammps``, reads ``log.lammps``).

    Usage::

        calc = LammpsCalculator(directory="./ar", pair_style="lj/cut 10.0", pair_coeff="* * 0.0103 3.40")
        r = calc.compute(crystal)
    """

    def __init__(
        self,
        directory: Union[str, Path] = "./lammps_calc",
        pair_style: str = "lj/cut 10.0",
        pair_coeff: str = "* * 1.0 1.0",
        lammps_cmd: str = "lmp_serial",
        units: str = "metal",
    ):
        """
        Args:
            directory: Default working directory.
            pair_style: LAMMPS ``pair_style`` command.
            pair_coeff: LAMMPS ``pair_coeff`` command.  Atom types are numbered
                1..n in order of first appearance of each element
                (``structure.symbol_set``), e.g. ``* * file.eam.alloy Na Cl``.
            lammps_cmd: LAMMPS executable.
            units: LAMMPS units style (energies are eV only for ``metal``).
        """
        super().__init__(directory, pair_style=pair_style, pair_coeff=pair_coeff,
                         lammps_cmd=lammps_cmd, units=units)

    def write_input(self, structure: Crystal | Molecule, directory: Optional[Union[str, Path]] = None) -> Path:
        """Write ``data.lammps`` and ``in.lammps``."""
        directory = self._dir(directory)
        p = self.parameters
        n_atoms = len(structure)
        is_periodic = isinstance(structure, Crystal)

        # One LAMMPS atom type per element, numbered in order of first
        # appearance (structure.symbol_set).  0.8.1 wrote every atom as type 1
        # with mass 1.0, silently treating e.g. NaCl as a one-component system.
        type_symbols = list(structure.symbol_set)
        type_of = {sym: i for i, sym in enumerate(type_symbols, 1)}

        data_lines = [
            "LAMMPS data file — MatSimPy",
            "",
            f"{n_atoms} atoms",
            "0 bonds",
            "0 angles",
            "0 dihedrals",
            "0 impropers",
            "",
            f"{len(type_symbols)} atom types",
            "",
        ]

        if is_periodic:
            # LAMMPS restricted-triclinic cell: a along x, b in the xy plane.
            # Positions are mapped through fractional coordinates, so the cell
            # rotation is exact; 0.8.1 wrote only |a|,|b|,|c| and the original
            # Cartesian positions, which is wrong for any non-orthogonal cell.
            m = structure.lattice.matrix
            lx = np.linalg.norm(m[0])
            xy = m[1] @ m[0] / lx
            xz = m[2] @ m[0] / lx
            ly = np.sqrt(m[1] @ m[1] - xy**2)
            yz = (m[1] @ m[2] - xy * xz) / ly
            lz = np.sqrt(m[2] @ m[2] - xz**2 - yz**2)
            lmp_cell = np.array([[lx, 0.0, 0.0], [xy, ly, 0.0], [xz, yz, lz]])
            frac = np.array(structure.frac_positions)
            periodic_axes = np.array(structure.pbc, dtype=bool)
            frac[:, periodic_axes] %= 1.0  # LAMMPS requires atoms inside periodic box
            positions = frac @ lmp_cell
            data_lines.append(f"0.0 {lx:.12f} xlo xhi")
            data_lines.append(f"0.0 {ly:.12f} ylo yhi")
            data_lines.append(f"0.0 {lz:.12f} zlo zhi")
            if not structure.lattice.is_orthogonal():
                data_lines.append(f"{xy:.12f} {xz:.12f} {yz:.12f} xy xz yz")
        else:
            positions = structure.positions
            max_coord = np.max(np.abs(positions)) * 2 if n_atoms else 1.0
            max_coord = max(max_coord, 1.0)
            data_lines.extend(
                [
                    f"{-max_coord:.6f} {max_coord:.6f} xlo xhi",
                    f"{-max_coord:.6f} {max_coord:.6f} ylo yhi",
                    f"{-max_coord:.6f} {max_coord:.6f} zlo zhi",
                ]
            )

        data_lines.extend(["", "Masses", ""])
        for sym, type_id in type_of.items():
            data_lines.append(f"{type_id} {Element(sym).atomic_mass:.6f}  # {sym}")
        data_lines.extend(["", "Atoms  # atomic", ""])
        for i, (species, pos) in enumerate(zip(structure.species, positions), 1):
            data_lines.append(f"{i} {type_of[species]} {pos[0]:.12f} {pos[1]:.12f} {pos[2]:.12f}")

        (directory / "data.lammps").write_text("\n".join(data_lines))

        # Input script
        if is_periodic:
            boundary = " ".join("p" if flag else "s" for flag in structure.pbc)
        else:
            boundary = "f f f"
        input_lines = [
            f"units {p['units']}",
            "atom_style atomic",
            f"boundary {boundary}",
            "read_data data.lammps",
            f"pair_style {p['pair_style']}",
            f"pair_coeff {p['pair_coeff']}",
            "thermo 1",
            "thermo_style custom step pe ke etotal temp press",
            "run 0",
        ]
        (directory / "in.lammps").write_text("\n".join(input_lines))
        return directory

    def _execute(self, directory: Path) -> None:
        result = subprocess.run(
            [self.parameters["lammps_cmd"], "-in", "in.lammps"],
            cwd=str(directory), capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"LAMMPS failed:\n{result.stderr[-500:]}")

    def read_results(self, directory: Optional[Union[str, Path]] = None) -> Results:
        """Potential energy (``pe`` column) of the last thermo line in ``log.lammps``."""
        path = (self.directory if directory is None else Path(directory)) / "log.lammps"
        if not path.exists():
            raise FileNotFoundError(f"LAMMPS log not found: {path}")
        pattern = r"^\s*\d+\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)"
        matches = list(re.finditer(pattern, path.read_text(), re.MULTILINE))
        # thermo_style: step pe ke etotal temp press.  0.8.x returned etotal
        # (equal to pe only because ``run 0`` has no velocities).
        return Results(energy=float(matches[-1].group(1)) if matches else None)


__all__ = ["LammpsCalculator"]
