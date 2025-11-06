"""
Examples for building bulk crystal structures.

This example demonstrates:
- Building structures from prototypes (FCC, BCC, etc.)
- Random crystal generation
- Working with symmetry
"""

from matsimpy.builders.bulk import from_prototype, random_crystal
from matsimpy.builders.bulk.symmetry import from_space_group
from matsimpy.core import Lattice

print("=" * 70)
print("MatSimPy Builders - Bulk Structures Examples")
print("=" * 70)

# ============================================================================
# Example 1: Building from Prototypes
# ============================================================================
print("\n1. Building Structures from Prototypes")
print("-" * 70)

# Face-Centered Cubic (FCC)
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
print(f"FCC Cu: {fcc_cu.formula}, {len(fcc_cu)} atoms, a={fcc_cu.lattice.a:.2f} Å")

# Body-Centered Cubic (BCC)
bcc_fe = from_prototype('bcc', 'Fe', 2.87)
print(f"BCC Fe: {bcc_fe.formula}, {len(bcc_fe)} atoms, a={bcc_fe.lattice.a:.2f} Å")

# Diamond structure
diamond_c = from_prototype('diamond', 'C', 3.57)
print(f"Diamond C: {diamond_c.formula}, {len(diamond_c)} atoms, a={diamond_c.lattice.a:.2f} Å")

# Hexagonal Close-Packed (HCP)
hcp_mg = from_prototype('hcp', 'Mg', [3.21, 3.21, 5.21])  # [a, b, c] for hexagonal
print(f"HCP Mg: {hcp_mg.formula}, {len(hcp_mg)} atoms, a={hcp_mg.lattice.a:.2f} Å, c={hcp_mg.lattice.c:.2f} Å")

# Rocksalt (NaCl structure) - using binary compound string
rocksalt = from_prototype('rocksalt', 'NaCl', 5.64)
print(f"Rocksalt NaCl: {rocksalt.formula}, {len(rocksalt)} atoms, a={rocksalt.lattice.a:.2f} Å")

# Perovskite structure
perovskite = from_prototype('perovskite', ['Ca', 'Ti', 'O'], 3.9)
print(f"Perovskite CaTiO3: {perovskite.formula}, {len(perovskite)} atoms, a={perovskite.lattice.a:.2f} Å")

# ============================================================================
# Example 2: Available Prototypes
# ============================================================================
print("\n\n2. Available Prototypes")
print("-" * 70)

prototypes = [
    'fcc', 'bcc', 'diamond', 'hcp', 
    'sc', 'rocksalt', 'zincblende', 
    'fluorite', 'perovskite'
]

print("Available prototypes:")
for proto in prototypes:
    try:
        # Try to create a simple example
        if proto == 'hcp':
            struct = from_prototype(proto, 'Mg', a=3.0, c=5.0)
        elif proto in ['rocksalt', 'zincblende', 'fluorite', 'perovskite']:
            if proto == 'rocksalt':
                struct = from_prototype(proto, 'NaCl', 5.0)
            elif proto == 'zincblende':
                struct = from_prototype(proto, 'ZnS', 5.4)
            elif proto == 'fluorite':
                struct = from_prototype(proto, 'CaF2', 5.5)
            else:  # perovskite
                struct = from_prototype(proto, ['Ca', 'Ti', 'O'], 4.0)
        else:
            struct = from_prototype(proto, 'C', 3.0)
        print(f"  ✓ {proto:12s} - {struct.formula:10s} ({len(struct)} atoms)")
    except Exception as e:
        print(f"  ✗ {proto:12s} - Error: {str(e)[:40]}")

# ============================================================================
# Example 3: Random Crystal Generation (requires PyXtal)
# ============================================================================
print("\n\n3. Random Crystal Generation")
print("-" * 70)

try:
    # Generate random crystal with space group 227 (Fd-3m, diamond)
    # This requires PyXtal to be installed
    random_si = random_crystal(3, 227, ['Si'], [8])
    print(f"Random Si (space group 227): {random_si.formula}")
    print(f"  Number of atoms: {len(random_si)}")
    print(f"  Lattice: a={random_si.lattice.a:.2f} Å")
except ImportError:
    print("PyXtal not installed. Skipping random crystal generation.")
    print("Install with: pip install pyxtal")
except Exception as e:
    print(f"Error generating random crystal: {e}")

# ============================================================================
# Example 4: Building from Space Group
# ============================================================================
print("\n\n4. Building from Space Group")
print("-" * 70)

try:
    # Build structure from space group number
    # Space group 225 (Fm-3m) for FCC
    fcc_from_sg = from_space_group(225, ['Cu'], [4], a=3.61)
    print(f"FCC Cu from space group 225: {fcc_from_sg.formula}")
    print(f"  Number of atoms: {len(fcc_from_sg)}")
    print(f"  Lattice: a={fcc_from_sg.lattice.a:.2f} Å")
except Exception as e:
    print(f"Error building from space group: {e}")

# ============================================================================
# Example 5: Comparing Different Structures
# ============================================================================
print("\n\n5. Comparing Different Structures")
print("-" * 70)

structures = {
    'FCC Cu': from_prototype('fcc', 'Cu', 3.61),
    'BCC Fe': from_prototype('bcc', 'Fe', 2.87),
    'Diamond C': from_prototype('diamond', 'C', 3.57),
}

print(f"{'Structure':<15} {'Formula':<10} {'Atoms':<8} {'Volume (Å³)':<12}")
print("-" * 50)
for name, struct in structures.items():
    print(f"{name:<15} {struct.formula:<10} {len(struct):<8} {struct.volume:<12.2f}")

print("\n" + "=" * 70)
print("Bulk structure examples completed!")
print("=" * 70)

