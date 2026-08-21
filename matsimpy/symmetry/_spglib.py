"""Shared adapters between MatSimPy crystals and spglib cells."""

from __future__ import annotations

import numpy as np

from ..core import Crystal, get_el_sp


def to_spglib_cell(
    crystal: Crystal,
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Return the lattice, fractional positions, and atomic numbers for spglib."""
    return (
        np.asarray(crystal.lattice.lattice_vectors, dtype=float),
        np.asarray(crystal.frac_positions, dtype=float),
        [get_el_sp(symbol).atomic_no for symbol in crystal.species],
    )


__all__ = ["to_spglib_cell"]
