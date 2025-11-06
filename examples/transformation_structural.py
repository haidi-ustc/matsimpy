"""
Examples for structural transformations.

This example demonstrates:
- Supercell generation
- Atom manipulation
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.structural import (
    make_supercell,
    swap_atoms
)

print("=" * 70)
print("MatSimPy Transformations - Structural Examples")
print("=" * 70)

# ============================================================================
# Example 1: Supercell Generation
# ============================================================================
print("\n1. Supercell Generation")
print("-" * 70)

# Create base structure
crystal = from_prototype('fcc', 'Cu', 3.61)
print(f"Base structure: {crystal.formula}, {len(crystal)} atoms")
print(f"  Lattice: a={crystal.lattice.a:.2f} Å")

# Create 2x2x2 supercell
supercell_2x2x2 = make_supercell(crystal, [2, 2, 2])
print(f"\n2x2x2 supercell: {supercell_2x2x2.formula}, {len(supercell_2x2x2)} atoms")
print(f"  Lattice: a={supercell_2x2x2.lattice.a:.2f} Å")
print(f"  Volume ratio: {supercell_2x2x2.volume / crystal.volume:.1f}x")

# Create 3x3x3 supercell
supercell_3x3x3 = make_supercell(crystal, [3, 3, 3])
print(f"\n3x3x3 supercell: {supercell_3x3x3.formula}, {len(supercell_3x3x3)} atoms")
print(f"  Volume ratio: {supercell_3x3x3.volume / crystal.volume:.1f}x")

# Create anisotropic supercell
supercell_aniso = make_supercell(crystal, [2, 2, 4])
print(f"\n2x2x4 supercell: {supercell_aniso.formula}, {len(supercell_aniso)} atoms")
print(f"  Lattice: a={supercell_aniso.lattice.a:.2f} Å, c={supercell_aniso.lattice.c:.2f} Å")

# ============================================================================
# Example 2: Atom Swapping
# ============================================================================
print("\n\n2. Atom Swapping")
print("-" * 70)

# Create binary compound
nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
print(f"Original: {nacl.formula}")
print(f"  Species: {list(nacl.species[:4])}")

# Swap two atoms
swapped = swap_atoms(nacl, 0, 1, inplace=False)
print(f"\nAfter swapping atoms 0 and 1:")
print(f"  Formula: {swapped.formula}")
print(f"  Species: {list(swapped.species[:4])}")

# ============================================================================
# Example 3: Large Supercells
# ============================================================================
print("\n\n3. Large Supercells")
print("-" * 70)

# Create progressively larger supercells
base = from_prototype('fcc', 'Cu', 3.61)
sizes = [(2, 2, 2), (4, 4, 4), (5, 5, 5)]

print(f"{'Size':<12} {'Atoms':<10} {'Volume (Å³)':<15}")
print("-" * 40)
for size in sizes:
    supercell = make_supercell(base, size)
    print(f"{str(size):<12} {len(supercell):<10} {supercell.volume:<15.2f}")

print("\n" + "=" * 70)
print("Structural transformation examples completed!")
print("=" * 70)

