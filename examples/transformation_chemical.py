"""
Examples for chemical transformations.

This example demonstrates:
- Chemical substitutions
- Bulk substitutions
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.chemical import substitute
from matsimpy.transformation.structural import make_supercell

print("=" * 70)
print("MatSimPy Transformations - Chemical Examples")
print("=" * 70)

# ============================================================================
# Example 1: Single Atom Substitution
# ============================================================================
print("\n1. Single Atom Substitution")
print("-" * 70)

# Create Si crystal
si = from_prototype('diamond', 'Si', 5.43)
supercell = make_supercell(si, [2, 2, 2])
print(f"Original: {supercell.formula}, {len(supercell)} atoms")

# Substitute one Si with Ge
substituted = substitute(supercell, [0], ['Ge'], inplace=False)
print(f"\nAfter substitution: {substituted.formula}")
print(f"  Si: {sum(1 for s in substituted.species if s == 'Si')}")
print(f"  Ge: {sum(1 for s in substituted.species if s == 'Ge')}")

# ============================================================================
# Example 2: Multiple Substitutions
# ============================================================================
print("\n\n2. Multiple Substitutions")
print("-" * 70)

# Substitute multiple atoms
substituted = substitute(supercell, [0, 1, 2], ['Ge', 'Ge', 'Ge'], inplace=False)
print(f"After substituting 3 atoms: {substituted.formula}")
print(f"  Si: {sum(1 for s in substituted.species if s == 'Si')}")
print(f"  Ge: {sum(1 for s in substituted.species if s == 'Ge')}")

# ============================================================================
# Example 3: Dictionary-Based Substitution
# ============================================================================
print("\n\n3. Dictionary-Based Substitution")
print("-" * 70)

# Create binary compound - using binary compound string
nacl = from_prototype('rocksalt', 'NaCl', 5.64)
nacl_super = make_supercell(nacl, [2, 2, 2])
print(f"Original: {nacl_super.formula}")

# Use dictionary mapping
substitution_map = {'Na': 'K', 'Cl': 'Br'}  # NaCl → KBr
substituted = substitute(nacl_super, list(range(len(nacl_super))), 
                        substitution_map, inplace=False)
print(f"\nAfter substitution (Na→K, Cl→Br): {substituted.formula}")
print(f"  K: {sum(1 for s in substituted.species if s == 'K')}")
print(f"  Br: {sum(1 for s in substituted.species if s == 'Br')}")

# ============================================================================
# Example 4: Selective Substitution
# ============================================================================
print("\n\n4. Selective Substitution")
print("-" * 70)

# Substitute only specific atoms
si = from_prototype('diamond', 'Si', 5.43)
supercell = make_supercell(si, [3, 3, 3])

# Substitute atoms at specific positions
indices_to_sub = [0, 5, 10, 15]
substituted = substitute(supercell, indices_to_sub, ['Ge'] * len(indices_to_sub), 
                         inplace=False)
print(f"Substituted {len(indices_to_sub)} specific atoms:")
print(f"  Formula: {substituted.formula}")
print(f"  Si: {sum(1 for s in substituted.species if s == 'Si')}")
print(f"  Ge: {sum(1 for s in substituted.species if s == 'Ge')}")

print("\n" + "=" * 70)
print("Chemical transformation examples completed!")
print("=" * 70)

