"""Space-group services backed by the optional :mod:`spglib` package."""

from collections import Counter
from typing import Sequence, Tuple

import numpy as np

from ..core import Crystal, Element, Lattice

try:
    import spglib
except ImportError:  # pragma: no cover - environment dependent
    spglib = None


_SPGLIB_ERROR = (
    "spglib is required for crystal space-group services. "
    "Install it with: pip install spglib"
)


def _require_spglib():
    if spglib is None:
        raise ImportError(_SPGLIB_ERROR)


def _atomic_number(species: str) -> int:
    try:
        return int(Element.get_element(str(species)).atomic_no)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(
            "spglib symmetry services require real chemical-element species; "
            "got {!r}".format(species)
        ) from exc


def _cell(structure: Crystal):
    if not isinstance(structure, Crystal):
        raise TypeError("structure must be a matsimpy Crystal")
    return (
        np.asarray(structure.lattice.matrix, dtype=float),
        np.asarray(structure.frac_positions, dtype=float),
        np.asarray([_atomic_number(s) for s in structure.species], dtype=int),
    )


class SpacegroupAnalyzer:
    """Analyze and standardize a :class:`~matsimpy.core.Crystal`."""

    def __init__(self, structure, symprec=0.01, angle_tolerance=5.0):
        self.structure = structure
        self.symprec = float(symprec)
        self.angle_tolerance = float(angle_tolerance)

    def _standardize(self, to_primitive: bool) -> Crystal:
        _require_spglib()
        result = spglib.standardize_cell(
            _cell(self.structure),
            to_primitive=to_primitive,
            no_idealize=False,
            symprec=self.symprec,
            angle_tolerance=self.angle_tolerance,
        )
        if result is None:
            raise ValueError(
                "spglib could not standardize the structure at symprec={}"
                .format(self.symprec)
            )
        lattice, positions, numbers = result
        species = [Element.from_Z(int(number)).symbol for number in numbers]
        return Crystal(species, np.mod(positions, 1.0), Lattice(lattice))

    def get_primitive_standard_structure(self) -> Crystal:
        return self._standardize(True)

    def get_conventional_standard_structure(self) -> Crystal:
        return self._standardize(False)

    def get_ir_reciprocal_mesh(
        self, mesh: Sequence[int], is_shift: Sequence[int] = (0, 0, 0)
    ) -> Tuple[list, list]:
        _require_spglib()
        mesh_array = np.asarray(mesh, dtype=int)
        shift_array = np.asarray(is_shift, dtype=int)
        if mesh_array.shape != (3,) or np.any(mesh_array <= 0):
            raise ValueError("mesh must contain three positive integers")
        if shift_array.shape != (3,) or np.any((shift_array != 0) & (shift_array != 1)):
            raise ValueError("is_shift must contain three values, each 0 or 1")
        mapping, grid = spglib.get_ir_reciprocal_mesh(
            mesh_array,
            _cell(self.structure),
            is_shift=shift_array,
            symprec=self.symprec,
        )
        if mapping is None:
            raise ValueError("spglib could not construct an irreducible reciprocal mesh")
        counts = Counter(int(index) for index in mapping)
        representatives = sorted(counts)
        points = [
            ((np.asarray(grid[index], dtype=float) + 0.5 * shift_array) / mesh_array).tolist()
            for index in representatives
        ]
        return points, [counts[index] for index in representatives]

    def _dataset(self):
        _require_spglib()
        result = spglib.get_symmetry_dataset(
            _cell(self.structure),
            symprec=self.symprec,
            angle_tolerance=self.angle_tolerance,
        )
        if result is None:
            raise ValueError("spglib could not determine the structure's space group")
        return result
