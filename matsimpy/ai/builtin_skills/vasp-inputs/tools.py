"""Tools of the vasp-inputs skill."""

import math

from matsimpy.core import Crystal
from matsimpy.utils.tooling import tool


@tool
def kpoint_mesh(structure: Crystal, kppa: int = 1000) -> list[int]:
    """Monkhorst-Pack mesh for a k-point density per reciprocal atom.

    Divisions are inversely proportional to the lattice vector lengths, so the
    k-point spacing is about the same along each axis.  Same rule as pymatgen's
    ``Kpoints.automatic_density``.

    Args:
        structure: Crystal to calculate.
        kppa: k-points per reciprocal atom (mesh points x atoms), e.g. 1000.
    """
    if kppa <= 0:
        raise ValueError("kppa must be positive")
    if abs(math.floor(kppa ** (1 / 3) + 0.5) ** 3 - kppa) < 1:
        kppa *= 1.01  # a perfect cube would put the divisions exactly on a rounding edge
    lattice = structure.lattice
    lengths = (lattice.a, lattice.b, lattice.c)
    scale = (kppa / len(structure) * lengths[0] * lengths[1] * lengths[2]) ** (1 / 3)
    return [math.floor(max(scale / length, 1)) for length in lengths]
