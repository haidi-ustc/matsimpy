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
    """A scalar or three-component magnetic moment."""

    def __init__(self, moment):
        values = np.asarray(moment if np.ndim(moment) else [0.0, 0.0, moment], dtype=float)
        if values.shape != (3,):
            raise ValueError("magnetic moment must be a scalar or length-3 vector")
        self.moment = values

    def __getitem__(self, index):
        return self.moment[index]

    def __iter__(self):
        return iter(self.moment)

    def __float__(self):
        return float(self.moment[2])

    def __eq__(self, other):
        return isinstance(other, Magmom) and np.array_equal(self.moment, other.moment)

    def as_dict(self):
        return {
            "@module": type(self).__module__,
            "@class": type(self).__name__,
            "moment": self.moment.tolist(),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["moment"])
