"""Native density-of-states result containers."""

from __future__ import annotations

from typing import Any

import numpy as np
from monty.json import MSONable

from .core import Spin


def _spin_from_key(key: Spin | str | int) -> Spin:
    if isinstance(key, Spin):
        return key
    if isinstance(key, str):
        return Spin[key]
    return Spin(key)


def _densities_from_dict(densities: dict[Spin | str | int, Any]) -> dict[Spin, np.ndarray]:
    converted = {}
    for spin, density in densities.items():
        converted[_spin_from_key(spin)] = np.asarray(density, dtype=float)
    return converted


def _densities_as_dict(densities: dict[Spin, np.ndarray]) -> dict[str, list[float]]:
    return {spin.name: density.tolist() for spin, density in densities.items()}


def _scaled_pdos(value: Any, factor: float) -> Any:
    if isinstance(value, dict):
        return {key: _scaled_pdos(item, factor) for key, item in value.items()}
    return np.asarray(value, dtype=float) / factor


def _pdos_as_dict(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key.name if isinstance(key, Spin) else key: _pdos_as_dict(item)
            for key, item in value.items()
        }
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


class Dos(MSONable):
    """Total or projected density of states on a common energy grid."""

    def __init__(self, efermi: float, energies: Any, densities: dict[Spin | str | int, Any]):
        self.efermi = float(efermi)
        self.energies = np.asarray(energies, dtype=float)
        if self.energies.ndim != 1:
            raise ValueError("DOS energies must be a one-dimensional array")

        self.densities = _densities_from_dict(densities)
        for density in self.densities.values():
            if density.ndim != 1:
                raise ValueError("DOS densities must be one-dimensional arrays")
            if len(density) != len(self.energies):
                raise ValueError("Density length must match energy length")

    def as_dict(self) -> dict[str, Any]:
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "efermi": self.efermi,
            "energies": self.energies.tolist(),
            "densities": _densities_as_dict(self.densities),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dos":
        return cls(data["efermi"], data["energies"], data["densities"])


class CompleteDos(MSONable):
    """Complete DOS with a native structure, total DOS, and projected DOS."""

    def __init__(
        self,
        structure: Any,
        total_dos: Dos,
        pdos: dict[Any, Any],
        normalize: bool = False,
    ):
        self.structure = structure
        self.total_dos = total_dos
        self.pdos = dict(pdos)

        if normalize:
            volume = float(structure.volume)
            if volume <= 0:
                raise ValueError("Cannot normalize DOS with non-positive structure volume")
            self.total_dos = Dos(
                total_dos.efermi,
                total_dos.energies,
                {spin: density / volume for spin, density in total_dos.densities.items()},
            )
            self.pdos = _scaled_pdos(self.pdos, volume)

    def as_dict(self) -> dict[str, Any]:
        structure = (
            self.structure.as_dict()
            if hasattr(self.structure, "as_dict")
            else self.structure
        )
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "structure": structure,
            "total_dos": self.total_dos.as_dict(),
            "pdos": _pdos_as_dict(self.pdos),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompleteDos":
        from matsimpy.core import Crystal

        structure = data["structure"]
        if isinstance(structure, dict) and structure.get("@class") == "Crystal":
            structure = Crystal.from_dict(structure)
        return cls(structure, Dos.from_dict(data["total_dos"]), data.get("pdos", {}))
