"""
Basic examples for MatSimPy core module.

This example demonstrates:
- Creating Crystal structures
- Creating Molecule structures
- Working with Lattice
- Using Composition
- Using Element
- Basic operations
- Calculator integration
"""

import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice, Composition, Element
from matsimpy.calculator import LennardJones
from matsimpy.builders.bulk import from_prototype

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
orthorhombic = Lattice.orthorhombic(3.0, 4.0, 5.0)

# Create from parameters (a, b, c, alpha, beta, gamma)
monoclinic = Lattice.from_parameters(
    a=5.0, b=5.0, c=5.0,
    alpha=90.0, beta=120.0, gamma=90.0
)

print(f"Cubic lattice: a={cubic.a:.2f} Å, volume={cubic.volume:.2f} Å³")
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

# Get element properties
si = Element('Si')
print(f"\nSilicon properties:")
print(f"  Atomic number: {si.atomic_no}")
print(f"  Atomic mass: {si.atomic_mass:.2f} amu")
if hasattr(si, 'radius'):
    print(f"  Atomic radius: {si.radius:.2f} Å" if si.radius else "  Atomic radius: N/A")

# ============================================================================
# Example 6: More Lattice Types
# ============================================================================
print("\n\n6. More Lattice Types")
print("-" * 70)

# Hexagonal lattice
hex_lattice = Lattice.hexagonal(3.0, 5.0)
print(f"Hexagonal: a={hex_lattice.a:.2f} Å, c={hex_lattice.c:.2f} Å")
print(f"  Volume: {hex_lattice.volume:.2f} Å³")

# Rhombohedral lattice
rhomb_lattice = Lattice.rhombohedral(5.0, 60.0)
print(f"\nRhombohedral: a={rhomb_lattice.a:.2f} Å, α={rhomb_lattice.alpha:.1f}°")
print(f"  Volume: {rhomb_lattice.volume:.2f} Å³")

# Triclinic lattice
triclinic_lattice = Lattice.from_parameters(
    a=5.0, b=6.0, c=7.0,
    alpha=80.0, beta=90.0, gamma=100.0
)
print(f"\nTriclinic: a={triclinic_lattice.a:.2f}, b={triclinic_lattice.b:.2f}, c={triclinic_lattice.c:.2f} Å")
print(f"  Angles: α={triclinic_lattice.alpha:.1f}°, β={triclinic_lattice.beta:.1f}°, γ={triclinic_lattice.gamma:.1f}°")

# ============================================================================
# Example 7: More Composition Operations
# ============================================================================
print("\n\n7. More Composition Operations")
print("-" * 70)

# Composition operations
comp1 = Composition('H2O')
comp2 = Composition('CO2')
print(f"H2O: {comp1.formula}")
print(f"CO2: {comp2.formula}")
print(f"  Note: Composition arithmetic not directly supported, use transformations instead")

# Composition from formula string
comp_fe2o3 = Composition('Fe2O3')
print(f"\nFe2O3 composition:")
print(f"  Formula: {comp_fe2o3.formula}")
print(f"  Fe count: {comp_fe2o3['Fe']}, O count: {comp_fe2o3['O']}")

# Get mass fractions using the mass_fractions method
h2o = Composition('H2O')
mass_frac = h2o.mass_fractions()  # Returns a dictionary
print(f"\nH2O mass fractions:")
print(f"  Hydrogen: {mass_frac['H']:.4f}")
print(f"  Oxygen: {mass_frac['O']:.4f}")
print(f"  Total: {sum(mass_frac.values()):.4f}")

# ============================================================================
# Example 8: Basic Selection Utilities
# ============================================================================
print("\n\n8. Basic Selection Utilities")
print("-" * 70)

# Create a mixed crystal
mixed_crystal = Crystal(
    ['Si', 'O', 'Si', 'O', 'Al'],
    [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5], [0.75, 0.75, 0.75], [0.125, 0.125, 0.125]],
    Lattice.cubic(5.0)
)

from matsimpy.utils.selection import select_by_species, AtomSelection

# Select by species
si_indices = select_by_species(mixed_crystal, 'Si')
print(f"Si atoms at indices: {si_indices}")

# Use AtomSelection class
sel = AtomSelection(mixed_crystal).by_species('O')
print(f"Oxygen atoms selected: {len(sel)} atoms")
print(f"  Indices: {list(sel)}")

# ============================================================================
# Example 9: Basic Calculator Integration
# ============================================================================
print("\n\n9. Basic Calculator Integration")
print("-" * 70)

# Create Ar crystal and attach calculator
ar_crystal = Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0))
lj_calc = LennardJones(sigma=3.4, epsilon=0.0104)
ar_crystal.calc = lj_calc

# Get energy using convenience method
energy = ar_crystal.get_potential_energy()
print(f"Ar crystal with LJ calculator:")
print(f"  Energy: {energy:.6f} eV")

# Get forces
forces = ar_crystal.get_forces()
print(f"  Forces: {forces[0]}")

# Same for molecule
ar_dimer = Molecule(['Ar', 'Ar'], [[0, 0, 0], [3.4, 0, 0]])
ar_dimer.calc = lj_calc
energy_mol = ar_dimer.get_potential_energy()
print(f"\nAr dimer with LJ calculator:")
print(f"  Energy: {energy_mol:.6f} eV")

# ============================================================================
# Example 10: Basic Serialization
# ============================================================================
print("\n\n10. Basic Serialization")
print("-" * 70)

# Convert to dictionary
crystal_dict = ar_crystal.as_dict()
print(f"Crystal serialized: {len(crystal_dict)} keys")
print(f"  Keys: {list(crystal_dict.keys())[:5]}...")

# Recreate from dictionary
crystal_restored = Crystal.from_dict(crystal_dict)
print(f"\nCrystal restored: {crystal_restored.formula}")
print(f"  Formula matches: {ar_crystal.formula == crystal_restored.formula}")
print(f"  Positions match: {np.allclose(ar_crystal.frac_positions, crystal_restored.frac_positions)}")

# ============================================================================
# Example 11: Copy Method
# ============================================================================
print("\n\n11. Copy Method")
print("-" * 70)

# Create a crystal and copy it
original = from_prototype('diamond', 'Si', 5.43)
copied = original.copy()

print(f"Original: {original.formula}, {len(original)} atoms")
print(f"Copied: {copied.formula}, {len(copied)} atoms")
print(f"  Are they the same object? {original is copied}")
print(f"  Do they have same formula? {original.formula == copied.formula}")

# Modify the copy
copied.add_atom('H', [0.5, 0.5, 0.5])
print(f"\nAfter adding H to copy:")
print(f"  Original: {len(original)} atoms")
print(f"  Copied: {len(copied)} atoms")
print(f"  Original unchanged: {len(original) == 2}")

print("\n" + "=" * 70)
print("Basic examples completed!")
print("=" * 70)

