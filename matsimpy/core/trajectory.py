"""An immutable sequence of crystal structure frames."""

from copy import deepcopy
from typing import Any, Dict, Iterable, Iterator, Optional, Sequence, Tuple, Union, overload

import numpy as np

from monty.json import MSONable, MontyDecoder, jsanitize

from .crystal import Crystal


class Trajectory(MSONable):
    """Sequence-like container holding independent copies of crystal frames."""

    def __init__(
        self,
        frames: Iterable[Crystal],
        constant_lattice: bool = False,
        frame_properties: Optional[Sequence[dict]] = None,
        charge: Optional[float] = None,
        spin: Optional[float] = None,
        spin_multiplicity: Optional[float] = None,
        time_step: Optional[float] = None,
        coords_are_displacement: bool = False,
        base_positions: Optional[Sequence[Sequence[float]]] = None,
    ) -> None:
        copied = tuple(self._copy_frame(frame) for frame in frames)
        if constant_lattice and copied:
            lattice = copied[0].lattice
            if any(frame.lattice != lattice for frame in copied[1:]):
                raise ValueError("constant_lattice=True requires identical lattices")
        self._frames: Tuple[Crystal, ...] = copied
        self.constant_lattice = bool(constant_lattice)
        properties = frame_properties if frame_properties is not None else [{} for _ in copied]
        if len(properties) != len(copied):
            raise ValueError("frame_properties must match the number of frames")
        self.frame_properties = tuple(deepcopy(value) for value in properties)
        self.charge = charge
        self.spin = spin
        self.spin_multiplicity = spin_multiplicity
        self.time_step = time_step
        self.coords_are_displacement = bool(coords_are_displacement)
        self.base_positions = None if base_positions is None else np.asarray(base_positions, dtype=float).copy()

    @staticmethod
    def _copy_frame(frame: Crystal) -> Crystal:
        if not isinstance(frame, Crystal):
            raise TypeError("trajectory frames must be Crystal objects")
        copied = frame.copy()
        if hasattr(frame, "_extra_properties"):
            copied._extra_properties = deepcopy(frame._extra_properties)
        return copied

    @classmethod
    def from_structures(
        cls, structures: Iterable[Crystal], constant_lattice: bool = False
    ) -> "Trajectory":
        return cls(structures, constant_lattice=constant_lattice)

    def __len__(self) -> int:
        return len(self._frames)

    @overload
    def __getitem__(self, index: int) -> Crystal: ...

    @overload
    def __getitem__(self, index: slice) -> "Trajectory": ...

    def __getitem__(self, index: Union[int, slice]) -> Union[Crystal, "Trajectory"]:
        if isinstance(index, slice):
            return self.__class__(self._frames[index], constant_lattice=self.constant_lattice)
        return self._frames[index]

    def __iter__(self) -> Iterator[Crystal]:
        return iter(self._frames)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "frames": [
                {
                    "structure": frame.as_dict(),
                    "extra_properties": jsanitize(
                        getattr(frame, "_extra_properties", None),
                        strict=True,
                        recursive_msonable=True,
                    ),
                }
                for frame in self._frames
            ],
            "constant_lattice": self.constant_lattice,
            "frame_properties": jsanitize(self.frame_properties, strict=True),
            "charge": self.charge,
            "spin": self.spin,
            "spin_multiplicity": self.spin_multiplicity,
            "time_step": self.time_step,
            "coords_are_displacement": self.coords_are_displacement,
            "base_positions": None if self.base_positions is None else self.base_positions.tolist(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Trajectory":
        decoder = MontyDecoder()
        frames = []
        for item in d["frames"]:
            # Accept the original direct-frame representation as well as the
            # metadata-preserving representation.
            if isinstance(item, dict) and "structure" in item:
                frame = decoder.process_decoded(item["structure"])
                extras = decoder.process_decoded(item.get("extra_properties"))
                if extras is not None:
                    frame._extra_properties = extras
            else:
                frame = decoder.process_decoded(item)
            frames.append(frame)
        return cls(
            frames,
            constant_lattice=d.get("constant_lattice", False),
            frame_properties=decoder.process_decoded(d.get("frame_properties")),
            charge=d.get("charge"), spin=d.get("spin"),
            spin_multiplicity=d.get("spin_multiplicity"), time_step=d.get("time_step"),
            coords_are_displacement=d.get("coords_are_displacement", False),
            base_positions=d.get("base_positions"),
        )
