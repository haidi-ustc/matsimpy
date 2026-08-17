"""Common native I/O data containers."""

from __future__ import annotations

import warnings
from copy import deepcopy
from typing import Any

import numpy as np
from monty.json import MSONable

from matsimpy.electronic_structure import Spin

_SOC_VECTOR_KEYS = {"diff_x", "diff_y", "diff_z"}


class VolumetricData(MSONable):
    """Native representation of regular volumetric grid data."""

    def __init__(
        self,
        structure: Any,
        data: dict[str, Any],
        distance_matrix: dict | None = None,
        data_aug: dict[str, Any] | None = None,
    ) -> None:
        if "total" not in data:
            raise ValueError("Volumetric data must include a 'total' channel")

        self.structure = structure
        self.data = _validated_grid_map(data, "data")
        self.dim = self.data["total"].shape
        self.data_aug = data_aug if data_aug is not None else {}
        self.ngridpts = int(np.prod(self.dim))
        self.is_soc = _SOC_VECTOR_KEYS.issubset(self.data)
        self.is_spin_polarized = "diff" in self.data and not self.is_soc
        self._spin_data: dict[Spin, np.ndarray] = {}
        self._distance_matrix = distance_matrix if distance_matrix is not None else {}
        self.name = type(self).__name__

    def __add__(self, other: "VolumetricData") -> "VolumetricData":
        return self.linear_add(other, 1.0)

    def __radd__(self, other: object) -> "VolumetricData":
        if other == 0 or other is None:
            return self
        if isinstance(other, type(self)):
            return self.__add__(other)
        return NotImplemented

    def __sub__(self, other: "VolumetricData") -> "VolumetricData":
        return self.linear_add(other, -1.0)

    @property
    def spin_data(self) -> dict[Spin, np.ndarray]:
        if self.is_soc:
            raise ValueError(
                "SOC volumetric data does not have collinear "
                "Spin.up/Spin.down channels"
            )
        if not self._spin_data:
            diff = self.data.get("diff", 0)
            self._spin_data = {
                Spin.up: 0.5 * (self.data["total"] + diff),
                Spin.down: 0.5 * (self.data["total"] - diff),
            }
        return self._spin_data

    def get_axis_grid(self, ind: int) -> list[float]:
        if ind not in (0, 1, 2):
            raise IndexError("Axis index must be 0, 1, or 2")
        lengths = (self.structure.lattice.a, self.structure.lattice.b, self.structure.lattice.c)
        return [i / self.dim[ind] * lengths[ind] for i in range(self.dim[ind])]

    def value_at(self, x: float, y: float, z: float) -> float:
        """Sample the total channel at fractional coordinates with periodic wrapping."""
        coords = np.mod(np.array([x, y, z], dtype=float), 1.0)
        floors = np.floor(coords * self.dim).astype(int)
        weights = coords * self.dim - floors
        lower = np.mod(floors, self.dim)
        upper = np.mod(floors + 1, self.dim)

        value = 0.0
        total = self.data["total"]
        for ix, wx in ((lower[0], 1.0 - weights[0]), (upper[0], weights[0])):
            for iy, wy in ((lower[1], 1.0 - weights[1]), (upper[1], weights[1])):
                for iz, wz in ((lower[2], 1.0 - weights[2]), (upper[2], weights[2])):
                    value += wx * wy * wz * total[ix, iy, iz]
        return np.asarray(value).item()

    def copy(self) -> "VolumetricData":
        return type(self)(
            self.structure,
            {key: value.copy() for key, value in self.data.items()},
            distance_matrix=deepcopy(self._distance_matrix),
            data_aug=deepcopy(self.data_aug),
        )

    def linear_add(self, other: "VolumetricData", scale_factor: float = 1.0) -> "VolumetricData":
        if not isinstance(other, VolumetricData):
            raise TypeError("Can only combine VolumetricData with VolumetricData")
        if self.structure != other.structure:
            warnings.warn(
                "Structures are different. Make sure you know what you are doing.",
                stacklevel=2,
            )
        if set(self.data) != set(other.data):
            raise ValueError("Data have different keys")
        if self.dim != other.dim:
            raise ValueError("Volumetric data grids must have the same shape")

        data = {
            key: self.data[key] + scale_factor * other.data[key]
            for key in self.data
        }
        return type(self)(self.structure, data, distance_matrix=deepcopy(self._distance_matrix))


def _validated_grid_map(
    arrays: dict[str, Any] | None,
    name: str,
    expected_shape: tuple[int, int, int] | None = None,
) -> dict[str, np.ndarray]:
    if not arrays:
        return {}

    converted: dict[str, np.ndarray] = {}
    shape = expected_shape
    for key, value in arrays.items():
        array = np.asarray(value)
        if array.ndim != 3:
            raise ValueError(f"{name} channel '{key}' must be three-dimensional")
        if any(dim <= 0 for dim in array.shape):
            raise ValueError(f"{name} channel '{key}' must have positive grid extents")
        if shape is None:
            shape = array.shape
        elif array.shape != shape:
            raise ValueError(
                "All volumetric arrays must have the same shape, "
                f"got {array.shape} and {shape}"
            )
        converted[key] = array
    return converted
