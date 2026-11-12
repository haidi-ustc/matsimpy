"""Immutable calculation results returned by :meth:`Calculator.compute`."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional

import numpy as np

_VOIGT = ((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1))


def stress_to_matrix(stress: Any) -> np.ndarray:
    """Return a 3x3 stress tensor from a 3x3 or Voigt [xx, yy, zz, yz, xz, xy] input."""
    s = np.array(stress, dtype=np.float64)
    if s.shape == (3, 3):
        return s
    if s.shape == (6,):
        m = np.empty((3, 3))
        for k, (i, j) in enumerate(_VOIGT):
            m[i, j] = m[j, i] = s[k]
        return m
    raise ValueError(f"Stress must have shape (3, 3) or (6,), got {s.shape}")


def stress_to_voigt(stress: Any) -> np.ndarray:
    """Return Voigt [xx, yy, zz, yz, xz, xy] from a 3x3 or Voigt input."""
    m = stress_to_matrix(stress)
    return np.array([m[i, j] for i, j in _VOIGT])


def _frozen(value: Any) -> Optional[np.ndarray]:
    if value is None:
        return None
    arr = np.array(value, dtype=np.float64, copy=True)
    arr.flags.writeable = False
    return arr


@dataclass(frozen=True, eq=False)
class Results:
    """Energy (eV), forces (eV/Å, shape (N, 3)) and stress (eV/Å³, 3x3) of one structure.

    Arrays are read-only and ``extra`` is a read-only mapping, so a result can be
    cached and shared safely.  Missing quantities are ``None``.

    Example:
        >>> r = calc.compute(crystal)
        >>> r.energy, r.forces.shape, r.stress_voigt
    """

    energy: Optional[float] = None
    forces: Optional[np.ndarray] = None
    stress: Optional[np.ndarray] = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.energy is not None:
            object.__setattr__(self, "energy", float(self.energy))
        object.__setattr__(self, "forces", _frozen(self.forces))
        stress = None if self.stress is None else stress_to_matrix(self.stress)
        object.__setattr__(self, "stress", _frozen(stress))
        object.__setattr__(self, "extra", MappingProxyType(copy.deepcopy(dict(self.extra))))

    @property
    def stress_voigt(self) -> Optional[np.ndarray]:
        """Stress in Voigt order [xx, yy, zz, yz, xz, xy], or ``None``."""
        return None if self.stress is None else stress_to_voigt(self.stress)

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "Results":
        """Build from a calculator's raw ``results`` dict."""
        known = {"energy", "forces", "stress"}
        return cls(
            energy=raw.get("energy"),
            forces=raw.get("forces"),
            stress=raw.get("stress"),
            extra={k: v for k, v in raw.items() if k not in known},
        )

    def as_dict(self) -> Dict[str, Any]:
        """Plain dict with independent copies (only the quantities that are present)."""
        out: Dict[str, Any] = {}
        if self.energy is not None:
            out["energy"] = self.energy
        if self.forces is not None:
            out["forces"] = self.forces.copy()
        if self.stress is not None:
            out["stress"] = self.stress.copy()
        out.update(copy.deepcopy(dict(self.extra)))
        return out


__all__ = ["Results", "stress_to_matrix", "stress_to_voigt"]
