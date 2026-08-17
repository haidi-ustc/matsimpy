"""Native density-of-states result containers."""

from __future__ import annotations

from typing import Any

import numpy as np
from monty.json import MSONable

from .core import Orbital, OrbitalType, Spin

_KEY_ENUMS = {"Spin": Spin, "Orbital": Orbital, "OrbitalType": OrbitalType}


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


def _encode_pdos_key(key: Any) -> dict[str, Any]:
    if isinstance(key, (Spin, Orbital, OrbitalType)):
        return {"type": key.__class__.__name__, "name": key.name}
    if isinstance(key, bool):
        return {"type": "bool", "value": key}
    if isinstance(key, int):
        return {"type": "int", "value": key}
    if isinstance(key, float):
        return {"type": "float", "value": key}
    if key is None:
        return {"type": "none", "value": None}
    return {"type": "str", "value": str(key)}


def _decode_pdos_key(data: dict[str, Any]) -> Any:
    key_type = data["type"]
    if key_type in _KEY_ENUMS:
        return _KEY_ENUMS[key_type][data["name"]]
    if key_type == "bool":
        return bool(data["value"])
    if key_type == "int":
        return int(data["value"])
    if key_type == "float":
        return float(data["value"])
    if key_type == "none":
        return None
    if key_type == "str":
        return str(data["value"])
    raise ValueError(f"Unsupported projected DOS key type: {key_type}")


def _pdos_as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "@type": "dict",
            "entries": [
                {"key": _encode_pdos_key(key), "value": _pdos_as_dict(item)}
                for key, item in value.items()
            ],
        }
    return {"@type": "ndarray", "data": np.asarray(value, dtype=float).tolist()}


def _pdos_from_dict(data: Any) -> Any:
    if not isinstance(data, dict) or "@type" not in data:
        return np.asarray(data, dtype=float)
    data_type = data["@type"]
    if data_type == "dict":
        return {
            _decode_pdos_key(entry["key"]): _pdos_from_dict(entry["value"])
            for entry in data["entries"]
        }
    if data_type == "ndarray":
        return np.asarray(data["data"], dtype=float)
    raise ValueError(f"Unsupported projected DOS payload type: {data_type}")


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
        return cls(
            structure,
            Dos.from_dict(data["total_dos"]),
            _pdos_from_dict(data.get("pdos", {"@type": "dict", "entries": []})),
        )
