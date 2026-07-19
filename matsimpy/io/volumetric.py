"""Dependency-free operations on periodic volumetric data."""

from __future__ import annotations

import copy
import operator
from typing import Any

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
        self.structure = structure
        self.data = arrays
        self.distance_matrix = distance_matrix
        self.data_aug = data_aug or {}

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
        if self.distance_matrix is not None:
            if isinstance(self.distance_matrix, dict) and index in self.distance_matrix:
                return np.asarray(self.distance_matrix[index])
            matrix = np.asarray(self.distance_matrix)
            if matrix.shape == self.dim:
                return matrix
            if matrix.shape == (len(self.structure), *self.dim):
                return matrix[index]
        grid = np.indices(self.dim).transpose(1, 2, 3, 0) / np.asarray(self.dim)
        delta = grid - np.asarray(self.structure.frac_positions[index])
        delta -= np.round(delta)
        return np.linalg.norm(delta @ np.asarray(self.structure.lattice.matrix), axis=-1)

    def get_integrated_diff(self, ind, radius, nbins=1):
        if nbins <= 0:
            raise ValueError("nbins must be positive")
        radii = np.linspace(radius / nbins, radius, nbins)
        field = self.data.get("diff", self.data["total"])
        # Count periodic images independently, as required by integration over
        # a real-space sphere (boundary grid points can occur more than once).
        grid = np.indices(self.dim).transpose(1, 2, 3, 0) / np.asarray(self.dim)
        delta = grid - np.asarray(self.structure.frac_positions[ind])
        lattice = np.asarray(self.structure.lattice.matrix)
        shortest = np.min(np.linalg.svd(lattice, compute_uv=False))
        extent = int(np.ceil(radius / shortest)) + 1
        distances = []
        weights = []
        for image in np.ndindex(*([2 * extent + 1] * 3)):
            translation = np.asarray(image) - extent
            image_distances = np.linalg.norm((delta + translation) @ lattice, axis=-1)
            mask = image_distances <= radius + 1e-12
            distances.append(image_distances[mask])
            weights.append(field[mask])
        distances = np.concatenate(distances)
        weights = np.concatenate(weights)
        integral = np.array([weights[distances <= value + 1e-12].sum() for value in radii])
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
            "distance_matrix": copy.deepcopy(self.distance_matrix),
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
