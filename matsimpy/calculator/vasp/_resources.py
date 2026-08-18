from __future__ import annotations

from collections.abc import Mapping
from os import PathLike
from typing import Any

from monty.serialization import loadfn

from matsimpy.exceptions import FormatError


def load_vasp_resource(path: str | PathLike[str], *, required: bool = True) -> Mapping[str, Any]:
    """Load a VASP packaged mapping resource with explicit failure handling."""
    try:
        resource = loadfn(path)
    except FileNotFoundError as exc:
        if not required:
            return {}
        raise FormatError(f"Required VASP resource is missing or unreadable: {path}") from exc
    except Exception as exc:
        raise FormatError(f"Failed to load VASP resource {path}") from exc

    if not isinstance(resource, Mapping):
        raise FormatError(f"VASP resource must be a mapping: {path}")

    return resource
