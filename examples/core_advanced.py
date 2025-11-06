"""
Advanced examples for MatSimPy core module.

This example demonstrates:
- Coordinate conversions
- Site properties
- Neighbor lists
- Advanced crystal operations
"""

import numpy as np
from matsimpy.core import Crystal, Lattice

print("=" * 70)
print("MatSimPy Core Module - Advanced Examples")
print("=" * 70)

# ============================================================================
# Example 1: Coordinate Conversions
# ============================================================================
print("\n1. Coordinate Conversions")
print("-" * 70)

# Create a crystal with fractional coordinates
lattice = Lattice.tetragonal(4.0, 6.0)
species = ['Si', 'O', 'O']
positions_frac = [[0, 0, 0], [0.25, 0.25, 0.25], [0.75, 0.75, 0.75]]
crystal = Crystal(species, positions_frac, lattice)

print("Fractional to Cartesian conversion:")
for i, (frac, cart) in enumerate(zip(crystal.frac_positions, crystal.cart_positions)):
    print(f"  {crystal.species[i]}: frac=({frac[0]:.3f}, {frac[1]:.3f}, {frac[2]:.3f}) "
          f"→ cart=({cart[0]:.2f}, {cart[1]:.2f}, {cart[2]:.2f}) Å")

# Create from cartesian coordinates
positions_cart = [[0, 0, 0], [1, 1, 1.5], [3, 3, 4.5]]
crystal2 = Crystal(species, positions_cart, lattice, coords_are_cartesian=True)
print(f"\nCreated from Cartesian coordinates:")
print(f"  Original cartesian: {positions_cart[1]}")
print(f"  Stored fractional: ({crystal2.frac_positions[1][0]:.3f}, "
      f"{crystal2.frac_positions[1][1]:.3f}, {crystal2.frac_positions[1][2]:.3f})")

# ============================================================================
# Example 2: Site Properties
# ============================================================================
print("\n\n2. Site Properties")
print("-" * 70)

# Create crystal with site properties
lattice = Lattice.cubic(5.0)
species = ['Fe', 'O']
positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
site_props = [
    {'magmom': 2.5, 'oxidation': 2},  # Fe site
    {'magmom': 0.0, 'oxidation': -2}  # O site
]
crystal = Crystal(species, positions, lattice, site_properties=site_props)

print("Crystal sites with properties:")
for i, site in enumerate(crystal.sites):
    print(f"  Site {i}: {site.specie}")
    print(f"    Position: ({site.frac_position[0]:.2f}, {site.frac_position[1]:.2f}, {site.frac_position[2]:.2f})")
    print(f"    Properties: {site.properties}")

# ============================================================================
# Example 3: Neighbor Lists
# ============================================================================
print("\n\n3. Neighbor Lists")
print("-" * 70)

# Create a simple cubic structure
lattice = Lattice.cubic(3.0)
species = ['Si'] * 8
# Create 2x2x2 simple cubic
positions = []
for i in [0, 0.5]:
    for j in [0, 0.5]:
        for k in [0, 0.5]:
            positions.append([i, j, k])

crystal = Crystal(species, positions, lattice)
print(f"Created {len(crystal)}-atom simple cubic structure")

# Get neighbor list
cutoff = 3.5  # Angstrom
neighbors = crystal.get_neighbor_list(cutoff, use_pbc=True)

print(f"\nNeighbor list (cutoff={cutoff} Å, with PBC):")
for atom_idx in range(min(3, len(crystal))):  # Show first 3 atoms
    atom_neighbors = neighbors.get(atom_idx, [])
    print(f"  Atom {atom_idx} ({crystal.species[atom_idx]}): {len(atom_neighbors)} neighbors")
    for neighbor_idx, distance in atom_neighbors[:3]:  # Show first 3 neighbors
        print(f"    → {neighbor_idx} ({crystal.species[neighbor_idx]}): {distance:.2f} Å")

# ============================================================================
# Example 4: Adding and Removing Atoms
# ============================================================================
print("\n\n4. Adding and Removing Atoms")
print("-" * 70)

# Start with a simple structure
lattice = Lattice.cubic(5.0)
crystal = Crystal(['Na'], [[0.5, 0.5, 0.5]], lattice)
print(f"Initial: {crystal.formula}, {len(crystal)} atoms")

# Add atoms
crystal.add_atom('Cl', [0, 0, 0])
crystal.add_atom('Na', [1, 0, 0])
print(f"After adding 2 atoms: {crystal.formula}, {len(crystal)} atoms")

# Remove an atom
crystal.remove_atom(0)
print(f"After removing atom 0: {crystal.formula}, {len(crystal)} atoms")

# ============================================================================
# Example 5: Substitution
# ============================================================================
print("\n\n5. Atom Substitution")
print("-" * 70)

# Create Si crystal
lattice = Lattice.cubic(5.43)
species = ['Si'] * 8
positions = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
            [0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.75, 0.25, 0.75], [0.25, 0.75, 0.75]]
crystal = Crystal(species, positions, lattice)
print(f"Initial: {crystal.formula}")

# Substitute single atom
crystal.substitute(0, 'Ge')
print(f"After substituting atom 0: {crystal.formula}")

# Substitute multiple atoms
crystal.substitute([1, 2], ['Ge', 'Ge'])
print(f"After substituting atoms 1,2: {crystal.formula}")

# Substitute all atoms of a species
crystal.substitute_all('Si', 'Ge')
print(f"After substituting all Si: {crystal.formula}")

# ============================================================================
# Example 6: Sorting Atoms
# ============================================================================
print("\n\n6. Sorting Atoms")
print("-" * 70)

# Create mixed structure
lattice = Lattice.cubic(5.0)
species = ['O', 'H', 'C', 'N', 'H']
positions = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0], [4, 0, 0]]
crystal = Crystal(species, positions, lattice)
print(f"Before sorting: {list(crystal.species)}")

# Sort by element (atomic number)
crystal.sort_atoms('element')
print(f"After sorting by element: {list(crystal.species)}")

# Sort alphabetically
crystal.sort_atoms('alphabet')
print(f"After sorting alphabetically: {list(crystal.species)}")

# ============================================================================
# Example 7: Serialization
# ============================================================================
print("\n\n7. Serialization (as_dict, from_dict)")
print("-" * 70)

lattice = Lattice.cubic(5.0)
crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)

# Convert to dictionary
crystal_dict = crystal.as_dict()
print("Crystal as_dict keys:", list(crystal_dict.keys()))

# Recreate from dictionary
crystal_recreated = Crystal.from_dict(crystal_dict)
print(f"Recreated crystal: {crystal_recreated.formula}")
print(f"Formula matches: {crystal.formula == crystal_recreated.formula}")
print(f"Positions match: {np.allclose(crystal.frac_positions, crystal_recreated.frac_positions)}")

print("\n" + "=" * 70)
print("Advanced examples completed!")
print("=" * 70)

