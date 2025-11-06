"""
Examples for lattice transformations.

This example demonstrates:
- Applying strain
- Scaling lattices
- Lattice transformations
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.lattice import (
    apply_strain,
    scale_lattice,
    set_volume
)

print("=" * 70)
print("MatSimPy Transformations - Lattice Examples")
print("=" * 70)

# ============================================================================
# Example 1: Applying Strain
# ============================================================================
print("\n1. Applying Strain")
print("-" * 70)

# Create FCC Cu
crystal = from_prototype('fcc', 'Cu', 3.61)
original_volume = crystal.volume
print(f"Original: a={crystal.lattice.a:.2f} Å, volume={original_volume:.2f} Å³")

# Apply uniaxial strain
strained = apply_strain(crystal, [0.05, 0, 0], inplace=False)
print(f"\nUniaxial strain (5% along a):")
print(f"  New a: {strained.lattice.a:.2f} Å")
print(f"  New volume: {strained.volume:.2f} Å³")

# Apply volumetric strain
strained_vol = apply_strain(crystal, [0.02, 0.02, 0.02], inplace=False)
print(f"\nVolumetric strain (2% in all directions):")
print(f"  New a: {strained_vol.lattice.a:.2f} Å")
print(f"  New volume: {strained_vol.volume:.2f} Å³")

# ============================================================================
# Example 2: Scaling Lattice
# ============================================================================
print("\n\n2. Scaling Lattice")
print("-" * 70)

crystal = from_prototype('fcc', 'Cu', 3.61)
print(f"Original: a={crystal.lattice.a:.2f} Å")

# Scale by factor
scaled = scale_lattice(crystal, 1.1, inplace=False)
print(f"\nScale by 1.1:")
print(f"  New a: {scaled.lattice.a:.2f} Å")

# Scale by different factors for each axis
scaled_aniso = scale_lattice(crystal, [1.1, 1.1, 1.2], inplace=False)
print(f"\nAnisotropic scaling [1.1, 1.1, 1.2]:")
print(f"  New a: {scaled_aniso.lattice.a:.2f} Å")
print(f"  New c: {scaled_aniso.lattice.c:.2f} Å")

# ============================================================================
# Example 3: Setting Volume
# ============================================================================
print("\n\n3. Setting Volume")
print("-" * 70)

crystal = from_prototype('fcc', 'Cu', 3.61)
original_volume = crystal.volume
print(f"Original volume: {original_volume:.2f} Å³")

# Set to 150% of original volume
new_volume = original_volume * 1.5
resized = set_volume(crystal, new_volume, inplace=False)
print(f"\nSet volume to {new_volume:.2f} Å³ (150% of original):")
print(f"  New a: {resized.lattice.a:.2f} Å")
print(f"  New volume: {resized.volume:.2f} Å³")

print("\n" + "=" * 70)
print("Lattice transformation examples completed!")
print("=" * 70)

