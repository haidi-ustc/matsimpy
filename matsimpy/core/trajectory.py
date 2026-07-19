"""An immutable sequence of crystal structure frames."""

from copy import deepcopy
from typing import Any, Dict, Iterable, Iterator, Tuple, Union, overload

from monty.json import MSONable, MontyDecoder, jsanitize

from .crystal import Crystal


class Trajectory(MSONable):
    """Sequence-like container holding independent copies of crystal frames."""

    def __init__(self, frames: Iterable[Crystal], constant_lattice: bool = False) -> None:
        copied = tuple(self._copy_frame(frame) for frame in frames)
        if constant_lattice and copied:
            lattice = copied[0].lattice
            if any(frame.lattice != lattice for frame in copied[1:]):
                raise ValueError("constant_lattice=True requires identical lattices")
        self._frames: Tuple[Crystal, ...] = copied
        self.constant_lattice = bool(constant_lattice)

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
        return cls(frames, constant_lattice=d.get("constant_lattice", False))
