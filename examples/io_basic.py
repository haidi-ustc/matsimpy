"""
Examples for IO operations.

This example demonstrates:
- Reading and writing VASP files
- Reading and writing XYZ files
- Reading and writing JSON files
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.io.vasp import write_POSCAR, read_POSCAR
from matsimpy.io.xyz import write_XYZ, read_XYZ
from matsimpy.io.json import write_json, read_json
import os

print("=" * 70)
print("MatSimPy IO - Basic Examples")
print("=" * 70)

# Create output directory
output_dir = "examples_output"
os.makedirs(output_dir, exist_ok=True)

# ============================================================================
# Example 1: VASP Format (POSCAR)
# ============================================================================
print("\n1. VASP Format (POSCAR)")
print("-" * 70)

# Create a crystal
crystal = from_prototype('fcc', 'Cu', 3.61)
print(f"Original crystal: {crystal.formula}, {len(crystal)} atoms")

# Write to POSCAR
poscar_file = os.path.join(output_dir, "fcc_cu.POSCAR")
write_POSCAR(crystal, poscar_file)
print(f"Written to: {poscar_file}")

# Read back
crystal_read = read_POSCAR(poscar_file)
print(f"Read from POSCAR: {crystal_read.formula}, {len(crystal_read)} atoms")
print(f"  Lattice matches: {crystal.lattice.a == crystal_read.lattice.a}")

# ============================================================================
# Example 2: XYZ Format
# ============================================================================
print("\n\n2. XYZ Format")
print("-" * 70)

# Create a molecule
from matsimpy.builders.molecule import build_tetrahedral
molecule = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
print(f"Original molecule: {molecule.formula}, {len(molecule)} atoms")

# Write to XYZ
xyz_file = os.path.join(output_dir, "ch4.xyz")
write_XYZ(molecule, xyz_file)
print(f"Written to: {xyz_file}")

# Read back
molecule_read = read_XYZ(xyz_file)
print(f"Read from XYZ: {molecule_read.formula}, {len(molecule_read)} atoms")

# ============================================================================
# Example 3: JSON Format
# ============================================================================
print("\n\n3. JSON Format")
print("-" * 70)

# Write crystal to JSON
json_file = os.path.join(output_dir, "crystal.json")
write_json(crystal, json_file)
print(f"Written to: {json_file}")

# Read back
crystal_json = read_json(json_file)
print(f"Read from JSON: {crystal_json.formula}, {len(crystal_json)} atoms")

# ============================================================================
# Example 4: Multiple Structures
# ============================================================================
print("\n\n4. Writing Multiple Structures")
print("-" * 70)

# Create multiple structures
structures = {
    'fcc_cu': from_prototype('fcc', 'Cu', 3.61),
    'bcc_fe': from_prototype('bcc', 'Fe', 2.87),
    'diamond_c': from_prototype('diamond', 'C', 3.57),
}

for name, struct in structures.items():
    poscar_file = os.path.join(output_dir, f"{name}.POSCAR")
    write_POSCAR(struct, poscar_file)
    print(f"  Written {name}: {struct.formula} to {poscar_file}")

print(f"\nAll files written to: {output_dir}/")
print("\n" + "=" * 70)
print("IO examples completed!")
print("=" * 70)

