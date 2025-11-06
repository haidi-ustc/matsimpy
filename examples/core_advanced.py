"""
Advanced examples for MatSimPy core module.

This example demonstrates:
- Coordinate conversions
- Site properties
- Neighbor lists
- Adding and removing atoms
- Atom substitution
- Sorting atoms
- Molecule operations (translate, rotate, to_crystal)
- Periodic boundary conditions
- Advanced selection
- Serialization
- Calculator integration
"""

import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.utils.selection import AtomSelection
from matsimpy.calculator import LennardJones

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
# Example 7: Periodic Boundary Conditions
# ============================================================================
print("\n\n7. Periodic Boundary Conditions")
print("-" * 70)

# Create crystal with custom PBC
lattice = Lattice.cubic(5.0)
species = ['Si'] * 4
positions = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]

# All directions periodic (default)
crystal_pbc_all = Crystal(species, positions, lattice, pbc=[True, True, True])
print(f"PBC [True, True, True]: {crystal_pbc_all.pbc}")

# Only z-direction periodic (2D slab)
crystal_pbc_z = Crystal(species, positions, lattice, pbc=[False, False, True])
print(f"PBC [False, False, True]: {crystal_pbc_z.pbc}")

# Non-periodic (cluster)
crystal_no_pbc = Crystal(species, positions, lattice, pbc=[False, False, False])
print(f"PBC [False, False, False]: {crystal_no_pbc.pbc}")

# ============================================================================
# Example 8: Molecule Operations
# ============================================================================
print("\n\n8. Molecule Operations")
print("-" * 70)

# Create water molecule
h2o = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
print(f"Original H2O:")
print(f"  Center of mass: {h2o.get_center_of_mass()}")

# Translate molecule
h2o.translate([1.0, 2.0, 3.0])
print(f"\nAfter translation by [1, 2, 3]:")
print(f"  Center of mass: {h2o.get_center_of_mass()}")

# Rotate molecule (90 degrees around z-axis)
h2o.rotate(90, [0, 0, 1])
print(f"\nAfter rotation (90° around z-axis):")
print(f"  O position: {h2o.positions[0]}")
print(f"  H1 position: {h2o.positions[1]}")

# Convert molecule to crystal (with vacuum)
h2o_crystal = h2o.to_crystal(vacuum=10.0)
print(f"\nH2O converted to crystal:")
print(f"  Lattice: {h2o_crystal.lattice.a:.2f} Å cubic")
print(f"  Volume: {h2o_crystal.volume:.2f} Å³")
print(f"  PBC: {h2o_crystal.pbc}")

# ============================================================================
# Example 9: Advanced Selection
# ============================================================================
print("\n\n9. Advanced Selection")
print("-" * 70)

# Create complex structure
complex_crystal = Crystal(
    ['Si', 'O', 'Si', 'O', 'Al', 'Si', 'O'],
    [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5], 
     [0.75, 0.75, 0.75], [0.125, 0.125, 0.125],
     [0.375, 0.375, 0.375], [0.625, 0.625, 0.625]],
    Lattice.cubic(10.0)
)

# Chain selection operations
sel = (AtomSelection(complex_crystal)
       .by_species('Si')  # Select Si atoms
       .near([0.5, 0.5, 0.5], 3.0))  # Near center

print(f"Si atoms near center: {len(sel)} atoms")
print(f"  Indices: {list(sel)}")

# Combine selections (use | operator or combine_selections)
sel1 = AtomSelection(complex_crystal).by_species('Si')
sel2 = AtomSelection(complex_crystal).by_species('Al')
combined = sel1 | sel2  # Use | operator for union
print(f"\nCombined selection (Si | Al): {len(combined)} atoms")

# Subtract selections
sel_diff = sel1 - sel  # All Si minus Si near center
print(f"Difference (all Si - Si near center): {len(sel_diff)} atoms")

# ============================================================================
# Example 10: Serialization and Deserialization
# ============================================================================
print("\n\n10. Serialization and Deserialization")
print("-" * 70)

lattice = Lattice.cubic(5.0)
crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)

# Convert to dictionary
crystal_dict = crystal.as_dict()
print(f"Crystal as_dict keys: {list(crystal_dict.keys())}")

# Recreate from dictionary
crystal_recreated = Crystal.from_dict(crystal_dict)
print(f"\nRecreated crystal: {crystal_recreated.formula}")
print(f"  Formula matches: {crystal.formula == crystal_recreated.formula}")
print(f"  Positions match: {np.allclose(crystal.frac_positions, crystal_recreated.frac_positions)}")
print(f"  Lattice matches: {np.allclose(crystal.lattice.matrix, crystal_recreated.lattice.matrix)}")

# Serialize with site properties
crystal_with_props = Crystal(
    ['Fe', 'O'],
    [[0, 0, 0], [0.5, 0.5, 0.5]],
    lattice,
    site_properties=[{'magmom': 2.5}, {'magmom': 0.0}]
)
crystal_dict_props = crystal_with_props.as_dict()
crystal_restored_props = Crystal.from_dict(crystal_dict_props)
print(f"\nWith site properties:")
print(f"  Original site 0 magmom: {crystal_with_props.sites[0].properties.get('magmom')}")
print(f"  Restored site 0 magmom: {crystal_restored_props.sites[0].properties.get('magmom')}")

