"""Native trajectory container."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, Sequence

from monty.json import MSONable

from .crystal import Crystal


class Trajectory(MSONable):
    """Sequence of native crystal structures."""

    def __init__(
        self, structures: Sequence[Crystal], constant_lattice: bool = True
    ) -> None:
        if not structures:
            raise ValueError("Trajectory requires at least one structure")
        self.structures = list(structures)
        self.constant_lattice = constant_lattice

    @classmethod
    def from_structures(
        cls, structures: Iterable[Crystal], constant_lattice: bool = True
    ) -> "Trajectory":
        return cls(list(structures), constant_lattice=constant_lattice)

    def __len__(self) -> int:
        return len(self.structures)

    def __iter__(self) -> Iterator[Crystal]:
        return iter(self.structures)

    def __getitem__(self, index: int) -> Crystal:
        return self.structures[index]

    def as_dict(self) -> Dict[str, Any]:
        """Convert trajectory to an MSONable dictionary."""
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "structures": [structure.as_dict() for structure in self.structures],
            "constant_lattice": self.constant_lattice,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Trajectory":
        """Create a trajectory from an MSONable dictionary."""
        structures = [
            structure if isinstance(structure, Crystal) else Crystal.from_dict(structure)
            for structure in d["structures"]
        ]
        return cls(
            structures=structures,
            constant_lattice=d.get("constant_lattice", True),
        )
