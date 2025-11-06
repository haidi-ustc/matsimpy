"""
Examples for composite transformations (high-throughput workflows).

This example demonstrates:
- TransformationPipeline: Reusable transformation sequences
- ParameterSweep: Systematic parameter variation
- BatchProcessor: Parallel batch processing
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.composite import (
    TransformationPipeline,
    ParameterSweep,
    BatchProcessor
)
from matsimpy.transformation.structural import make_supercell
from matsimpy.transformation.lattice import apply_strain
from matsimpy.transformation.geometric import translate
import numpy as np

print("=" * 70)
print("MatSimPy Transformations - Composite Examples")
print("=" * 70)

# ============================================================================
# Example 1: TransformationPipeline
# ============================================================================
print("\n1. TransformationPipeline - Reusable Transformation Sequences")
print("-" * 70)

# Create base structure
base = from_prototype('diamond', 'Si', 5.43)
print(f"Base structure: {base.formula}, {len(base)} atoms")

# Define a pipeline for strain study
pipeline = TransformationPipeline("strain_study")
pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
pipeline.add_step(apply_strain, strain_matrix=[[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])

# Apply pipeline
result = pipeline.apply(base)
print(f"\nAfter pipeline:")
print(f"  Formula: {result.formula}")
print(f"  Atoms: {len(result)}")
print(f"  Lattice a: {result.lattice.a:.4f} Å")

# Apply to multiple structures
structures = [
    from_prototype('diamond', 'Si', 5.43),
    from_prototype('diamond', 'C', 3.57)
]
results = pipeline.apply_batch(structures)
print(f"\nApplied to {len(structures)} structures:")
for i, res in enumerate(results):
    print(f"  Structure {i+1}: {res.formula}, {len(res)} atoms")

# ============================================================================
# Example 2: ParameterSweep - Cartesian Product Mode
# ============================================================================
print("\n\n2. ParameterSweep - Cartesian Product Mode")
print("-" * 70)

# Create base structure
base = from_prototype('fcc', 'Cu', 3.61)

# Define parameter ranges
sweep = ParameterSweep(
    base_structure=base,
    transformations={
        'supercell': {
            'func': make_supercell,
            'params': {
                'scaling_matrix': [
                    [2, 2, 2],
                    [3, 3, 3],
                    [4, 4, 4]
                ]
            }
        }
    },
    mode='cartesian'
)

# Generate structures
structures = []
for struct, params in sweep:
    structures.append(struct)
print(f"Generated {len(structures)} structures:")
for i, struct in enumerate(structures):
    print(f"  Structure {i+1}: {struct.formula}, {len(struct)} atoms, "
          f"lattice a={struct.lattice.a:.2f} Å")

# ============================================================================
# Example 3: ParameterSweep - Zip Mode
# ============================================================================
print("\n\n3. ParameterSweep - Zip Mode")
print("-" * 70)

# Create base structure
base = from_prototype('diamond', 'Si', 5.43)

# Define parameter ranges (must have same length in zip mode)
sweep = ParameterSweep(
    base_structure=base,
    transformations={
        'strain': {
            'func': apply_strain,
            'params': {
                'strain_matrix': [
                    [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],  # 1% strain in x
                    [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],  # 2% strain in x
                    [[0.03, 0, 0], [0, 0, 0], [0, 0, 0]]   # 3% strain in x
                ]
            }
        }
    },
    mode='zip'
)

# Generate structures
structures = []
for struct, params in sweep:
    structures.append(struct)
print(f"Generated {len(structures)} structures with varying strain:")
for i, struct in enumerate(structures):
    print(f"  Structure {i+1}: lattice a={struct.lattice.a:.4f} Å")

# ============================================================================
# Example 4: BatchProcessor - Parallel Processing
# ============================================================================
print("\n\n4. BatchProcessor - Parallel Batch Processing")
print("-" * 70)

# Create multiple base structures
base_structures = [
    from_prototype('fcc', 'Cu', 3.61),
    from_prototype('bcc', 'Fe', 2.87),
    from_prototype('diamond', 'Si', 5.43),
    from_prototype('hcp', 'Mg', [3.21, 3.21, 5.21])
]

# Define transformations to apply in sequence
transformations = [
    lambda s: make_supercell(s, [2, 2, 2]),
    lambda s: apply_strain(s, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
]

# Process in batch
processor = BatchProcessor(
    transformations=transformations,
    n_workers=2,
    progress=False,  # Set to True to show progress bar
    error_handling='skip'
)
results = processor.process(base_structures)

print(f"\nProcessed {len(results)} structures:")
for i, result in enumerate(results):
    if result.success:
        print(f"  Structure {i+1}: {result.structure.formula}, "
              f"{len(result.structure)} atoms, "
              f"volume={result.structure.volume:.2f} Å³")
    else:
        print(f"  Structure {i+1}: Failed - {result.error}")

# ============================================================================
# Example 5: Complex Workflow with Pipeline and Sweep
# ============================================================================
print("\n\n5. Complex Workflow - Combining Pipeline and Sweep")
print("-" * 70)

# Create a pipeline for defect study
defect_pipeline = TransformationPipeline("defect_study")
defect_pipeline.add_step(make_supercell, scaling_matrix=[3, 3, 3])

# Create base structure
base = from_prototype('diamond', 'Si', 5.43)

# Apply pipeline first
supercell = defect_pipeline.apply(base)
print(f"After pipeline: {supercell.formula}, {len(supercell)} atoms")

# Then apply parameter sweep for different strain values
strain_sweep = ParameterSweep(
    base_structure=supercell,
    transformations={
        'strain': {
            'func': apply_strain,
            'params': {
                'strain_matrix': [
                    [[0.0, 0, 0], [0, 0, 0], [0, 0, 0]],      # No strain
                    [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],     # 1% strain
                    [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]]      # 2% strain
                ]
            }
        }
    },
    mode='zip'
)

# Generate strained structures
strained_structures = []
for struct, params in strain_sweep:
    strained_structures.append(struct)
print(f"\nGenerated {len(strained_structures)} strained structures:")
for i, struct in enumerate(strained_structures):
    print(f"  Structure {i+1}: lattice a={struct.lattice.a:.4f} Å")

print("\n" + "=" * 70)
print("Composite transformation examples completed!")
print("=" * 70)

