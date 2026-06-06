"""General-purpose dictionary and nested-access helpers."""

from __future__ import annotations

import copy
from typing import Any, Mapping, Optional


def get_nested_value(data: dict, key_path: str, default: Any = None) -> Any:
    """Get a value from a nested dict using dot-notation key path."""
    keys = key_path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def set_nested_value(data: dict, key_path: str, value: Any) -> None:
    """Set a value in a nested dict using dot-notation key path.

    Creates intermediate dicts as needed.
    """
    keys = key_path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def copy_properties(properties: Optional[Mapping[str, Any]]) -> dict:
    """Return a deep copy of *properties* dict, or empty dict if None.

    Raises:
        TypeError: If *properties* is not a dict or None.
    """
    if properties is None:
        return {}
    if not isinstance(properties, Mapping):
        raise TypeError("Properties must be a dictionary or None.")
    return copy.deepcopy(dict(properties))


__all__ = ["get_nested_value", "set_nested_value", "copy_properties"]
