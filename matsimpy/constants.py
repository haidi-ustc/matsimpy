"""
Package-wide physical and numerical constants for MatSimPy.

Placing constants here (package root) means every subpackage can import
them with a single, dependency-free import:

    from matsimpy.constants import POSITION_TOL, LATTICE_TOL

No subpackage dependency is introduced and circular-import risk is zero.
"""

# Tolerance for comparing atomic positions (Angstroms).
# Used in Structure.__eq__ and Structure.__hash__.
# __hash__ rounds to 7 decimal places (bucket = 5e-8); POSITION_TOL = 1e-8
# satisfies the hash contract: 1e-8 < 5e-8, so any two positions that are
# "equal" under __eq__ will round identically and produce the same hash.
POSITION_TOL: float = 1e-8

# Tolerance for comparing lattice vectors (Angstroms).
# Used in Lattice.__eq__ and in Structure.__eq__ when comparing lattice matrices.
# Lattice.__hash__ rounds to 5 decimal places (bucket = 5e-6); LATTICE_TOL = 1e-6
# satisfies the hash contract: 1e-6 < 5e-6.
LATTICE_TOL: float = 1e-6
