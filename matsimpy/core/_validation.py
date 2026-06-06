"""Shared validation helpers for core structure metadata."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from numbers import Integral
from typing import Any, Optional, Tuple

import numpy as np

from ..utils.dict_utils import copy_properties

from .lattice import Lattice
from .periodic_table import Element, DUMMY_ELEMENTS


def normalize_species(
    specie: Any,
    *,
    allow_dummy: bool = True,
    none_as_dummy: bool = False,
) -> str:
    """Normalize one atomic species through the shared element validator."""
    if specie is None:
        if none_as_dummy:
            return "X"
        raise TypeError("Species cannot be None.")

    if isinstance(specie, Element):
        symbol = specie.symbol
    elif isinstance(specie, Integral) and not isinstance(specie, (bool, np.bool_)):
        symbol = Element.from_Z(int(specie)).symbol
    elif isinstance(specie, str):
        if not specie:
            raise ValueError("Species symbol cannot be empty.")
        symbol = Element(specie).symbol
    else:
        raise TypeError("Species must be a string, integer, or Element object.")

    if not allow_dummy and symbol in DUMMY_ELEMENTS:
        raise ValueError(f"Dummy species '{symbol}' is not allowed here.")
    return symbol


def validate_lattice(lattice: Any) -> Lattice:
    """Validate a Crystal lattice argument with domain-specific errors."""
    if lattice is None:
        raise ValueError("Crystal requires a Lattice.")
    if not isinstance(lattice, Lattice):
        raise TypeError(f"Crystal lattice must be a Lattice, got {type(lattice).__name__}.")
    return lattice


def validate_pbc(pbc: Optional[Sequence[Any]]) -> Tuple[bool, bool, bool]:
    """Validate and normalize periodic-boundary flags."""
    if pbc is None:
        return (True, True, True)
    if isinstance(pbc, (str, bytes)) or not isinstance(pbc, Sequence):
        raise ValueError("PBC must be a sequence of 3 booleans.")

    pbc_values = list(pbc)
    if len(pbc_values) != 3:
        raise ValueError("PBC must have exactly 3 elements (for a, b, c axes).")
    if not all(isinstance(value, (bool, np.bool_)) for value in pbc_values):
        raise ValueError("All PBC elements must be booleans.")
    return tuple(bool(value) for value in pbc_values)


def validate_site_properties(
    site_properties: Optional[Sequence[Mapping[str, Any]]],
    n_atoms: int,
) -> Tuple[dict, ...]:
    """Validate, length-check, and deep-copy per-atom site properties.

    ``None`` and an empty sequence both mean "no site properties".  A non-empty
    sequence must contain exactly one mapping per atom.
    """
    if site_properties is None:
        return ()
    if isinstance(site_properties, Mapping):
        raise TypeError(
            "site_properties must be a sequence of dictionaries, not a single dictionary"
        )

    props = list(site_properties)
    if not props:
        return ()
    if len(props) != n_atoms:
        raise ValueError(
            f"Number of site_properties ({len(props)}) must match number of atoms ({n_atoms})"
        )
    return tuple(copy_properties(p) for p in props)
