"""Primitive electronic-structure types used by VASP parsers."""

from enum import IntEnum

import numpy as np
from monty.json import MSONable


class Spin(IntEnum):
    """Electronic spin channel."""

    up = 1
    down = -1


class OrbitalType(IntEnum):
    """Orbital angular-momentum type."""

    s = 0
    p = 1
    d = 2
    f = 3


class Orbital(IntEnum):
    """Specific orbitals in the order emitted by VASP."""

    s = 0
    py = 1
    pz = 2
    px = 3
    dxy = 4
    dyz = 5
    dz2 = 6
    dxz = 7
    dx2 = 8
    f_3 = 9
    f_2 = 10
    f_1 = 11
    f0 = 12
    f1 = 13
    f2 = 14
    f3 = 15


class Magmom(MSONable):
    """An immutable magnetic moment, stored as a Cartesian 3-vector.

    A scalar ``m`` (collinear moment) is stored as ``[0, 0, m]``, so
    ``float(magmom)`` is the z component. ``moment`` is a read-only array and
    attributes cannot be reassigned.
    """

    __slots__ = ("_moment",)

    def __init__(self, moment):
        values = np.array(moment if np.ndim(moment) else [0.0, 0.0, moment], dtype=float)
        if values.shape != (3,):
            raise ValueError("magnetic moment must be a scalar or length-3 vector")
        if not np.isfinite(values).all():
            raise ValueError("magnetic moment must be finite")
        values.flags.writeable = False
        object.__setattr__(self, "_moment", values)

    def __setattr__(self, name, value):
        raise AttributeError("Magmom is immutable")

    def __delattr__(self, name):
        raise AttributeError("Magmom is immutable")

    def __reduce__(self):
        # pickle/deepcopy rebuild through __init__ (attribute assignment is blocked)
        return (type(self), (self._moment.tolist(),))

    @property
    def moment(self) -> np.ndarray:
        """Read-only ``(3,)`` array of the moment components."""
        return self._moment

    def __getitem__(self, index):
        return self._moment[index]

    def __iter__(self):
        return iter(self._moment)

    def __len__(self):
        return 3

    def __float__(self):
        return float(self._moment[2])

    def __eq__(self, other):
        if not isinstance(other, Magmom):
            return NotImplemented
        return np.array_equal(self._moment, other._moment)

    __hash__ = None  # float value object: compare, don't hash (as Site/Lattice)

    def __repr__(self):
        return f"Magmom({self._moment.tolist()!r})"

    def as_dict(self):
        return {
            "@module": type(self).__module__,
            "@class": type(self).__name__,
            "moment": self.moment.tolist(),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["moment"])
