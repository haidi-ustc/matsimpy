"""Calculator base classes.

A calculator maps a structure to an immutable :class:`Results`::

    r = calc.compute(structure)      # the one core API (cached, LRU)
    r.energy, r.forces, r.stress

Calculators hold parameters and a result cache only; they keep no "current
structure" and no mutable results (both removed in 0.9.0).
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

import numpy as np
from monty.json import MSONable

from ..core import Crystal, Molecule
from .results import Results, stress_to_matrix, stress_to_voigt

StructureT = Union[Crystal, Molecule]


class Calculator(ABC, MSONable):
    """Base class: subclasses implement :meth:`_calculate`.

    Results are cached keyed by the structure's exact fingerprint (species,
    coordinates, lattice, PBC, site properties); the ``cache_size`` most
    recently used structures are kept.

    Example:
        >>> calc = LennardJones(sigma=3.4, epsilon=0.0104)
        >>> r = calc.compute(crystal)
        >>> calc.get_potential_energy(crystal) == r.energy
        True
    """

    #: Number of structures whose results are kept (least recently used evicted).
    cache_size: int = 8

    def __init__(self, **parameters: Any) -> None:
        self.parameters = parameters.copy()
        self._cache: "OrderedDict[int, Results]" = OrderedDict()

    # -- the core API ----------------------------------------------------------

    @abstractmethod
    def _calculate(self, structure: StructureT) -> Union[Results, Mapping[str, Any]]:
        """Compute *structure*; return :class:`Results` or a raw ``{"energy": ...}`` dict."""

    def compute(self, structure: StructureT) -> Results:
        """Return the immutable :class:`Results` for *structure* (cached, LRU).

        Raises:
            TypeError: If *structure* is not a Crystal or Molecule.
        """
        if not isinstance(structure, (Crystal, Molecule)):
            raise TypeError(
                f"structure must be a Crystal or Molecule, got {type(structure).__name__}"
            )
        cache = self.__dict__.setdefault("_cache", OrderedDict())
        key = structure._structural_hash()
        hit = cache.get(key)
        if hit is not None:
            cache.move_to_end(key)
            return hit
        raw = self._calculate(structure)
        result = raw if isinstance(raw, Results) else Results.from_raw(raw)
        cache[key] = result
        while len(cache) > max(1, int(self.cache_size)):
            cache.popitem(last=False)
        return result

    def _invalidate(self) -> None:
        """Drop every cached result (call whenever parameters or the model change)."""
        self.__dict__.setdefault("_cache", OrderedDict()).clear()

    # -- parameters ------------------------------------------------------------

    def set_parameters(self, **kwargs: Any) -> None:
        """Update parameters (clears all cached results)."""
        self.parameters.update(kwargs)
        self._invalidate()

    def get_parameters(self) -> Dict[str, Any]:
        """Copy of the current parameters."""
        return self.parameters.copy()

    # -- convenience getters (all require the structure) -------------------------

    def get_potential_energy(self, structure: StructureT) -> float:
        """Potential energy (eV). Raises ValueError if the calculator gives none."""
        energy = self.compute(structure).energy
        if energy is None:
            raise ValueError("Energy not available in results.")
        return energy

    def get_forces(self, structure: StructureT) -> np.ndarray:
        """Forces (eV/Å), shape (N, 3), as a writable copy."""
        forces = self.compute(structure).forces
        if forces is None:
            raise ValueError("Forces not available in results.")
        return forces.copy()

    def get_stress(self, structure: StructureT, *, voigt: bool = False) -> np.ndarray:
        """Stress (eV/Å³): 3x3, or Voigt [xx, yy, zz, yz, xz, xy] with ``voigt=True``."""
        stress = self.compute(structure).stress
        if stress is None:
            raise ValueError("Stress not available in results.")
        return stress_to_voigt(stress) if voigt else stress_to_matrix(stress)

    # -- serialization (parameters only; results are never serialized) ----------

    def as_dict(self) -> Dict[str, Any]:
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "parameters": self.parameters.copy(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Calculator":
        return cls(**d.get("parameters", {}))

    def __repr__(self) -> str:
        params = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
        return f"{self.__class__.__name__}({params})"


class FileIOCalculator(Calculator):
    """Calculator that drives an external program through files.

    ``compute(structure)`` = :meth:`write_input` → :meth:`_execute` →
    :meth:`read_results`.  For offline work call the two file steps directly::

        calc.write_input(structure, "run1")   # inputs only, nothing executed
        ...                                    # run the program yourself
        r = calc.read_results("run1")          # -> Results
    """

    def __init__(self, directory: Union[str, Path], **parameters: Any) -> None:
        # Every constructor argument lives in ``parameters`` so that
        # ``from_dict(as_dict())`` rebuilds the same calculator.
        super().__init__(directory=str(directory), **parameters)

    @property
    def directory(self) -> Path:
        return Path(self.parameters["directory"])

    def _dir(self, directory: Optional[Union[str, Path]]) -> Path:
        path = self.directory if directory is None else Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @abstractmethod
    def write_input(self, structure: StructureT, directory: Optional[Union[str, Path]] = None) -> Path:
        """Write the program's input files into *directory* (default: ``self.directory``)."""

    @abstractmethod
    def read_results(self, directory: Optional[Union[str, Path]] = None) -> Results:
        """Parse the program's output files in *directory* into :class:`Results`."""

    @abstractmethod
    def _execute(self, directory: Path) -> None:
        """Run the external program in *directory*."""

    def _calculate(self, structure: StructureT) -> Results:
        directory = self.write_input(structure)
        self._execute(directory)
        return self.read_results(directory)


__all__ = ["Calculator", "FileIOCalculator"]
