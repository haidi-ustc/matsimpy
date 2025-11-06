"""
Examples for symmetry analysis.

This example demonstrates:
- Getting symmetry information (space group, point group, crystal system)
- Getting standard conventional cell
- Comparing primitive and conventional cells
"""

from matsimpy.builders.bulk import from_prototype

print("=" * 70)
print("MatSimPy Symmetry Analysis - Basic Examples")
print("=" * 70)

# ============================================================================
# Example 1: Basic Symmetry Information
# ============================================================================
print("\n1. Basic Symmetry Information")
print("-" * 70)

# Create diamond structure (primitive cell)
diamond = from_prototype('diamond', 'Si', 5.43)
print(f"Structure: {diamond.formula}, {len(diamond)} atoms (primitive cell)")

# Get symmetry information
sym_info = diamond.get_symmetry_info()
print(f"\nSymmetry information:")
print(f"  Space group number: {sym_info['space_group_number']}")
print(f"  Space group symbol: {sym_info['space_group_symbol']}")
print(f"  Point group: {sym_info['point_group']}")
print(f"  Crystal system: {sym_info['crystal_system']}")
print(f"  Hall symbol: {sym_info['hall_symbol']}")

# ============================================================================
# Example 2: Conventional Cell
# ============================================================================
print("\n\n2. Standard Conventional Cell")
print("-" * 70)

# Start with primitive cell
primitive = from_prototype('diamond', 'Si', 5.43)
print(f"Primitive cell: {primitive.formula}, {len(primitive)} atoms")
print(f"  Lattice: a={primitive.lattice.a:.4f} Å, "
      f"α={primitive.lattice.alpha:.1f}°, "
      f"β={primitive.lattice.beta:.1f}°, "
      f"γ={primitive.lattice.gamma:.1f}°")

# Get conventional cell
conventional = primitive.get_conventional_cell()
print(f"\nConventional cell: {conventional.formula}, {len(conventional)} atoms")
print(f"  Lattice: a={conventional.lattice.a:.4f} Å, "
      f"α={conventional.lattice.alpha:.1f}°, "
      f"β={conventional.lattice.beta:.1f}°, "
      f"γ={conventional.lattice.gamma:.1f}°")
print(f"  Volume ratio: {conventional.volume / primitive.volume:.2f}x")

# ============================================================================
# Example 3: Different Crystal Systems
# ============================================================================
print("\n\n3. Symmetry Analysis for Different Crystal Systems")
print("-" * 70)

structures = {
    'FCC Cu': from_prototype('fcc', 'Cu', 3.61),
    'BCC Fe': from_prototype('bcc', 'Fe', 2.87),
    'Diamond Si': from_prototype('diamond', 'Si', 5.43),
    'Rocksalt NaCl': from_prototype('rocksalt', 'NaCl', 5.64),
}

print(f"{'Structure':<20} {'SG':<8} {'Point Group':<12} {'Crystal System':<15}")
print("-" * 70)
for name, struct in structures.items():
    sym_info = struct.get_symmetry_info()
    print(f"{name:<20} {sym_info['space_group_number']:<8} "
          f"{sym_info['point_group']:<12} {sym_info['crystal_system']:<15}")

# ============================================================================
# Example 4: Primitive vs Conventional Cell Comparison
# ============================================================================
print("\n\n4. Primitive vs Conventional Cell Comparison")
print("-" * 70)

# Create primitive cell
primitive = from_prototype('fcc', 'Cu', 3.61)
print(f"Primitive cell:")
print(f"  Formula: {primitive.formula}")
print(f"  Atoms: {len(primitive)}")
print(f"  Lattice type: Rhombohedral (primitive)")
print(f"  Lattice a: {primitive.lattice.a:.4f} Å")
print(f"  Lattice angles: α={primitive.lattice.alpha:.1f}°, "
      f"β={primitive.lattice.beta:.1f}°, γ={primitive.lattice.gamma:.1f}°")

# Get conventional cell
conventional = primitive.get_conventional_cell()
print(f"\nConventional cell:")
print(f"  Formula: {conventional.formula}")
print(f"  Atoms: {len(conventional)}")
print(f"  Lattice type: Cubic (conventional)")
print(f"  Lattice a: {conventional.lattice.a:.4f} Å")
print(f"  Lattice angles: α={conventional.lattice.alpha:.1f}°, "
      f"β={conventional.lattice.beta:.1f}°, γ={conventional.lattice.gamma:.1f}°")

print(f"\n  Volume: {primitive.volume:.2f} Å³ (primitive) vs "
      f"{conventional.volume:.2f} Å³ (conventional)")
print(f"  Volume ratio: {conventional.volume / primitive.volume:.1f}x")

# ============================================================================
# Example 5: Symmetry Tolerance
# ============================================================================
print("\n\n5. Symmetry Tolerance (symprec)")
print("-" * 70)

# Create structure
crystal = from_prototype('diamond', 'Si', 5.43)

# Get symmetry with different tolerances
for symprec in [1e-3, 1e-5, 1e-7]:
    sym_info = crystal.get_symmetry_info(symprec=symprec)
    print(f"symprec={symprec:.0e}: SG={sym_info['space_group_number']} "
          f"({sym_info['space_group_symbol']})")

print("\n" + "=" * 70)
print("Symmetry analysis examples completed!")
print("=" * 70)

