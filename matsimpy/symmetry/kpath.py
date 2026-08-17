"""Native high-symmetry k-path generation for limited lattice families."""

from __future__ import annotations

import numpy as np

from matsimpy.core import Crystal
from matsimpy.symmetry.analyzer import SymmetryAnalyzer


_PRIMITIVE_CUBIC_KPATH = {
    "kpoints": {
        "Γ": [0.0, 0.0, 0.0],
        "X": [0.0, 0.5, 0.0],
        "M": [0.5, 0.5, 0.0],
        "R": [0.5, 0.5, 0.5],
    },
    "path": [["Γ", "X", "M", "Γ", "R", "X"], ["M", "R"]],
    "provenance": "native primitive-cubic table",
}


class HighSymmetryKpath:
    """High-symmetry path service backed by native symmetry classification."""

    def __init__(self, crystal: Crystal, symprec: float = 1e-5) -> None:
        self.crystal = crystal
        self.symprec = symprec
        analyzer = SymmetryAnalyzer(crystal, symprec=symprec)
        symmetry = analyzer.analyze_crystal(crystal)
        self.crystal_system = symmetry.get("crystal_system")

        if self.crystal_system != "Cubic":
            raise NotImplementedError(
                "HighSymmetryKpath only supports the native primitive-cubic "
                f"path table; detected crystal system: {self.crystal_system}"
            )

        self.kpath = {
            "kpoints": {
                label: list(coords)
                for label, coords in _PRIMITIVE_CUBIC_KPATH["kpoints"].items()
            },
            "path": [list(segment) for segment in _PRIMITIVE_CUBIC_KPATH["path"]],
            "provenance": _PRIMITIVE_CUBIC_KPATH["provenance"],
        }

    def get_kpoints(
        self,
        line_density: int = 20,
        coords_are_cartesian: bool = False,
    ) -> tuple[list[list[float]], list[str]]:
        """Return interpolated k-points and endpoint labels for the native path."""
        if line_density < 1:
            raise ValueError("line_density must be a positive integer")

        kpoints: list[list[float]] = []
        labels: list[str] = []
        for path in self.kpath["path"]:
            for start_label, end_label in zip(path[:-1], path[1:]):
                start = np.array(self.kpath["kpoints"][start_label], dtype=float)
                end = np.array(self.kpath["kpoints"][end_label], dtype=float)
                for index in range(line_density + 1):
                    if kpoints and index == 0:
                        continue
                    fraction = index / line_density
                    point = (1.0 - fraction) * start + fraction * end
                    if coords_are_cartesian:
                        point = (
                            point
                            @ self.crystal.lattice.get_reciprocal_lattice().matrix
                        )
                    if index == 0:
                        label = start_label
                    elif index == line_density:
                        label = end_label
                    else:
                        label = ""
                    kpoints.append(point.tolist())
                    labels.append(label)

        return kpoints, labels
