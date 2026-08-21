"""Native high-symmetry k-path generation for 2D and cubic lattices."""

from __future__ import annotations

from numbers import Integral, Real

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

_FIXED_2D_KPATHS = {
    "square": {
        "kpoints": {
            "Γ": [0.0, 0.0],
            "X": [0.0, 0.5],
            "M": [0.5, 0.5],
        },
        "path": [["M", "Γ", "X", "M"]],
    },
    "rectangular": {
        "kpoints": {
            "Γ": [0.0, 0.0],
            "X": [0.5, 0.0],
            "S": [0.5, 0.5],
            "Y": [0.0, 0.5],
        },
        "path": [["Γ", "X", "S", "Y", "Γ", "S"]],
    },
    "hexagonal": {
        "kpoints": {
            "Γ": [0.0, 0.0],
            "M": [0.5, 0.0],
            "K": [1.0 / 3.0, 1.0 / 3.0],
        },
        "path": [["Γ", "M", "K", "Γ"]],
    },
}

_2D_PROVENANCE = "native 2D Bravais-lattice table"


class HighSymmetryKpath:
    """High-symmetry path service backed by native lattice classification.

    Two-dimensional crystals are identified from ``Crystal.pbc`` and classified
    from their in-plane primitive lattice metric.  The supported 2D families are
    oblique, rectangular, centered rectangular (rhombic), square, and hexagonal.
    Path sequences and canonical special points follow ASE's 2D Bravais tables,
    but fractional coordinates are mapped back to the input lattice basis.
    Three-dimensional support remains limited to primitive cubic crystals.
    """

    def __init__(
        self,
        crystal: Crystal,
        symprec: float = 1e-5,
        angle_tolerance: float = -1.0,
    ) -> None:
        if not isinstance(crystal, Crystal):
            raise TypeError("crystal must be a Crystal instance")
        if (
            isinstance(symprec, bool)
            or not isinstance(symprec, Real)
            or not np.isfinite(symprec)
            or symprec <= 0
        ):
            raise ValueError("symprec must be a positive finite number")
        if (
            isinstance(angle_tolerance, bool)
            or not isinstance(angle_tolerance, Real)
            or not np.isfinite(angle_tolerance)
            or (angle_tolerance < 0 and angle_tolerance != -1.0)
        ):
            raise ValueError("angle_tolerance must be -1 or a non-negative number")

        self.crystal = crystal
        self.symprec = float(symprec)
        self.angle_tolerance = float(angle_tolerance)
        periodic_dimensions = sum(crystal.pbc)

        if periodic_dimensions == 2:
            self.crystal_system = "2D"
            self.space_group_symbol = None
            self.kpath = self._build_2d_kpath()
            return
        if periodic_dimensions != 3:
            raise NotImplementedError(
                "HighSymmetryKpath supports crystals with two or three periodic "
                f"dimensions; detected {periodic_dimensions} periodic dimensions"
            )

        analyzer = SymmetryAnalyzer(
            crystal,
            symprec=self.symprec,
            angle_tolerance=self.angle_tolerance,
        )
        symmetry = analyzer.analyze_crystal(crystal)
        self.crystal_system = symmetry.get("crystal_system")
        self.space_group_symbol = symmetry.get("space_group_symbol")

        if self.crystal_system != "Cubic":
            raise NotImplementedError(
                "HighSymmetryKpath only supports the native primitive-cubic "
                f"path table; detected crystal system: {self.crystal_system}"
            )
        centering = self._space_group_centering(self.space_group_symbol)
        if centering != "P":
            raise NotImplementedError(
                "HighSymmetryKpath only supports the native primitive-cubic "
                "path table; detected cubic space group "
                f"{self.space_group_symbol} with centering {centering}"
            )

        self.lattice_type = "primitive_cubic"
        self.kpath = self._copy_kpath(_PRIMITIVE_CUBIC_KPATH)

    @staticmethod
    def _copy_kpath(kpath: dict) -> dict:
        return {
            "kpoints": {
                label: list(coords) for label, coords in kpath["kpoints"].items()
            },
            "path": [list(segment) for segment in kpath["path"]],
            "provenance": kpath["provenance"],
        }

    def _build_2d_kpath(self) -> dict:
        periodic_axes = [
            index for index, periodic in enumerate(self.crystal.pbc) if periodic
        ]
        vectors = np.asarray(self.crystal.lattice.matrix[periodic_axes], dtype=float)
        vectors, transform = self._reduce_2d_basis(vectors)
        lengths = np.linalg.norm(vectors, axis=1)

        angle = self._angle_between(vectors[0], vectors[1])
        angle_tol = 1e-3 if self.angle_tolerance == -1.0 else self.angle_tolerance
        equal_lengths = np.isclose(
            lengths[0], lengths[1], rtol=self.symprec, atol=self.symprec
        )
        right_angle = np.isclose(angle, 90.0, rtol=0.0, atol=angle_tol)
        hexagonal_angle = np.isclose(
            angle, 60.0, rtol=0.0, atol=angle_tol
        ) or np.isclose(angle, 120.0, rtol=0.0, atol=angle_tol)

        if equal_lengths and right_angle:
            lattice_type = "square"
        elif equal_lengths and hexagonal_angle:
            lattice_type = "hexagonal"
            if angle < 90.0:
                vectors, transform = self._flip_second_vector(
                    vectors, transform
                )
                angle = 180.0 - angle
        elif right_angle:
            lattice_type = "rectangular"
        elif equal_lengths:
            lattice_type = "centered_rectangular"
            if angle > 90.0:
                vectors, transform = self._flip_second_vector(
                    vectors, transform
                )
                angle = 180.0 - angle
        else:
            lattice_type = "oblique"
            if angle > 90.0:
                vectors, transform = self._flip_second_vector(
                    vectors, transform
                )
                angle = 180.0 - angle

        self.lattice_type = lattice_type
        if lattice_type in _FIXED_2D_KPATHS:
            table = _FIXED_2D_KPATHS[lattice_type]
        elif lattice_type == "centered_rectangular":
            table = self._centered_rectangular_kpath(angle)
        else:
            table = self._oblique_kpath(lengths[0], lengths[1], angle)

        inverse_transpose = np.linalg.inv(transform).T
        mapped_points = {}
        for label, point in table["kpoints"].items():
            original_plane_point = np.asarray(point, dtype=float) @ inverse_transpose
            original_point = np.zeros(3)
            original_point[periodic_axes] = original_plane_point
            mapped_points[label] = original_point.tolist()

        return {
            "kpoints": mapped_points,
            "path": [list(segment) for segment in table["path"]],
            "provenance": _2D_PROVENANCE,
        }

    def _reduce_2d_basis(
        self,
        vectors: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Gauss-reduce two primitive vectors and retain their basis mapping."""
        reduced = np.array(vectors, dtype=float, copy=True)
        transform = np.eye(2)
        swap = np.array([[0.0, 1.0], [1.0, 0.0]])

        for _ in range(32):
            lengths_squared = np.einsum("ij,ij->i", reduced, reduced)
            if lengths_squared[1] < lengths_squared[0] and not np.isclose(
                lengths_squared[0],
                lengths_squared[1],
                rtol=self.symprec,
                atol=self.symprec,
            ):
                reduced = swap @ reduced
                transform = swap @ transform

            projection = np.dot(reduced[0], reduced[1]) / np.dot(
                reduced[0], reduced[0]
            )
            boundary_tolerance = max(self.symprec, np.finfo(float).eps * 10)
            if projection > 0.5 + boundary_tolerance:
                multiplier = int(np.floor(projection + 0.5))
            elif projection < -0.5 - boundary_tolerance:
                multiplier = int(np.ceil(projection - 0.5))
            else:
                multiplier = 0
            if multiplier == 0:
                return reduced, transform

            reduction = np.array([[1.0, 0.0], [-multiplier, 1.0]])
            reduced = reduction @ reduced
            transform = reduction @ transform

        raise ValueError("Unable to reduce the two-dimensional primitive lattice")

    @staticmethod
    def _angle_between(first: np.ndarray, second: np.ndarray) -> float:
        denominator = np.linalg.norm(first) * np.linalg.norm(second)
        cosine = np.dot(first, second) / denominator
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    @staticmethod
    def _flip_second_vector(
        vectors: np.ndarray,
        transform: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        flip = np.array([[1.0, 0.0], [0.0, -1.0]])
        return flip @ vectors, flip @ transform

    @staticmethod
    def _centered_rectangular_kpath(angle: float) -> dict:
        alpha = np.radians(angle)
        eta = np.sin(alpha / 2.0) ** 2 / np.sin(alpha) ** 2
        xi = eta * np.cos(alpha)
        return {
            "kpoints": {
                "Γ": [0.0, 0.0],
                "X": [eta, -eta],
                "A1": [0.5 + xi, 0.5 - xi],
                "Y": [0.5, 0.5],
            },
            "path": [["Γ", "X", "A1", "Y", "Γ"]],
        }

    @staticmethod
    def _oblique_kpath(a: float, b: float, angle: float) -> dict:
        alpha = np.radians(angle)
        cosine = np.cos(alpha)
        sine_squared = np.sin(alpha) ** 2
        eta = (1.0 - a * cosine / b) / (2.0 * sine_squared)
        nu = 0.5 - eta * b * cosine / a
        return {
            "kpoints": {
                "Γ": [0.0, 0.0],
                "Y": [0.0, 0.5],
                "H": [eta, 1.0 - nu],
                "C": [0.5, 0.5],
                "H1": [1.0 - eta, nu],
                "X": [0.5, 0.0],
            },
            "path": [["Γ", "Y", "H", "C", "H1", "X", "Γ"]],
        }

    @staticmethod
    def _space_group_centering(space_group_symbol: str | None) -> str | None:
        if not space_group_symbol:
            return None
        return space_group_symbol.strip()[0]

    def get_kpoints(
        self,
        line_density: int = 20,
        coords_are_cartesian: bool = False,
    ) -> tuple[list[list[float]], list[str]]:
        """Return interpolated k-points and endpoint labels for the native path.

        Fractional points use the input crystal's reciprocal basis.  Reducing a
        non-canonical primitive cell can therefore produce valid fractions outside
        the conventional ``[0, 1)`` interval.  Cartesian points are expressed in
        the reciprocal-lattice units returned by :class:`~matsimpy.core.Lattice`.
        """
        if (
            isinstance(line_density, bool)
            or not isinstance(line_density, Integral)
            or line_density < 1
        ):
            raise ValueError("line_density must be a positive integer")
        if not isinstance(coords_are_cartesian, (bool, np.bool_)):
            raise TypeError("coords_are_cartesian must be a boolean")

        kpoints: list[list[float]] = []
        labels: list[str] = []
        for path in self.kpath["path"]:
            for segment_index, (start_label, end_label) in enumerate(
                zip(path[:-1], path[1:])
            ):
                start = np.array(self.kpath["kpoints"][start_label], dtype=float)
                end = np.array(self.kpath["kpoints"][end_label], dtype=float)
                for index in range(line_density + 1):
                    if segment_index > 0 and index == 0:
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
