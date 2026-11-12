"""Tools of the cubic-supercell skill, loaded only when the skill is activated."""

from __future__ import annotations

import math

from matsimpy.core import Crystal
from matsimpy.utils.tooling import tool


@tool
def cubic_supercell_matrix(crystal: Crystal, min_atoms: int = 64) -> list[int]:
    """Choose a diagonal supercell with at least ``min_atoms`` atoms and near-equal lengths.

    Args:
        crystal: The crystal to repeat.
        min_atoms: The smallest acceptable number of atoms.

    Returns:
        The repetitions [na, nb, nc] along a, b and c.
    """
    lengths = (crystal.lattice.a, crystal.lattice.b, crystal.lattice.c)
    target = (min_atoms / len(crystal) * math.prod(lengths)) ** (1 / 3)
    repeats = [max(1, round(target / length)) for length in lengths]
    while len(crystal) * math.prod(repeats) < min_atoms:
        shortest = min(range(3), key=lambda i: repeats[i] * lengths[i])
        repeats[shortest] += 1
    return repeats
