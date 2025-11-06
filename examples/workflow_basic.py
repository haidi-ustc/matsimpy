"""
Basic workflow example.

This example demonstrates a complete workflow:
1. Create a bulk structure
2. Create a supercell
3. Add defects
4. Apply transformations
5. Save to file
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.defects import create_vacancy, create_substitution
from matsimpy.transformation.structural import make_supercell
from matsimpy.transformation.geometric import translate
from matsimpy.io.vasp import write_POSCAR
import os

print("=" * 70)
print("MatSimPy - Basic Workflow Example")
print("=" * 70)

# ============================================================================
# Step 1: Create Bulk Structure
# ============================================================================
print("\nStep 1: Create Bulk Structure")
print("-" * 70)

# Create FCC Cu
crystal = from_prototype('fcc', 'Cu', 3.61)
print(f"Created: {crystal.formula}")
print(f"  Atoms: {len(crystal)}")
print(f"  Lattice: a={crystal.lattice.a:.2f} Å")

# ============================================================================
# Step 2: Create Supercell
# ============================================================================
print("\nStep 2: Create Supercell")
print("-" * 70)

# Make 3x3x3 supercell
supercell = make_supercell(crystal, [3, 3, 3])
print(f"Supercell: {supercell.formula}")
print(f"  Atoms: {len(supercell)}")
print(f"  Lattice: a={supercell.lattice.a:.2f} Å")

# ============================================================================
# Step 3: Add Defects
# ============================================================================
print("\nStep 3: Add Defects")
print("-" * 70)

# Create vacancy
defected = create_vacancy(supercell, 0)
print(f"After vacancy: {defected.formula}, {len(defected)} atoms")

# Create substitution
defected = create_substitution(defected, 1, 'Ni')
print(f"After substitution: {defected.formula}")
print(f"  Cu: {sum(1 for s in defected.species if s == 'Cu')}")
print(f"  Ni: {sum(1 for s in defected.species if s == 'Ni')}")

# ============================================================================
# Step 4: Apply Transformations
# ============================================================================
print("\nStep 4: Apply Transformations")
print("-" * 70)

# Translate structure
translated = translate(defected, [0.1, 0.1, 0.1], inplace=False)
print(f"Translated by [0.1, 0.1, 0.1]")
print(f"  Structure unchanged: {len(translated) == len(defected)}")

# ============================================================================
# Step 5: Save to File
# ============================================================================
print("\nStep 5: Save to File")
print("-" * 70)

output_dir = "examples_output"
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, "defected_cu.POSCAR")
write_POSCAR(defected, output_file)
print(f"Saved to: {output_file}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("Workflow Summary")
print("=" * 70)
print(f"1. Created bulk: {crystal.formula} ({len(crystal)} atoms)")
print(f"2. Created supercell: {supercell.formula} ({len(supercell)} atoms)")
print(f"3. Added defects: {defected.formula} ({len(defected)} atoms)")
print(f"4. Applied transformations")
print(f"5. Saved to: {output_file}")
print("=" * 70)

