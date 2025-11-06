"""
Examples for building nanostructures.

This example demonstrates:
- Building nanotubes from 2D materials
- Building carbon nanotubes
- Building twisted bilayer structures
"""

from matsimpy.builders.nanostructure import (
    build_nanotube,
    build_carbon_nanotube,
    build_twisted_bilayer
)
from matsimpy.core import Crystal, Lattice
import numpy as np

print("=" * 70)
print("MatSimPy Builders - Nanostructure Examples")
print("=" * 70)

# ============================================================================
# Example 1: Carbon Nanotubes
# ============================================================================
print("\n1. Carbon Nanotubes")
print("-" * 70)

# Zigzag nanotube (n, 0)
cnt_zigzag = build_carbon_nanotube(10, 0, length=1)
print(f"Zigzag (10, 0) CNT: {cnt_zigzag.formula}")
print(f"  Atoms: {len(cnt_zigzag)}")
print(f"  Diameter: ~{cnt_zigzag.lattice.a:.2f} Å")

# Armchair nanotube (n, n)
cnt_armchair = build_carbon_nanotube(6, 6, length=1)
print(f"\nArmchair (6, 6) CNT: {cnt_armchair.formula}")
print(f"  Atoms: {len(cnt_armchair)}")

# Chiral nanotube
cnt_chiral = build_carbon_nanotube(7, 3, length=1)
print(f"\nChiral (7, 3) CNT: {cnt_chiral.formula}")
print(f"  Atoms: {len(cnt_chiral)}")

# ============================================================================
# Example 2: Nanotubes from 2D Materials
# ============================================================================
print("\n\n2. Nanotubes from 2D Materials")
print("-" * 70)

# Create h-BN monolayer
a_bn = 2.50
lattice_bn = Lattice(np.array([
    [a_bn, 0, 0],
    [-a_bn/2, a_bn*np.sqrt(3)/2, 0],
    [0, 0, 20.0]
]))
hbn = Crystal(['B', 'N'], [[0.0, 0.0, 0.0], [1.0/3.0, 2.0/3.0, 0.0]], 
              lattice_bn, coords_are_cartesian=False)

# Build h-BN nanotube
hbn_tube = build_nanotube(hbn, (10, 0), length=None)
print(f"h-BN nanotube (10, 0): {hbn_tube.formula}")
print(f"  Atoms: {len(hbn_tube)}")
print(f"  B: {sum(1 for s in hbn_tube.species if s == 'B')}")
print(f"  N: {sum(1 for s in hbn_tube.species if s == 'N')}")

# ============================================================================
# Example 3: Twisted Bilayer Structures
# ============================================================================
print("\n\n3. Twisted Bilayer Structures")
print("-" * 70)

# Create a simple 2D layer (graphene-like)
a = 2.46
lattice_2d = Lattice(np.array([
    [a, 0, 0],
    [-a/2, a*np.sqrt(3)/2, 0],
    [0, 0, 20.0]
]))
graphene = Crystal(['C', 'C'], [[0.0, 0.0, 0.0], [1.0/3.0, 2.0/3.0, 0.0]], 
                   lattice_2d, coords_are_cartesian=False)

# Create twisted bilayer with 10.9° twist angle (near magic angle)
twisted = build_twisted_bilayer(graphene, twist_angle=10.9, layer_spacing=3.35)
print(f"Twisted bilayer (10.9°): {twisted.formula}")
print(f"  Atoms: {len(twisted)}")
print(f"  Layer spacing: {twisted.lattice.c:.2f} Å")

# ============================================================================
# Example 4: Different Chirality Effects
# ============================================================================
print("\n\n4. Different Chirality Effects")
print("-" * 70)

chiralities = [
    (10, 0),   # Zigzag
    (10, 10),  # Armchair
    (7, 3),    # Chiral
]

print(f"{'Chirality':<15} {'Formula':<15} {'Atoms':<8}")
print("-" * 40)
for n, m in chiralities:
    tube = build_carbon_nanotube(n, m, length=1)
    print(f"({n}, {m}):<15} {tube.formula:<15} {len(tube):<8}")

print("\n" + "=" * 70)
print("Nanostructure examples completed!")
print("=" * 70)

