"""Mark library functions as AI tools.

``@tool`` only attaches metadata to a function; it does not wrap or change it,
and it imports nothing from MatSimPy, so any layer can use it.
:mod:`matsimpy.ai.tools` finds marked functions and builds each tool's name,
description and parameter schema from the function itself: its name, its
signature and type hints, and its docstring.  Changing the function changes
the tool.

Example::

    from matsimpy.utils.tooling import tool

    @tool(name="write_structure", paths=("filename",))
    def write(structure, filename: str, format: str | None = None) -> None:
        '''Write a structure to a file.

        Args:
            structure: Structure to write.
            filename: Output path.
            format: Format name; detected from the extension if omitted.
        '''
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, overload

__all__ = ["ToolMarker", "tool", "tool_marker"]

_ATTRIBUTE = "__matsimpy_tool__"
F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class ToolMarker:
    """Overrides for a marked function.  ``None`` means "derive from the function"."""

    name: str | None = None
    description: str | None = None
    paths: tuple[str, ...] = ()
    """Parameters that are file paths: resolved inside the agent's workspace."""
    exclude: tuple[str, ...] = ()
    """Parameters hidden from the tool (they keep their default value)."""


@overload
def tool(func: F) -> F: ...


@overload
def tool(
    *,
    name: str | None = None,
    description: str | None = None,
    paths: tuple[str, ...] | list[str] = (),
    exclude: tuple[str, ...] | list[str] = (),
) -> Callable[[F], F]: ...


def tool(func=None, *, name=None, description=None, paths=(), exclude=()):
    """Mark ``func`` as an AI tool, optionally overriding its name or description."""
    marker = ToolMarker(name, description, tuple(paths), tuple(exclude))

    def mark(function):
        if not callable(function):
            raise TypeError(f"@tool needs a function, got {type(function).__name__}")
        setattr(function, _ATTRIBUTE, marker)
        return function

    return mark(func) if func is not None else mark


def tool_marker(obj: object) -> ToolMarker | None:
    """The :class:`ToolMarker` of a marked function, else ``None``."""
    marker = getattr(obj, _ATTRIBUTE, None)
    return marker if isinstance(marker, ToolMarker) else None
