"""
Examples for building nanostructures.

This example demonstrates:
- Carbon nanotubes from chirality indices
- Nanotubes rolled from any 2D sheet: hexagonal, square, rectangular, and thick
  (three-layer) sheets such as MoS2
- Twisted bilayers and multilayers in commensurate supercells
"""

import numpy as np

from matsimpy.builders.nanostructure import (
    build_carbon_nanotube,
    build_magic_angle_twisted,
    build_nanotube,
    build_twisted_bilayer,
    build_twisted_multilayer,
    commensurate_twist_angles,
)
from matsimpy.core import Crystal, Lattice

print("=" * 70)
print("MatSimPy Builders - Nanostructure Examples")
print("=" * 70)

# ============================================================================
# Example 1: Carbon nanotubes
# ============================================================================
print("\n1. Carbon Nanotubes")
print("-" * 70)
print(f"{'Chirality':<12} {'Atoms':>6} {'Diameter (A)':>14} {'Period (A)':>12}")
for n, m in [(10, 0), (6, 6), (7, 3)]:
    tube = build_carbon_nanotube(n, m)
    diameter = 2 * tube.metadata["radius"]
    print(f"({n}, {m}){'':<6} {len(tube):>6} {diameter:>14.3f} {tube.lattice.c:>12.3f}")

longer = build_carbon_nanotube(6, 6, length=20.0)
print(f"(6, 6) at least 20 A long: {len(longer)} atoms, {longer.lattice.c:.2f} A")

# ============================================================================
# Example 2: Nanotubes from other 2D lattices
# ============================================================================
print("\n\n2. Nanotubes from 2D Sheets")
print("-" * 70)

# h-BN in a 120-degree hexagonal basis; the sheet only needs a and b in the xy-plane
hbn = Crystal(["B", "N"], [[1 / 3, 2 / 3, 0.5], [2 / 3, 1 / 3, 0.5]], Lattice.hexagonal(2.50, 20.0))
bnnt = build_nanotube(hbn, (8, 0))
print(f"h-BN (8, 0): {bnnt.formula}, translation indices {bnnt.metadata['translation']}")

# Square lattice
square = Crystal(["Cu"], [[0.0, 0.0, 0.5]], Lattice.tetragonal(2.55, 20.0))
for chirality in [(10, 0), (4, 3)]:
    tube = build_nanotube(square, chirality)
    print(f"square {chirality}: {len(tube)} atoms, period {tube.lattice.c:.3f} A")

# Rectangular lattice (a puckered, phosphorene-like sheet: two heights)
rectangular = Crystal(
    ["P", "P", "P", "P"],
    [[0.0, 0.0, 0.45], [0.5, 0.18, 0.45], [0.0, 0.5, 0.55], [0.5, 0.68, 0.55]],
    Lattice.orthorhombic(3.30, 4.60, 20.0),
)
for chirality in [(0, 8), (12, 0)]:
    tube = build_nanotube(rectangular, chirality)
    print(f"rectangular {chirality}: {len(tube)} atoms, period {tube.lattice.c:.3f} A")

# MoS2: the S layers above and below Mo become an outer and an inner shell
mos2 = Crystal(
    ["Mo", "S", "S"],
    [[1 / 3, 2 / 3, 0.5], [2 / 3, 1 / 3, 0.5 + 1.56 / 20], [2 / 3, 1 / 3, 0.5 - 1.56 / 20]],
    Lattice.hexagonal(3.16, 20.0),
)
tube = build_nanotube(mos2, (10, 10))
center = np.array([tube.lattice.a / 2, tube.lattice.b / 2])
radii = np.linalg.norm(tube.cart_positions[:, :2] - center, axis=1)
shells = ", ".join(f"{r:.2f}" for r in np.unique(np.round(radii, 2)))
print(f"MoS2 (10, 10): {tube.formula}, shell radii {shells} A")

# ============================================================================
# Example 3: Twisted bilayers and multilayers
# ============================================================================
print("\n\n3. Twisted Layers")
print("-" * 70)

graphene = Crystal(["C", "C"], [[0.0, 0.0, 0.5], [1 / 3, 2 / 3, 0.5]], Lattice.hexagonal(2.46, 20.0))

print("Commensurate angles of graphene with at most 400 atoms:")
for item in commensurate_twist_angles(graphene, max_atoms=400, max_angle=30):
    print(f"  {item['angle']:8.4f} deg  {item['atoms']:>4} atoms")

tblg = build_twisted_bilayer(graphene, 21.786789)
print(f"\nTwisted bilayer at 21.79 deg: {len(tblg)} atoms, "
      f"realized angles {tblg.metadata['twist_angles']}")

magic = build_magic_angle_twisted(graphene, 31, 32)
print(f"Magic-angle (31, 32): {magic.metadata['twist_angles'][1]:.4f} deg, {len(magic)} atoms")

# An arbitrary angle: accept a nearby commensurate angle or a little strain
near = build_twisted_bilayer(graphene, 5.0, max_strain=1e-3, angle_tolerance=0.05)
print(f"Near 5 deg: {near.metadata['twist_angles'][1]:.4f} deg, {len(near)} atoms, "
      f"strain {max(near.metadata['strain']):.1e}")

# Graphene on h-BN: the 1.8% mismatch gives a 57 x 57 / 56 x 56 moire cell
hbn_matched = Crystal(["B", "N"], [[1 / 3, 2 / 3, 0.5], [2 / 3, 1 / 3, 0.5]], Lattice.hexagonal(2.504, 20.0))
hetero = build_twisted_bilayer(graphene, 0.0, top_layer=hbn_matched, max_atoms=14000)
print(f"Graphene/h-BN: {hetero.formula}, h-BN strain {hetero.metadata['strain'][1]:.1e}")

trilayer = build_twisted_multilayer(graphene, 3, [21.786789, -21.786789])
print(f"Alternating twisted trilayer: {len(trilayer)} atoms, "
      f"angles {trilayer.metadata['twist_angles']}")

print("\n" + "=" * 70)
print("Nanostructure examples completed!")
print("=" * 70)
