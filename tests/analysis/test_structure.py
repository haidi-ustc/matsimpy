"""Tests for matsimpy.analysis.structure.StructureAnalyzer."""

import numpy as np
import pytest

from matsimpy.analysis.structure import StructureAnalyzer
from matsimpy.core import Crystal, Lattice, Molecule


@pytest.mark.parametrize("structure, distance", [
    (Molecule(["O", "H"], [[0, 0, 0], [0.96, 0, 0]]), 0.96),
    (Crystal(["Na", "Cl"], [[0, 0, 0], [0.9, 0, 0]], Lattice.cubic(4.0)), 0.4),  # through the boundary
    (Crystal(["Na", "Cl"], [[0, 0, 0], [0.9, 0, 0]], Lattice.cubic(4.0), pbc=[False] * 3), 3.6),
    (Crystal(["Cu", "H"], [[0, 0, 0], [0, 0.5, 0]], Lattice([[4, 0, 0], [16, 0.4, 0], [0, 0, 4]])), 0.2),
])
def test_pair_distance(structure, distance):
    assert StructureAnalyzer(structure).pair_distance(0, 1) == pytest.approx(distance)
