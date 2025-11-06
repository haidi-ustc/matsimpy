"""
Examples for building surface structures.

This example demonstrates:
- Creating surface slabs
- Adding adsorbates
- Working with different surface orientations
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.surface import generate_slab, add_adsorbate
from matsimpy.transformation.structural import make_supercell

print("=" * 70)
print("MatSimPy Builders - Surface Structures Examples")
print("=" * 70)

# ============================================================================
# Example 1: Creating Surface Slabs
# ============================================================================
print("\n1. Creating Surface Slabs")
print("-" * 70)

# Start with bulk FCC Cu
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
print(f"Bulk FCC Cu: {fcc_cu.formula}, {len(fcc_cu)} atoms")

# Create (111) surface slab
slab_111 = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)
print(f"\n(111) surface slab:")
print(f"  Formula: {slab_111.formula}")
print(f"  Number of atoms: {len(slab_111)}")
print(f"  Lattice c (thickness): {slab_111.lattice.c:.2f} Å")

# Create (100) surface slab
slab_100 = generate_slab(fcc_cu, (1, 0, 0), min_slab_size=10.0, min_vacuum_size=15.0)
print(f"\n(100) surface slab:")
print(f"  Formula: {slab_100.formula}")
print(f"  Number of atoms: {len(slab_100)}")
print(f"  Lattice c (thickness): {slab_100.lattice.c:.2f} Å")

# Create (110) surface slab
slab_110 = generate_slab(fcc_cu, (1, 1, 0), min_slab_size=10.0, min_vacuum_size=15.0)
print(f"\n(110) surface slab:")
print(f"  Formula: {slab_110.formula}")
print(f"  Number of atoms: {len(slab_110)}")
print(f"  Lattice c (thickness): {slab_110.lattice.c:.2f} Å")

# ============================================================================
# Example 2: Adding Adsorbates
# ============================================================================
print("\n\n2. Adding Adsorbates to Surfaces")
print("-" * 70)

# Create a simple slab
slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=8.0, min_vacuum_size=10.0)
print(f"Initial slab: {slab.formula}, {len(slab)} atoms")

# Add oxygen atom as adsorbate
slab_with_o = add_adsorbate(slab, 'O', position=(0.5, 0.5), height=2.0)
print(f"\nAfter adding O adsorbate:")
print(f"  Formula: {slab_with_o.formula}")
print(f"  Number of atoms: {len(slab_with_o)}")
print(f"  O atoms: {sum(1 for s in slab_with_o.species if s == 'O')}")

# Add multiple adsorbates
slab_multi = add_adsorbate(slab, 'H', position=(0.25, 0.25), height=1.8)
slab_multi = add_adsorbate(slab_multi, 'H', position=(0.75, 0.75), height=1.8)
print(f"\nAfter adding 2 H adsorbates:")
print(f"  Formula: {slab_multi.formula}")
print(f"  Number of atoms: {len(slab_multi)}")
print(f"  H atoms: {sum(1 for s in slab_multi.species if s == 'H')}")

# ============================================================================
# Example 3: Different Surface Orientations
# ============================================================================
print("\n\n3. Comparing Different Surface Orientations")
print("-" * 70)

orientations = [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
print(f"{'Orientation':<15} {'Atoms':<8} {'Surface Area (Å²)':<18}")
print("-" * 45)

for miller in orientations:
    slab = generate_slab(fcc_cu, miller, min_slab_size=8.0, min_vacuum_size=10.0)
    surface_area = slab.lattice.a * slab.lattice.b
    print(f"{str(miller):<15} {len(slab):<8} {surface_area:<18.2f}")

# ============================================================================
# Example 4: Creating Larger Surface Cells
# ============================================================================
print("\n\n4. Creating Larger Surface Cells")
print("-" * 70)

# Create a (1x1) slab
small_slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=8.0, min_vacuum_size=10.0)
print(f"(1x1) slab: {len(small_slab)} atoms")

# Make a (2x2) supercell
large_slab = make_supercell(small_slab, [2, 2, 1])
print(f"(2x2) supercell: {len(large_slab)} atoms")

# Add adsorbate to larger cell
large_slab_ads = add_adsorbate(large_slab, 'O', position=(0.5, 0.5), height=2.0)
print(f"(2x2) with adsorbate: {len(large_slab_ads)} atoms")

print("\n" + "=" * 70)
print("Surface structure examples completed!")
print("=" * 70)

