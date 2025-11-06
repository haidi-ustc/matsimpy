"""
Examples for building alloy structures.

This example demonstrates:
- Random alloy generation
- Ordered alloy generation
- Intermetallic compounds
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.alloy import generate_random_alloy, generate_ordered_alloy, generate_intermetallic
from matsimpy.transformation.structural import make_supercell

print("=" * 70)
print("MatSimPy Builders - Alloy Structures Examples")
print("=" * 70)

# ============================================================================
# Example 1: Random Alloys
# ============================================================================
print("\n1. Random Alloy Generation")
print("-" * 70)

# Start with FCC Cu
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
print(f"Base structure: {fcc_cu.formula}, {len(fcc_cu)} atoms")

# Create a supercell for better alloy representation
supercell = make_supercell(fcc_cu, [4, 4, 4])
print(f"Supercell: {supercell.formula}, {len(supercell)} atoms")

# Generate random Cu-Ni alloy (25% Ni)
cu_ni_alloy = generate_random_alloy(supercell, ['Ni'], 'Cu', [0.25])
print(f"\nRandom Cu-Ni alloy (25% Ni):")
print(f"  Formula: {cu_ni_alloy.formula}")
print(f"  Total atoms: {len(cu_ni_alloy)}")
print(f"  Cu atoms: {sum(1 for s in cu_ni_alloy.species if s == 'Cu')}")
print(f"  Ni atoms: {sum(1 for s in cu_ni_alloy.species if s == 'Ni')}")

# Generate ternary alloy (Cu-Ni-Zn)
cu_ni_zn_alloy = generate_random_alloy(supercell, ['Ni', 'Zn'], 'Cu', [0.2, 0.1])
print(f"\nRandom Cu-Ni-Zn alloy (20% Ni, 10% Zn):")
print(f"  Formula: {cu_ni_zn_alloy.formula}")
print(f"  Cu atoms: {sum(1 for s in cu_ni_zn_alloy.species if s == 'Cu')}")
print(f"  Ni atoms: {sum(1 for s in cu_ni_zn_alloy.species if s == 'Ni')}")
print(f"  Zn atoms: {sum(1 for s in cu_ni_zn_alloy.species if s == 'Zn')}")

# ============================================================================
# Example 2: Ordered Alloys
# ============================================================================
print("\n\n2. Ordered Alloy Generation")
print("-" * 70)

# Create ordered substitution pattern
ordered_alloy = generate_ordered_alloy(supercell, ['Ni'], 'Cu', [0.25])
print(f"Ordered Cu-Ni alloy (25% Ni):")
print(f"  Formula: {ordered_alloy.formula}")
print(f"  Cu atoms: {sum(1 for s in ordered_alloy.species if s == 'Cu')}")
print(f"  Ni atoms: {sum(1 for s in ordered_alloy.species if s == 'Ni')}")

# ============================================================================
# Example 3: Intermetallic Compounds
# ============================================================================
print("\n\n3. Intermetallic Compounds")
print("-" * 70)

try:
    # L1_2 structure (e.g., Cu3Au)
    l12 = generate_intermetallic('L1_2', ['Cu', 'Au'], a=3.75)
    print(f"L1_2 Cu3Au:")
    print(f"  Formula: {l12.formula}")
    print(f"  Atoms: {len(l12)}")
    print(f"  Cu: {sum(1 for s in l12.species if s == 'Cu')}")
    print(f"  Au: {sum(1 for s in l12.species if s == 'Au')}")
    
    # B2 structure (e.g., FeAl)
    b2 = generate_intermetallic('B2', ['Fe', 'Al'], a=2.9)
    print(f"\nB2 FeAl:")
    print(f"  Formula: {b2.formula}")
    print(f"  Atoms: {len(b2)}")
    print(f"  Fe: {sum(1 for s in b2.species if s == 'Fe')}")
    print(f"  Al: {sum(1 for s in b2.species if s == 'Al')}")
    
except Exception as e:
    print(f"Error generating intermetallic: {e}")

# ============================================================================
# Example 4: Comparing Alloy Types
# ============================================================================
print("\n\n4. Comparing Alloy Types")
print("-" * 70)

base = make_supercell(fcc_cu, [3, 3, 3])
concentration = 0.2

random = generate_random_alloy(base, ['Ni'], 'Cu', [concentration])
ordered = generate_ordered_alloy(base, ['Ni'], 'Cu', [concentration])

print(f"{'Type':<15} {'Formula':<15} {'Cu':<6} {'Ni':<6}")
print("-" * 45)
print(f"{'Random':<15} {random.formula:<15} "
      f"{sum(1 for s in random.species if s == 'Cu'):<6} "
      f"{sum(1 for s in random.species if s == 'Ni'):<6}")
print(f"{'Ordered':<15} {ordered.formula:<15} "
      f"{sum(1 for s in ordered.species if s == 'Cu'):<6} "
      f"{sum(1 for s in ordered.species if s == 'Ni'):<6}")

print("\n" + "=" * 70)
print("Alloy structure examples completed!")
print("=" * 70)

