"""
Pytest configuration file.

This file is automatically loaded by pytest and sets up the test environment.
It ensures the matsimpy package is importable by adding the parent directory
to sys.path. This eliminates the need for sys.path.insert in individual test files.
"""
import sys
import os

import pytest

# Add the parent directory to the path so matsimpy can be imported
# This is only needed if the package is not installed in development mode
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def has_torch():
    """Check if torch is installed."""
    try:
        import torch
        return True
    except ImportError:
        return False


def has_torch_geometric():
    """Check if torch_geometric is installed."""
    try:
        import torch_geometric
        return True
    except ImportError:
        return False


def has_ase():
    """Check if ase is installed."""
    try:
        import ase
        return True
    except ImportError:
        return False


def has_pymatgen():
    """Check if pymatgen is installed."""
    try:
        import pymatgen
        return True
    except ImportError:
        return False


def make_cubic_lattice(a=10.0):
    """Return a simple cubic lattice for tests."""
    from matsimpy.core import Lattice

    return Lattice.cubic(a)


def make_simple_molecule():
    """Return a reusable two-atom molecule for tests."""
    from matsimpy.core import Molecule

    return Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])


def make_simple_crystal(lattice=None):
    """Return a reusable two-atom crystal for tests."""
    from matsimpy.core import Crystal

    if lattice is None:
        lattice = make_cubic_lattice(10.0)
    return Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)


@pytest.fixture
def cubic_lattice():
    return make_cubic_lattice()


@pytest.fixture
def simple_molecule():
    return make_simple_molecule()


@pytest.fixture
def simple_crystal():
    return make_simple_crystal()
