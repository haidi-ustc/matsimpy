"""
External library adapters for MatSimPy.

Provides converters to/from:
- pymatgen (Structure, Molecule)
- ASE (Atoms)

Each adapter lazily imports its dependency at call time.
If the dependency is not installed, ImportError is raised with
an install hint.

Usage::

    >>> from matsimpy.adapters.pymatgen import to_pymatgen, from_pymatgen
    >>> pmg_struct = to_pymatgen(crystal)
    >>> crystal = from_pymatgen(pmg_struct)
"""

__all__ = []
