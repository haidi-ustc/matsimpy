"""Small JSON-schema subset validator for MatSimPy registries."""

from __future__ import annotations

from numbers import Real
from typing import Any


def validate_kwargs(schema: dict | None, kwargs: dict[str, Any]) -> None:
    """Validate kwargs against the schema subset used by registry specs."""
    if not schema:
        return

    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in kwargs:
            raise ValueError(f"Missing required parameter: {name}")

    for name, value in kwargs.items():
        prop = properties.get(name)
        if not prop:
            continue
        _validate_value(name, value, prop)


def _validate_value(name: str, value: Any, schema: dict) -> None:
    if "oneOf" in schema:
        errors = []
        for option in schema["oneOf"]:
            try:
                _validate_value(name, value, option)
                return
            except (TypeError, ValueError) as exc:
                errors.append(str(exc))
        raise TypeError(f"Parameter '{name}' does not match any allowed schema: {'; '.join(errors)}")

    expected_type = schema.get("type")
    if expected_type is None:
        return

    if expected_type == "string":
        valid = isinstance(value, str)
    elif expected_type == "number":
        valid = isinstance(value, Real) and not isinstance(value, bool)
    elif expected_type == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == "boolean":
        valid = isinstance(value, bool)
    elif expected_type == "array":
        valid = isinstance(value, list)
    elif expected_type == "object":
        valid = isinstance(value, dict)
    else:
        return

    if not valid:
        article = "an" if expected_type in {"integer", "array", "object"} else "a"
        raise TypeError(f"Parameter '{name}' must be {article} {expected_type}")

    if expected_type == "array":
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(value) < min_items:
            raise ValueError(f"Parameter '{name}' must contain at least {min_items} items")
        if max_items is not None and len(value) > max_items:
            raise ValueError(f"Parameter '{name}' must contain at most {max_items} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_value(f"{name}[{index}]", item, item_schema)


__all__ = ["validate_kwargs"]
