"""Native computed entry containers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from monty.json import MSONable

from .composition import Composition
from .crystal import Crystal


class ComputedEntry(MSONable):
    """Computed energy associated with a native composition."""

    def __init__(
        self,
        composition: Composition,
        energy: float,
        parameters: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        entry_id: Optional[Any] = None,
    ) -> None:
        self.composition = composition
        self.energy = energy
        self.parameters = deepcopy(parameters) if parameters is not None else {}
        self.data = deepcopy(data) if data is not None else {}
        self.entry_id = entry_id

    def as_dict(self) -> Dict[str, Any]:
        """Convert entry to an MSONable dictionary."""
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "composition": self.composition.as_dict(),
            "energy": self.energy,
            "parameters": deepcopy(self.parameters),
            "data": deepcopy(self.data),
            "entry_id": self.entry_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComputedEntry":
        """Create an entry from an MSONable dictionary."""
        composition = d["composition"]
        if not isinstance(composition, Composition):
            composition = Composition.from_dict(composition)
        return cls(
            composition=composition,
            energy=d["energy"],
            parameters=d.get("parameters"),
            data=d.get("data"),
            entry_id=d.get("entry_id"),
        )


class ComputedStructureEntry(ComputedEntry):
    """Computed energy associated with a native crystal structure."""

    def __init__(
        self,
        structure: Crystal,
        energy: float,
        parameters: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        entry_id: Optional[Any] = None,
    ) -> None:
        self.structure = structure
        super().__init__(structure.composition, energy, parameters, data, entry_id)

    def as_dict(self) -> Dict[str, Any]:
        """Convert structure entry to an MSONable dictionary."""
        d = super().as_dict()
        d["structure"] = self.structure.as_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComputedStructureEntry":
        """Create a structure entry from an MSONable dictionary."""
        structure = d["structure"]
        if not isinstance(structure, Crystal):
            structure = Crystal.from_dict(structure)
        return cls(
            structure=structure,
            energy=d["energy"],
            parameters=d.get("parameters"),
            data=d.get("data"),
            entry_id=d.get("entry_id"),
        )
