"""Dependency-free operations on periodic volumetric data."""

from __future__ import annotations

import copy
import itertools
import operator

import numpy as np
from monty.json import MSONable

from matsimpy.core import Crystal
from matsimpy.electronic_structure import Spin


class VolumetricData(MSONable):
    """A structure and one or more scalar fields sampled on a periodic grid."""

    def __init__(self, structure, data, distance_matrix=None, data_aug=None):
        if not data:
            raise ValueError("data must be a non-empty mapping of grids")
        arrays = {key: np.asarray(value) for key, value in data.items()}
        shapes = {value.shape for value in arrays.values()}
        if any(value.ndim != 3 for value in arrays.values()):
            raise ValueError("volumetric grids must be three-dimensional")
        if len(shapes) != 1:
            raise ValueError("all volumetric grids must have the same shape")
        dim = next(iter(shapes))
        if any(length == 0 for length in dim):
            raise ValueError("volumetric grid dimensions must be non-zero")
        self.structure = structure
        self.data = arrays
        self.distance_matrix = distance_matrix
        self._distance_matrix = self._validate_distance_matrix(distance_matrix)
        self.data_aug = data_aug or {}

    def _validate_distance_matrix(self, distance_matrix):
        """Normalize an optional per-site distance cache and validate every grid."""
        if distance_matrix is None:
            return {}
        if isinstance(distance_matrix, dict):
            cache = {}
            for index, distances in distance_matrix.items():
                if not isinstance(index, (int, np.integer)) or not 0 <= int(index) < len(self.structure):
                    raise ValueError("distance_matrix contains an invalid site index")
                array = np.asarray(distances, dtype=float)
                if array.shape != self.dim:
                    raise ValueError(f"distance_matrix grids must have shape {self.dim}")
                cache[int(index)] = array
            return cache

        matrix = np.asarray(distance_matrix, dtype=float)
        if matrix.shape == (len(self.structure), *self.dim):
            return {index: matrix[index] for index in range(len(self.structure))}
        if len(self.structure) == 1 and matrix.shape == self.dim:
            return {0: matrix}
        raise ValueError(
            f"distance_matrix must have shape {(len(self.structure), *self.dim)}"
            + (f" or {self.dim} for a single-site structure" if len(self.structure) == 1 else "")
        )

    @property
    def dim(self):
        return tuple(next(iter(self.data.values())).shape)

    @property
    def ngridpts(self):
        return int(np.prod(self.dim))

    @property
    def is_spin_polarized(self):
        return "diff" in self.data

    @property
    def spin_data(self):
        if not self.is_spin_polarized:
            return {Spin.up: self.data["total"]}
        return {
            Spin.up: (self.data["total"] + self.data["diff"]) / 2,
            Spin.down: (self.data["total"] - self.data["diff"]) / 2,
        }

    def value_at(self, x, y, z):
        return self.data["total"][x, y, z]

    def get_interpolated_value(self, frac_coords):
        """Trilinearly interpolate the total grid at periodic fractional coordinates."""
        position = np.mod(np.asarray(frac_coords, dtype=float), 1.0) * np.asarray(self.dim)
        lower = np.floor(position).astype(int)
        fraction = position - lower
        result = 0.0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    weight = ((1 - fraction[0]) if dx == 0 else fraction[0])
                    weight *= ((1 - fraction[1]) if dy == 0 else fraction[1])
                    weight *= ((1 - fraction[2]) if dz == 0 else fraction[2])
                    index = tuple((lower + (dx, dy, dz)) % self.dim)
                    result += weight * self.data["total"][index]
        return float(result)

    def get_average_along_axis(self, ind):
        if ind not in (0, 1, 2):
            raise ValueError("axis must be 0, 1, or 2")
        return np.mean(self.data["total"], axis=tuple(axis for axis in range(3) if axis != ind))

    def _distances_from_site(self, index):
        if index < 0 or index >= len(self.structure):
            raise IndexError("site index out of range")
        if index in self._distance_matrix:
            return self._distance_matrix[index]
        grid = np.indices(self.dim).transpose(1, 2, 3, 0) / np.asarray(self.dim)
        delta = grid - np.asarray(self.structure.frac_positions[index])
        lattice = np.asarray(self.structure.lattice.matrix)
        sigma_min = np.min(np.linalg.svd(lattice, compute_uv=False))
        distances = np.empty(self.dim)

        # This solves the three-dimensional closest-vector problem exactly.  A
        # rounded fractional translation supplies an initial upper bound R.
        # Since ||x A|| >= sigma_min(A) ||x||, no improving lattice vector can
        # lie outside the component bounds ||delta + n|| <= R / sigma_min.
        for grid_index in np.ndindex(self.dim):
            displacement = delta[grid_index]
            initial = displacement - np.round(displacement)
            upper_bound = np.linalg.norm(initial @ lattice)
            fractional_bound = upper_bound / sigma_min + 1e-12
            ranges = [
                range(
                    int(np.ceil(-component - fractional_bound)),
                    int(np.floor(-component + fractional_bound)) + 1,
                )
                for component in displacement
            ]
            translations = np.asarray(list(itertools.product(*ranges)), dtype=float)
            distances[grid_index] = np.min(np.linalg.norm((displacement + translations) @ lattice, axis=1))
        self._distance_matrix[index] = distances
        return distances

    def get_integrated_diff(self, ind, radius, nbins=1):
        if nbins <= 0:
            raise ValueError("nbins must be positive")
        radii = np.linspace(radius / nbins, radius, nbins)
        field = self.data.get("diff", self.data["total"])
        distances = self._distances_from_site(ind)
        integral = np.array([field[distances <= value + 1e-12].sum() for value in radii])
        integral /= self.ngridpts
        return np.column_stack((radii, integral))

    def _binary(self, other, operation):
        if isinstance(other, VolumetricData):
            if self.dim != other.dim or set(self.data) != set(other.data):
                raise ValueError("volumetric operands must have matching grids and data keys")
            data = {key: operation(value, other.data[key]) for key, value in self.data.items()}
        else:
            data = {key: operation(value, other) for key, value in self.data.items()}
        return type(self)(
            self.structure,
            data,
            distance_matrix=self.distance_matrix,
            data_aug=copy.deepcopy(self.data_aug),
        )

    def __add__(self, other):
        return self._binary(other, operator.add)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self._binary(other, operator.sub)

    def __rsub__(self, other):
        return self._binary(other, lambda value, scalar: scalar - value)

    def __mul__(self, other):
        return self._binary(other, operator.mul)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        return self._binary(other, operator.truediv)

    def linear_add(self, other, scale_factor=1.0):
        return self + other * scale_factor

    def as_dict(self):
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "structure": self.structure.as_dict(),
            "data": {key: value.tolist() for key, value in self.data.items()},
            "distance_matrix": (
                {index: distances.tolist() for index, distances in self._distance_matrix.items()}
                if self.distance_matrix is not None
                else None
            ),
            "data_aug": self.data_aug,
        }

    @classmethod
    def from_dict(cls, d):
        structure = d["structure"]
        if isinstance(structure, dict):
            structure = Crystal.from_dict(structure)
        return cls(
            structure,
            d["data"],
            distance_matrix=d.get("distance_matrix"),
            data_aug=d.get("data_aug"),
        )
