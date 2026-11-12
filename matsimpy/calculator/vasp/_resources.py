"""Loading of the data files shipped with ``matsimpy.calculator.vasp``.

Input-set YAMLs, POTCAR hashes/statistics and vdW parameters are package data.
A missing or broken file is an installation error, so it is reported where it
happens instead of being replaced by ``{}`` (which silently produced input sets
without INCAR defaults and disabled POTCAR validation).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from monty.serialization import loadfn

from matsimpy.exceptions import FormatError


def load_resource(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a JSON/YAML mapping (optionally ``.bz2``/``.gz`` compressed).

    Returns a new ``dict`` on every call, so callers may modify it.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        FormatError: if the file cannot be parsed or is not a mapping.
    """
    path = os.fspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VASP resource file not found: {path}")
    try:
        data = loadfn(path)
    except Exception as exc:
        raise FormatError(f"Cannot parse VASP resource file {path}: {exc}") from exc
    if not isinstance(data, Mapping):
        raise FormatError(
            f"VASP resource file {path} must contain a mapping, got {type(data).__name__}"
        )
    return dict(data)


__all__ = ["load_resource"]
