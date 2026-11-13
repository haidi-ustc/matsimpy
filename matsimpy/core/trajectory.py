"""An immutable sequence of crystal structure frames.

Per-frame data (energies, forces, ...) lives in each frame's ``metadata``;
the separate ``frame_properties`` list of 0.8.x was removed in 0.9.0.
"""

from typing import Any, Dict, Iterable, Iterator, Optional, Sequence, Tuple, Union, overload

import numpy as np

from monty.json import MSONable, MontyDecoder

from .crystal import Crystal


class Trajectory(MSONable):
    """Sequence-like container holding independent copies of crystal frames."""

    def __init__(
        self,
        frames: Iterable[Crystal],
        constant_lattice: bool = False,
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
        if copied:
            species0 = tuple(copied[0].species)
            for k, frame in enumerate(copied[1:], start=1):
                if tuple(frame.species) != species0:
                    raise ValueError(
                        f"Trajectory frame {k} has species {frame.formula} "
                        f"({len(frame)} atoms); all frames must have the same atoms "
                        f"in the same order as frame 0 ({copied[0].formula}, {len(species0)} atoms)"
                    )
        for name, value in (("charge", charge), ("spin", spin),
                            ("spin_multiplicity", spin_multiplicity), ("time_step", time_step)):
            if value is not None and (
                isinstance(value, (bool, np.bool_))
                or not isinstance(value, (int, float, np.integer, np.floating))
                or not np.isfinite(value)
            ):
                raise ValueError(f"{name} must be a finite number or None, got {value!r}")
        if time_step is not None and time_step <= 0:
            raise ValueError(f"time_step must be positive, got {time_step}")
        if coords_are_displacement and base_positions is None:
            raise ValueError("coords_are_displacement=True requires base_positions")
        self._frames: Tuple[Crystal, ...] = copied
        self.constant_lattice = bool(constant_lattice)
        self.charge = charge
        self.spin = spin
        self.spin_multiplicity = spin_multiplicity
        self.time_step = time_step
        self.coords_are_displacement = bool(coords_are_displacement)
        if base_positions is None:
            self._base_positions = None
        else:
            self._base_positions = np.array(base_positions, dtype=float, copy=True)
            n_atoms = len(copied[0]) if copied else self._base_positions.shape[0]
            if self._base_positions.shape != (n_atoms, 3):
                raise ValueError(
                    f"base_positions must have shape ({n_atoms}, 3), got {self._base_positions.shape}"
                )
            if not np.all(np.isfinite(self._base_positions)):
                raise ValueError("base_positions must be finite")
            self._base_positions.flags.writeable = False
        self._frozen = True

    def __setattr__(self, name: str, value: Any) -> None:
        # Trajectory is an immutable value container: all state is fixed in
        # __init__ (0.8.0 allowed e.g. ``traj.constant_lattice = True`` without
        # re-validating the frames).
        if self.__dict__.get("_frozen", False):
            raise AttributeError(
                f"Trajectory is immutable; cannot set {name!r}. Build a new Trajectory."
            )
        object.__setattr__(self, name, value)

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        base = self.__dict__.get("_base_positions")
        if isinstance(base, np.ndarray):
            base.flags.writeable = False

    @property
    def base_positions(self) -> Optional[np.ndarray]:
        """Read-only view of the displacement reference positions, or ``None``."""
        if self._base_positions is None:
            return None
        view = self._base_positions.view()
        view.flags.writeable = False
        return view

    @staticmethod
    def _copy_frame(frame: Crystal) -> Crystal:
        if not isinstance(frame, Crystal):
            raise TypeError("trajectory frames must be Crystal objects")
        return frame.copy()  # metadata (e.g. per-frame forces) travels with the frame

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

    @overload
    def __getitem__(self, index: Union[Sequence[int], np.ndarray]) -> "Trajectory": ...

    def __getitem__(
        self, index: Union[int, slice, Sequence[int], np.ndarray]
    ) -> Union[Crystal, "Trajectory"]:
        if isinstance(index, (int, np.integer)):
            return self._copy_frame(self._frames[int(index)])

        if isinstance(index, slice):
            indices = list(range(len(self)))[index]
        else:
            array = np.asarray(index)
            if array.ndim != 1 or not np.issubdtype(array.dtype, np.integer):
                raise TypeError("trajectory indices must be a one-dimensional integer sequence")
            indices = [int(value) for value in array]

        return self.__class__(
            (self._frames[value] for value in indices),
            constant_lattice=self.constant_lattice,
            charge=self.charge,
            spin=self.spin,
            spin_multiplicity=self.spin_multiplicity,
            time_step=self.time_step,
            coords_are_displacement=self.coords_are_displacement,
            # Base positions describe the sites shared by every displacement
            # frame, so frame selection copies rather than subsets them.
            base_positions=self.base_positions,
        )

    def __iter__(self) -> Iterator[Crystal]:
        # Yield independent copies, consistent with __getitem__; handing out the
        # internal frames let callers mutate the trajectory through them.
        return (self._copy_frame(frame) for frame in self._frames)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "frames": [
                {"structure": frame.as_dict()}  # frame metadata is inside as_dict()
                for frame in self._frames
            ],
            "constant_lattice": self.constant_lattice,
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
            # Readers for older files: direct frames, and frames with a separate
            # "extra_properties" block (<=0.8.6), which now becomes frame metadata.
            if isinstance(item, dict) and "structure" in item:
                frame = decoder.process_decoded(item["structure"])
                extras = decoder.process_decoded(item.get("extra_properties"))
                if extras:
                    frame = frame.with_metadata(**extras)
            else:
                frame = decoder.process_decoded(item)
            frames.append(frame)
        # <=0.8.7 files kept per-frame dicts in a parallel "frame_properties" list.
        legacy = decoder.process_decoded(d.get("frame_properties")) or []
        frames = [f.with_metadata(**props) if props else f for f, props in zip(frames, legacy)] + frames[len(legacy):]
        return cls(
            frames,
            constant_lattice=d.get("constant_lattice", False),
            charge=d.get("charge"), spin=d.get("spin"),
            spin_multiplicity=d.get("spin_multiplicity"), time_step=d.get("time_step"),
            coords_are_displacement=d.get("coords_are_displacement", False),
            base_positions=d.get("base_positions"),
        )
