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
    def __init__(self, value):
        values = value if isinstance(value, (list, tuple, np.ndarray)) else [value]
        self.components = tuple(float(component) for component in values)
