"""
Examples for geometric transformations.

This example demonstrates:
- Translation operations
- Rotation operations
- Combining transformations
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.molecule import build_tetrahedral
from matsimpy.transformation.geometric import translate, rotate

print("=" * 70)
print("MatSimPy Transformations - Geometric Examples")
print("=" * 70)

# ============================================================================
# Example 1: Translation
# ============================================================================
print("\n1. Translation Operations")
print("-" * 70)

# Create a crystal
crystal = from_prototype('fcc', 'Cu', 3.61)
print(f"Original crystal: {len(crystal)} atoms")

# Translate by a vector
translation_vector = [1.0, 2.0, 3.0]
translated = translate(crystal, translation_vector, inplace=False)
print(f"\nTranslated by {translation_vector}:")
print(f"  Original position [0]: {crystal.cart_positions[0]}")
print(f"  Translated position [0]: {translated.cart_positions[0]}")

# In-place translation
translate(crystal, [0.5, 0.5, 0.5], inplace=True)
print(f"\nIn-place translation by [0.5, 0.5, 0.5]")
print(f"  New position [0]: {crystal.cart_positions[0]}")

# ============================================================================
# Example 2: Rotation
# ============================================================================
print("\n\n2. Rotation Operations")
print("-" * 70)

# Create a molecule
molecule = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
original_pos = molecule.positions[0].copy()
print(f"Original molecule: {molecule.formula}")
print(f"  First atom position: {original_pos}")

# Rotate around z-axis
rotated = rotate(molecule, angle=90.0, axis=[0, 0, 1], inplace=False)
print(f"\nRotated 90° around z-axis:")
print(f"  Original position [0]: {original_pos}")
print(f"  Rotated position [0]: {rotated.positions[0]}")

# Rotate around custom axis
rotated2 = rotate(molecule, angle=45.0, axis=[1, 1, 0], inplace=False)
print(f"\nRotated 45° around [1,1,0] axis:")
print(f"  New position [0]: {rotated2.positions[0]}")

# In-place rotation
rotate(molecule, angle=180.0, axis=[0, 1, 0], inplace=True)
print(f"\nIn-place rotation 180° around y-axis")
print(f"  New position [0]: {molecule.positions[0]}")

# ============================================================================
# Example 3: Rotation Around Center
# ============================================================================
print("\n\n3. Rotation Around Center")
print("-" * 70)

# Get center of mass
com = molecule.get_center_of_mass()
print(f"Molecule center of mass: {com}")

# Rotate around center
rotated_center = rotate(molecule, angle=90.0, axis=[0, 0, 1], 
                        center=com, inplace=False)
print(f"\nRotated 90° around z-axis at center:")
print(f"  Center of mass: {rotated_center.get_center_of_mass()}")
print(f"  (Should be same as original)")

# ============================================================================
# Example 4: Combining Transformations
# ============================================================================
print("\n\n4. Combining Transformations")
print("-" * 70)

# Create fresh molecule
molecule = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
pos_before = molecule.positions[0].copy()

# Translate then rotate
molecule = translate(molecule, [1.0, 1.0, 1.0], inplace=False)
molecule = rotate(molecule, angle=90.0, axis=[0, 0, 1], inplace=False)

print(f"After translate then rotate:")
print(f"  Original position [0]: {pos_before}")
print(f"  Final position [0]: {molecule.positions[0]}")

# Rotate then translate
molecule2 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
molecule2 = rotate(molecule2, angle=90.0, axis=[0, 0, 1], inplace=False)
molecule2 = translate(molecule2, [1.0, 1.0, 1.0], inplace=False)

print(f"\nAfter rotate then translate:")
print(f"  Original position [0]: {pos_before}")
print(f"  Final position [0]: {molecule2.positions[0]}")
print(f"  (Note: different order gives different result)")

# ============================================================================
# Example 5: Crystal Translation (with PBC)
# ============================================================================
print("\n\n5. Crystal Translation (Periodic Boundary Conditions)")
print("-" * 70)

crystal = from_prototype('fcc', 'Cu', 3.61)
original_frac = crystal.frac_positions[0].copy()

# Translate crystal
translated_crystal = translate(crystal, [1.0, 2.0, 3.0], inplace=False)
print(f"Original fractional position [0]: {original_frac}")
print(f"Translated fractional position [0]: {translated_crystal.frac_positions[0]}")

# Note: For crystals, translation affects cartesian coordinates
# but fractional coordinates are relative to lattice

print("\n" + "=" * 70)
print("Geometric transformation examples completed!")
print("=" * 70)

