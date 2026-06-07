# Calculator Modules — Design Spec

Date: 2026-06-07
Status: Design approved

## Target Structure

```
matsimpy/calculator/
├── __init__.py            # re-exports all
├── base.py                # BaseCalculator (existing)
├── lj/                    # Lennard-Jones
│   ├── __init__.py
│   └── calculator.py
├── vasp/                  # adapted from pymatgen-core io.vasp
│   ├── __init__.py
│   ├── inputs.py          # Incar, Kpoints, Potcar, Poscar
│   ├── outputs.py         # Outcar, Vasprun, Oszicar, Chgcar, ...
│   └── sets.py            # Input sets (relax, static, etc.)
├── gaussian/              # adapted from pymatgen-core io.gaussian
│   ├── __init__.py
│   ├── inputs.py
│   └── outputs.py
└── lammps/                # adapted from pymatgen-core io.lammps
    ├── __init__.py
    ├── inputs.py
    └── outputs.py
```

## Remove
- `matsimpy/code/` — entire package
- `matsimpy/calculator/dft/` — merged into vasp/
- `matsimpy/calculator/ml/` — removed

## Source & Acknowledgment
Every file includes header:
```python
"""Adapted from pymatgen (https://pymatgen.org/).
Original: pymatgen.io.{module}.{file}
Copyright (c) pymatgen Development Team. MIT License.
"""
```

## Post-Copy Optimization
After copying from pymatgen-core:
1. Remove pymatgen internal dependencies — replace with matsimpy equivalents (Crystal ↔ Structure, Lattice)
2. Remove monty dependency where possible — use matsimpy serialization
3. Simplify imports — flat structure, fewer files where pymatgen splits too fine
4. Add type hints consistent with matsimpy conventions
5. Write tests for each module
6. Ensure compatibility with matsimpy's immutability contract
