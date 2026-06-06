"""Internal helpers shared by transformation functions."""

from __future__ import annotations

import copy
from typing import Iterable, Optional, Sequence, Union

import numpy as np

from ..core import Crystal, Molecule


Structure = Union[Crystal, Molecule]


def copy_site_properties(structure: Structure) -> Optional[list[dict]]:
    """Return deep-copied site properties, or ``None`` when absent."""
    props = getattr(structure, "site_properties", ())
    if not props:
        return None
    return [copy.deepcopy(prop) for prop in props]


def site_properties_for_indices(
    structure: Structure, indices: Iterable[int]
) -> Optional[list[dict]]:
    """Return deep-copied site properties reindexed by ``indices``."""
    props = getattr(structure, "site_properties", ())
    if not props:
        return None
    return [copy.deepcopy(props[int(index)]) for index in indices]


def repeated_site_properties_for_index(
    structure: Structure, index: int, count: int
) -> Optional[list[dict]]:
    """Return ``count`` copies of one site's properties, or ``None`` when absent."""
    props = getattr(structure, "site_properties", ())
    if not props:
        return None
    return [copy.deepcopy(props[index]) for _ in range(count)]


def rebuild_structure(
    source: Structure,
    species: Sequence[str],
    positions: Sequence[Sequence[float]],
    *,
    lattice=None,
    coords_are_cartesian: bool = False,
    pbc: Optional[Sequence[bool]] = None,
    site_properties: Optional[Sequence[dict]] = None,
) -> Structure:
    """Rebuild a structure while preserving source-level invariants by default."""
    if isinstance(source, Crystal):
        return Crystal(
            list(species),
            positions,
            lattice=lattice if lattice is not None else source.lattice,
            coords_are_cartesian=coords_are_cartesian,
            pbc=list(pbc if pbc is not None else source.pbc),
            site_properties=site_properties,
        )

    return Molecule(
        list(species),
        positions,
        site_properties=site_properties,
    )


from ..utils.validation import validate_vector3, validate_positive_scalar, validate_integer_matrix3
