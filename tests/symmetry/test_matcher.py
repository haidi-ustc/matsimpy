from matsimpy.core import Crystal, Lattice
from matsimpy.symmetry.matcher import StructureMatcher


def test_structure_matcher_ignores_site_order():
    crystal = Crystal(
        ["Si", "Si"],
        [[0, 0, 0], [0.25, 0.25, 0.25]],
        Lattice.cubic(5.43),
    )
    reversed_crystal = Crystal(
        list(reversed(crystal.species)),
        list(reversed(crystal.frac_positions)),
        crystal.lattice,
    )

    assert StructureMatcher(stol=1e-5).fit(crystal, reversed_crystal)


def test_structure_matcher_wraps_periodic_fractional_sites():
    first = Crystal(["Si"], [[0.99, 0.0, 0.0]], Lattice.cubic(5.43))
    second = Crystal(["Si"], [[-0.01, 0.0, 0.0]], Lattice.cubic(5.43))

    assert StructureMatcher(stol=1e-5).fit(first, second)


def test_structure_matcher_rejects_different_lattices():
    first = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
    second = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.50))

    assert not StructureMatcher(ltol=1e-3).fit(first, second)


def test_structure_matcher_finds_non_greedy_site_assignment():
    first = Crystal(
        ["Si", "Si"],
        [[0.09, 0, 0], [0.0, 0, 0]],
        Lattice.cubic(10),
    )
    second = Crystal(
        ["Si", "Si"],
        [[0.05, 0, 0], [0.11, 0, 0]],
        Lattice.cubic(10),
    )

    assert StructureMatcher(stol=0.06).fit(first, second)
