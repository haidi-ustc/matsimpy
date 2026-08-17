# MatSimPy Examples

This directory contains comprehensive examples demonstrating how to use different modules of MatSimPy.

## Examples by Module

### Core Module
- **`core_basic.py`** - Basic usage of Crystal, Molecule, Lattice, and Composition
- **`core_advanced.py`** - Advanced features: coordinate conversions, sites, neighbor lists

### Builders Module
- **`builders_bulk.py`** - Building bulk crystal structures (FCC, BCC, etc.)
- **`builders_surface.py`** - Creating surface slabs and adding adsorbates
- **`builders_alloy.py`** - Generating random and ordered alloys
- **`builders_molecule.py`** - Building molecular structures
- **`builders_defects.py`** - Creating point defects in crystals
- **`builders_nanostructure.py`** - Building nanotubes and twisted structures

### Transformation Module
- **`transformation_geometric.py`** - Translation and rotation operations
- **`transformation_lattice.py`** - Lattice strain, scaling, transformations
- **`transformation_chemical.py`** - Chemical substitutions
- **`transformation_structural.py`** - Supercell generation, atom manipulation
- **`transformation_composite.py`** - High-throughput workflows (Pipeline, ParameterSweep, BatchProcessor)

### IO Module
- **`io_basic.py`** - Reading and writing structure files (VASP, XYZ, JSON)

### Calculator Module
- **`calculator_basic.py`** - Using calculators (Lennard-Jones and the MatterSim ML potential) for energy, force, and stress calculations

### Configuration Module
- **`config_basic.py`** - Global configuration system usage

### Storage Module
- **`storage_basic.py`** - Persistent data storage for structures and results

### Symmetry Module
- **`symmetry_basic.py`** - Symmetry analysis (space group, point group, conventional cell)

### Integration Examples
- **`workflow_basic.py`** - Complete workflow from structure creation to analysis

## Running Examples

Each example file is self-contained and can be run directly:

```bash
python examples/core_basic.py
```

Or interactively:

```python
exec(open('examples/core_basic.py').read())
```

## Requirements

All examples assume MatSimPy is installed. Some examples may require additional dependencies:
- RDKit (for SMILES parsing in molecule builders)
- PyXtal (for random crystal generation)
- MatterSim (for ML calculator examples)
- maggma (for `storage_basic.py` - install with `pip install MatSimPy[storage]`)

## MatterSim ML Calculator

`calculator_basic.py` demonstrates the `Mattersim` calculator, which drives MatterSim's M3GNet-based potentials directly from MatSimPy structures (no ASE required). To use it:

1. Install the dependencies: `pip install mattersim` (plus `torch`/`torch_geometric`).
2. Place a model checkpoint at `~/.matsimpy/models/`, e.g. `mattersim-v1.0.0-1M.pth.tar`, or pass `model_path` explicitly.

The MatSimPy `Mattersim` calculator is validated to reproduce the ASE-based MatterSim calculator (energy, forces, and stress agree to float32 precision) for both the diamond-Si example and arbitrary random cells. Note the stress units: `Mattersim.results["stress"]` is a **3×3 tensor in eV/Å³**, whereas ASE's `MatterSimCalculator.get_stress()` returns a **Voigt 6-vector in eV/Å³** — the same physical quantity, different shape.

## Example Output

All examples generate output files in the `examples_output/` directory (if applicable). The output directory is automatically created if it doesn't exist.

## Running All Examples

You can run all examples at once using the provided script:

```bash
bash examples/run.sh
```

Or manually:

```bash
for f in examples/*.py; do
    python "$f"
done
```
