"""Computed energy entries using MatSimPy core objects."""

from copy import deepcopy
from typing import Any, Dict, Mapping, Optional, Union

from monty.json import MSONable, MontyDecoder

from matsimpy.core.composition import Composition
from matsimpy.core.crystal import Crystal


class ComputedEntry(MSONable):
    """A composition and its calculated energy and metadata."""

    def __init__(
        self,
        composition: Union[Composition, str, Mapping[str, int]],
        energy: float,
        correction: float = 0.0,
        parameters: Optional[dict] = None,
        data: Optional[dict] = None,
        entry_id: Optional[str] = None,
    ) -> None:
        if isinstance(composition, Composition):
            self.composition = composition
        elif isinstance(composition, str):
            self.composition = Composition(composition)
        elif isinstance(composition, Mapping):
            formula = "".join(
                "%s%s" % (symbol, amount if amount != 1 else "")
                for symbol, amount in composition.items()
            )
            self.composition = Composition(formula)
        else:
            raise TypeError("composition must be a Composition, formula, or mapping")
        self.uncorrected_energy = float(energy)
        self.correction = float(correction)
        self.parameters = deepcopy(parameters) if parameters is not None else {}
        self.data = deepcopy(data) if data is not None else {}
        self.entry_id = entry_id

    @property
    def energy(self) -> float:
        return self.uncorrected_energy + self.correction

    @property
    def energy_per_atom(self) -> float:
        num_atoms = sum(self.composition.composition.values())
        return self.energy / num_atoms

    def as_dict(self) -> Dict[str, Any]:
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "composition": self.composition.as_dict(),
            "energy": self.uncorrected_energy,
            "correction": self.correction,
            "parameters": deepcopy(self.parameters),
            "data": deepcopy(self.data),
            "entry_id": self.entry_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComputedEntry":
        decoder = MontyDecoder()
        composition = decoder.process_decoded(d["composition"])
        return cls(
            composition,
            d["energy"],
            correction=d.get("correction", 0.0),
            parameters=decoder.process_decoded(d.get("parameters")),
            data=decoder.process_decoded(d.get("data")),
            entry_id=d.get("entry_id"),
        )


class ComputedStructureEntry(ComputedEntry):
    """A crystal structure and its calculated energy and metadata."""

    def __init__(
        self,
        structure: Crystal,
        energy: float,
        correction: float = 0.0,
        parameters: Optional[dict] = None,
        data: Optional[dict] = None,
        entry_id: Optional[str] = None,
    ) -> None:
        if not isinstance(structure, Crystal):
            raise TypeError("structure must be a Crystal")
        self.structure = structure.copy()
        super().__init__(self.structure.composition, energy, correction, parameters, data, entry_id)

    def as_dict(self) -> Dict[str, Any]:
        result = super().as_dict()
        result["structure"] = self.structure.as_dict()
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComputedStructureEntry":
        decoder = MontyDecoder()
        return cls(
            decoder.process_decoded(d["structure"]),
            d["energy"],
            correction=d.get("correction", 0.0),
            parameters=decoder.process_decoded(d.get("parameters")),
            data=decoder.process_decoded(d.get("data")),
            entry_id=d.get("entry_id"),
        )