# ============================================================================
# Example 11: Calculator Integration
# ============================================================================
print("\n\n11. Calculator Integration")
print("-" * 70)

# Create structure and calculator
crystal = Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0))
calc = LennardJones(sigma=3.4, epsilon=0.0104)

# Attach calculator
crystal.calc = calc

# Use convenience methods
energy = crystal.get_potential_energy()
forces = crystal.get_forces()
stress = crystal.get_stress()

print(f"Calculator attached to crystal:")
print(f"  Energy: {energy:.6f} eV")
print(f"  Forces shape: {forces.shape}")
print(f"  Stress shape: {stress.shape}")
print(f"  Stress tensor:\n{stress}")

# Calculator with molecule
molecule = Molecule(['Ar', 'Ar'], [[0, 0, 0], [3.4, 0, 0]])
molecule.calc = calc
energy_mol = molecule.get_potential_energy()
forces_mol = molecule.get_forces()

print(f"\nCalculator attached to molecule:")
print(f"  Energy: {energy_mol:.6f} eV")
print(f"  Forces shape: {forces_mol.shape}")

# ============================================================================
# Example 12: Advanced Neighbor Finding
# ============================================================================
print("\n\n12. Advanced Neighbor Finding")
print("-" * 70)

# Create larger structure
lattice = Lattice.cubic(5.0)
species = ['Si'] * 27  # 3x3x3 simple cubic
positions = []
for i in [0, 0.33, 0.67]:
    for j in [0, 0.33, 0.67]:
        for k in [0, 0.33, 0.67]:
            positions.append([i, j, k])

crystal = Crystal(species, positions, lattice)
print(f"Created {len(crystal)}-atom structure")

# Get neighbor list with PBC
cutoff = 6.0
neighbors = crystal.get_neighbor_list(cutoff, use_pbc=True)

# Statistics
neighbor_counts = [len(neighbors.get(i, [])) for i in range(len(crystal))]
print(f"\nNeighbor statistics (cutoff={cutoff} Å, with PBC):")
print(f"  Average neighbors: {np.mean(neighbor_counts):.1f}")
print(f"  Min neighbors: {min(neighbor_counts)}")
print(f"  Max neighbors: {max(neighbor_counts)}")

# Show first few atoms
print(f"\nFirst 3 atoms:")
for i in range(min(3, len(crystal))):
    atom_neighbors = neighbors.get(i, [])
    print(f"  Atom {i}: {len(atom_neighbors)} neighbors")
    if atom_neighbors:
        distances = [d for _, d in atom_neighbors[:3]]
        print(f"    First 3 distances: {[f'{d:.2f}' for d in distances]} Å")

# Get neighbor list without PBC
neighbors_no_pbc = crystal.get_neighbor_list(cutoff, use_pbc=False)
neighbor_counts_no_pbc = [len(neighbors_no_pbc.get(i, [])) for i in range(len(crystal))]
print(f"\nWithout PBC:")
print(f"  Average neighbors: {np.mean(neighbor_counts_no_pbc):.1f}")

# ============================================================================
# Example 13: Advanced Substitution
# ============================================================================
print("\n\n13. Advanced Substitution")
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

# Substitute using AtomSelection
crystal = Crystal(species, positions, lattice)  # Reset
sel = AtomSelection(crystal).by_indices([0, 1, 2])
crystal.substitute(sel, 'Ge')
print(f"After substituting selected atoms: {crystal.formula}")

# ============================================================================
# Example 14: Site Access and Properties
# ============================================================================
print("\n\n14. Site Access and Properties")
print("-" * 70)

# Create crystal with site properties
lattice = Lattice.cubic(5.0)
species = ['Fe', 'O', 'Fe']
positions = [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0]]
site_props = [
    {'magmom': 2.5, 'oxidation': 2},
    {'magmom': 0.0, 'oxidation': -2},
    {'magmom': 2.5, 'oxidation': 2}
]
crystal = Crystal(species, positions, lattice, site_properties=site_props)

print("Crystal sites:")
for i, site in enumerate(crystal.sites):
    print(f"  Site {i}: {site.specie}")
    print(f"    Fractional: ({site.frac_position[0]:.2f}, {site.frac_position[1]:.2f}, {site.frac_position[2]:.2f})")
    print(f"    Cartesian: ({site.cart_position[0]:.2f}, {site.cart_position[1]:.2f}, {site.cart_position[2]:.2f}) Å")
    print(f"    Properties: {site.properties}")

# Access sites directly
print(f"\nFirst site: {crystal.sites[0]}")
print(f"Site specie: {crystal.sites[0].specie}")
print(f"Site properties: {crystal.sites[0].properties}")

print("\n" + "=" * 70)
print("Advanced examples completed!")
print("=" * 70)

