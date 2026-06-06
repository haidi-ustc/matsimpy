"""
Typing protocols for structural type constraints.

These protocols allow transformations, IO handlers, and builders to
declare their type constraints without importing concrete Crystal/Molecule
classes, avoiding circular imports. They also serve as the stable interface
contract for plugins.
"""

from typing import Protocol, runtime_checkable
import numpy as np


@runtime_checkable
class StructureLike(Protocol):
    """Protocol for anything that behaves like a Structure."""

    species: tuple
    positions: np.ndarray
    lattice: object | None

    @property
    def formula(self) -> str: ...

    @property
    def composition(self) -> object: ...


@runtime_checkable
class CrystalLike(StructureLike, Protocol):
    """Protocol for periodic structures with a lattice."""

    lattice: object  # not None
    pbc: tuple

    @property
    def frac_positions(self) -> np.ndarray: ...

    @property
    def cart_positions(self) -> np.ndarray: ...


@runtime_checkable
class MoleculeLike(StructureLike, Protocol):
    """Protocol for non-periodic structures."""

    lattice: None


__all__ = ["StructureLike", "CrystalLike", "MoleculeLike"]
