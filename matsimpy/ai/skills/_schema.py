"""Shared helpers for building JSON Schemas from MatSimPy function signatures."""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable


STRUCTURE_PARAM_NAMES = {
    "structure",
    "structures",
    "crystal",
    "molecule",
    "bulk",
    "substrate",
    "film",
    "bottom",
    "top",
    "other",
}


def resolve_annotation(ann) -> str | None:
    """Resolve a Python annotation to a JSON Schema primitive type."""
    if ann is None or ann is inspect.Parameter.empty:
        return None

    origin = typing.get_origin(ann)
    args = typing.get_args(ann)

    if origin in (typing.Union,):
        if type(None) in args:
            non_none = [arg for arg in args if arg is not type(None)]
            return resolve_annotation(non_none[0]) if non_none else None
        return resolve_annotation(args[0] if args else ann)

    if ann is str:
        return "string"
    if ann is int:
        return "integer"
    if ann is float:
        return "number"
    if ann is bool:
        return "boolean"

    origin_str = str(origin).lower() if origin else ""
    type_str = str(ann).lower()
    if "list" in origin_str or "list" in type_str:
        return "array"
    if "tuple" in origin_str or "tuple" in type_str:
        return "array"
    if "dict" in origin_str or "dict" in type_str:
        return "object"

    return None


def sig_to_schema(fn: Callable) -> dict:
    """Build a compact JSON Schema object from a callable signature."""
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return {"type": "object", "properties": {}, "required": []}

    props = {}
    required = []
    for name, param in sig.parameters.items():
        if name in ("self", "kwargs", "args"):
            continue

        if name in STRUCTURE_PARAM_NAMES:
            prop = {
                "type": "object",
                "description": "MatSimPy structure reference returned by a previous tool call",
            }
        else:
            json_type = resolve_annotation(param.annotation)
            prop = {"type": json_type} if json_type else {}

        if param.default is inspect.Parameter.empty:
            required.append(name)
        elif param.default is not None and isinstance(param.default, (str, int, float, bool)):
            prop["default"] = param.default

        props[name] = prop

    return {"type": "object", "properties": props, "required": required}


def first_doc_line(fn: Callable, fallback: str = "") -> str:
    """Return the first useful docstring line for tool descriptions."""
    doc = inspect.getdoc(fn) or fallback
    return doc.splitlines()[0].strip() if doc else fallback
