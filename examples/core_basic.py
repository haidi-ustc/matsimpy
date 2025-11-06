"""
Basic examples for MatSimPy core module.

This example demonstrates:
- Creating Crystal structures
- Creating Molecule structures
- Working with Lattice
- Using Composition
- Basic operations
"""

import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice, Composition, Element

print("=" * 70)
print("MatSimPy Core Module - Basic Examples")
print("=" * 70)

# ============================================================================
# Example 1: Creating a Crystal Structure
# ============================================================================
print("\n1. Creating a Crystal Structure")
print("-" * 70)

# Create a cubic lattice
lattice = Lattice.cubic(5.0)  # 5 Angstrom cubic cell

# Create a simple cubic crystal with two atoms
species = ['Na', 'Cl']
positions = [[0, 0, 0], [0.5, 0.5, 0.5]]  # Fractional coordinates
crystal = Crystal(species, positions, lattice)

print(f"Crystal formula: {crystal.formula}")
print(f"Number of atoms: {len(crystal)}")
print(f"Lattice parameters: a={crystal.lattice.a:.2f} Å")
print(f"Volume: {crystal.volume:.2f} Å³")

# Access fractional and cartesian coordinates
print(f"\nFractional positions:")
for i, pos in enumerate(crystal.frac_positions):
    print(f"  {crystal.species[i]}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

print(f"\nCartesian positions:")
for i, pos in enumerate(crystal.cart_positions):
    print(f"  {crystal.species[i]}: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}) Å")

# ============================================================================
# Example 2: Creating a Molecule
# ============================================================================
print("\n\n2. Creating a Molecule")
print("-" * 70)

# Create a water molecule
h2o_species = ['O', 'H', 'H']
h2o_positions = [
    [0.0, 0.0, 0.0],      # O at origin
    [0.96, 0.0, 0.0],     # H1
    [-0.24, 0.93, 0.0]    # H2 (bent geometry)
]
h2o = Molecule(h2o_species, h2o_positions)

print(f"Molecule formula: {h2o.formula}")
print(f"Number of atoms: {len(h2o)}")
print(f"Center of mass: {h2o.get_center_of_mass()}")

# ============================================================================
# Example 3: Working with Lattice
# ============================================================================
print("\n\n3. Working with Lattice")
print("-" * 70)

# Create different lattice types
cubic = Lattice.cubic(4.0)
tetragonal = Lattice.tetragonal(3.0, 5.0)
orthorhombic = Lattice.orthorhomic(3.0, 4.0, 5.0)

# Create from parameters (a, b, c, alpha, beta, gamma)
monoclinic = Lattice.from_parameters(
    a=5.0, b=5.0, c=5.0,
    alpha=90.0, beta=120.0, gamma=90.0
)

print(f"Cubic lattice: a={cubic.a:.2f} Å, volume={cubic.volume():.2f} Å³")
print(f"Tetragonal: a={tetragonal.a:.2f}, c={tetragonal.c:.2f} Å")
print(f"Orthorhombic: a={orthorhombic.a:.2f}, b={orthorhombic.b:.2f}, c={orthorhombic.c:.2f} Å")
print(f"Monoclinic: α={monoclinic.alpha:.1f}°, β={monoclinic.beta:.1f}°, γ={monoclinic.gamma:.1f}°")

# ============================================================================
# Example 4: Using Composition
# ============================================================================
print("\n\n4. Using Composition")
print("-" * 70)

# Create compositions from formulas
comp1 = Composition('H2O')
comp2 = Composition('Ca(OH)2')
comp3 = Composition('Fe2O3')

print(f"H2O: {comp1.formula}")
print(f"  H count: {comp1['H']}, O count: {comp1['O']}")

print(f"\nCa(OH)2: {comp2.formula}")
print(f"  Ca count: {comp2['Ca']}, O count: {comp2['O']}, H count: {comp2['H']}")

print(f"\nFe2O3: {comp3.formula}")
print(f"  Fe count: {comp3['Fe']}, O count: {comp3['O']}")

# ============================================================================
# Example 5: Using Element
# ============================================================================
print("\n\n5. Using Element")
print("-" * 70)

# Get element information
h = Element('H')
o = Element('O')
fe = Element('Fe')

print(f"Hydrogen: Z={h.atomic_no}, mass={h.atomic_mass:.2f} amu")
print(f"Oxygen: Z={o.atomic_no}, mass={o.atomic_mass:.2f} amu")
print(f"Iron: Z={fe.atomic_no}, mass={fe.atomic_mass:.2f} amu")

# Get element from atomic number
element_from_z = Element.from_Z(6)  # Carbon
print(f"\nElement from Z=6: {element_from_z.symbol}")

print("\n" + "=" * 70)
print("Basic examples completed!")
print("=" * 70)

