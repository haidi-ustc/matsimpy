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

### IO Module
- **`io_basic.py`** - Reading and writing structure files (VASP, XYZ, JSON)
- **`io_advanced.py`** - Advanced file format operations

### Calculator Module
- **`calculator_basic.py`** - Using calculators (LJ, ML) for energy and force calculations

### Configuration Module
- **`config_basic.py`** - Global configuration system usage

### Storage Module
- **`storage_basic.py`** - Persistent data storage for structures and results

### Integration Examples
- **`workflow_basic.py`** - Complete workflow from structure creation to analysis
- **`workflow_advanced.py`** - Advanced workflows with multiple transformations

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
- maggma (for `storage_basic.py` - install with `pip install MatSimPy[storage]`)

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

