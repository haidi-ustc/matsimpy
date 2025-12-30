#!/usr/bin/env python3
"""
Test script for the two new methods added to Structure class:
1. __contains__ - Check if element is in structure
2. __iter__ - Iterate over sites
"""

from matsimpy.core import Crystal, Molecule, Lattice

print("=" * 70)
print("Testing new Structure methods")
print("=" * 70)

# Create a test crystal structure
print("\n1. Creating a Crystal structure (SiO2-like)")
crystal = Crystal(
    ['Si', 'O', 'Si', 'O', 'O'],
    [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5], [0.75, 0.75, 0.75], [0.1, 0.1, 0.1]],
    Lattice.cubic(5.0)
)
print(f"   Formula: {crystal.formula}")
print(f"   Number of atoms: {len(crystal)}")

# Test __contains__ method
print("\n2. Testing __contains__ method ('element' in structure)")
print(f"   'Si' in crystal: {'Si' in crystal}")
print(f"   'O' in crystal: {'O' in crystal}")
print(f"   'Fe' in crystal: {'Fe' in crystal}")
print(f"   'C' in crystal: {'C' in crystal}")

# Test __iter__ method
print("\n3. Testing __iter__ method (iterate over sites)")
print("   Iterating over crystal sites:")
for i, site in enumerate(crystal):
    print(f"      Site {i}: {site.specie} at frac_pos {site.frac_position}")

# Test with Molecule
print("\n4. Testing with Molecule (H2O)")
molecule = Molecule(
    ['O', 'H', 'H'],
    [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]]
)
print(f"   Formula: {molecule.formula}")

print("\n   Testing __contains__ on molecule:")
print(f"      'O' in molecule: {'O' in molecule}")
print(f"      'H' in molecule: {'H' in molecule}")
print(f"      'C' in molecule: {'C' in molecule}")

print("\n   Iterating over molecule sites:")
for i, site in enumerate(molecule):
    print(f"      Site {i}: {site.specie} at position {site.position}")

# Test converting to list
print("\n5. Converting structure to list of sites")
sites_list = list(crystal)
print(f"   Number of sites: {len(sites_list)}")
print(f"   First site: {sites_list[0].specie} at {sites_list[0].frac_position}")

# Test practical usage with 'in' operator
print("\n6. Practical example: Check elements before operations")
if 'Si' in crystal:
    print("   Crystal contains Si - can proceed with Si-related operations")
if 'Fe' not in crystal:
    print("   Crystal does not contain Fe - skipping Fe-related operations")

print("\n" + "=" * 70)
print("All tests completed successfully! ✓")
print("=" * 70)
