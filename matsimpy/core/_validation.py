"""Shared validation helpers for core structure metadata."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from numbers import Integral
from typing import Any, Optional, Tuple

import numpy as np

from ..utils.dict_utils import copy_properties

from .lattice import Lattice
from .periodic_table import Element, ELEMENTS, DUMMY_ELEMENTS


_CANONICAL_SYMBOLS = frozenset(ELEMENTS) | frozenset(DUMMY_ELEMENTS)


def normalize_species(
    specie: Any,
    *,
    allow_dummy: bool = True,
    none_as_dummy: bool = False,
) -> str:
    """Normalize one atomic species through the shared element validator."""
    if type(specie) is str and specie in _CANONICAL_SYMBOLS:
        # Fast path: already a canonical symbol (every structure re-validates
        # its species on construction, so this is hot).
        if not allow_dummy and specie in DUMMY_ELEMENTS:
            raise ValueError(f"Dummy species '{specie}' is not allowed here.")
        return specie
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
    if isinstance(pbc, np.ndarray):
        if pbc.dtype != bool or pbc.shape != (3,):
            raise ValueError("PBC must be a sequence of 3 booleans.")
        pbc = pbc.tolist()
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


# Sentinel for "no default given" in Structure.site_property().
_MISSING = object()


def _validate_metadata(metadata: Optional[Mapping[str, Any]]) -> dict:
    """Validate and deep-copy structure-level metadata (string keys only)."""
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise TypeError(f"metadata must be a mapping, got {type(metadata).__name__}")
    if not all(isinstance(k, str) for k in metadata):
        raise TypeError("metadata keys must be strings")
    return copy.deepcopy(dict(metadata))


def resolve_indices(structure: Any, indices: Any) -> Any:
    """Unwrap a selection object into plain indices.

    Accepts anything exposing ``.structure`` and ``.indices`` (such as
    ``matsimpy.analysis.AtomSelection``) by duck typing, so core never imports
    the analysis layer.  Other inputs are returned unchanged.
    """
    if hasattr(indices, "indices") and hasattr(indices, "structure"):
        if indices.structure is not structure:
            raise ValueError("AtomSelection must be created from this structure")
        return list(indices.indices)
    return indices


def reject_bool_coordinates(values: Any, what: str = "Positions") -> None:
    """Raise ``TypeError`` if *values* contains booleans.

    ``np.array([True, 0, 0], dtype=float)`` silently gives ``[1., 0., 0.]``,
    which hides a caller bug (e.g. a mask passed where coordinates belong).
    """
    if isinstance(values, np.ndarray):
        if values.dtype == bool:
            raise TypeError(f"{what} must be numeric, got a boolean array")
        if values.dtype != object:
            return
    if isinstance(values, (bool, np.bool_)):
        raise TypeError(f"{what} must be numeric, got bool")
    try:
        flat = np.ravel(np.asarray(values, dtype=object))
    except (TypeError, ValueError):
        return  # ragged input: the numeric conversion that follows reports it
    if any(isinstance(v, (bool, np.bool_)) for v in flat):
        raise TypeError(f"{what} must be numeric, got bool")


def validate_cutoff(cutoff, *, allow_zero=True):
    """Validate a neighbor-list cutoff radius.

    Args:
        cutoff: The cutoff value to validate.
        allow_zero: Whether zero-radius queries are permitted.

    Returns:
        float: The validated cutoff.

    Raises:
        ValueError: If cutoff is negative, NaN, or infinite.
        TypeError: If cutoff is not numeric.
    """
    if isinstance(cutoff, (bool, np.bool_)) or not isinstance(cutoff, (int, float, np.integer, np.floating)):
        raise TypeError(f"cutoff must be a number, got {type(cutoff).__name__}")
    value = float(cutoff)
    if np.isnan(value):
        raise ValueError("cutoff must not be NaN")
    if np.isinf(value):
        raise ValueError("cutoff must be finite")
    if value < 0:
        raise ValueError(f"cutoff must be non-negative, got {value}")
    if value == 0 and not allow_zero:
        raise ValueError("cutoff must be positive, got 0")
    return value
