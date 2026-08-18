"""Native electronic-structure primitives."""

from enum import IntEnum

import numpy as np
from monty.json import MSONable


class Spin(IntEnum):
    down = -1
    up = 1


class OrbitalType(IntEnum):
    s = 0
    p = 1
    d = 2
    f = 3


class Orbital(IntEnum):
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
    __slots__ = ("_components",)

    def __init__(self, value):
        values = value if isinstance(value, (list, tuple, np.ndarray)) else [value]
        components = tuple(float(component) for component in values)
        if len(components) not in (1, 3):
            raise ValueError("Magmom requires one or three components.")
        object.__setattr__(self, "_components", components)

    def __setattr__(self, name, value):
        if name == "_components" and not hasattr(self, "_components"):
            object.__setattr__(self, name, value)
            return
        raise AttributeError("Magmom is immutable.")

    @property
    def components(self):
        return self._components

    def __len__(self):
        return len(self.components)

    def __iter__(self):
        return iter(self.components)

    def __getitem__(self, index):
        return self.components[index]

    def __float__(self):
        if len(self.components) != 1:
            raise TypeError("Only scalar Magmom values can be converted to float.")
        return self.components[0]

    def __eq__(self, other):
        if not isinstance(other, Magmom):
            return NotImplemented
        return self.components == other.components

    def __repr__(self):
        if len(self.components) == 1:
            return f"Magmom({self.components[0]!r})"
        return f"Magmom({list(self.components)!r})"

    def as_dict(self):
        return {
            "@module": type(self).__module__,
            "@class": type(self).__name__,
            "value": list(self.components),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["value"])
