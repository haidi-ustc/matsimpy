"""Shared validation helpers for core structure metadata."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any, Optional, Tuple


def copy_properties(properties: Optional[Mapping[str, Any]]) -> dict:
    """Validate and deep-copy one site property mapping."""
    if properties is None:
        return {}
    if not isinstance(properties, Mapping):
        raise TypeError("Properties must be a dictionary or None.")
    return copy.deepcopy(dict(properties))


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
        raise TypeError("site_properties must be a sequence of dictionaries, not a single dictionary")

    props = list(site_properties)
    if not props:
        return ()
    if len(props) != n_atoms:
        raise ValueError(
            f"Number of site_properties ({len(props)}) must match number of atoms ({n_atoms})"
        )
    return tuple(copy_properties(p) for p in props)
