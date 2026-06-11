"""
BuilderRegistry — registry for structure constructors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..utils.schema_validation import validate_kwargs


@dataclass(frozen=True)
class BuilderSpec:
    """Metadata for a registered structure builder.

    Attributes:
        name: Unique identifier.
        category: ``"bulk"`` | ``"surface"`` | ``"molecule"`` | ``"nanostructure"``.
        callable: The builder function.
        description: One-line summary.
        output_type: The type returned (Crystal or Molecule).
        parameter_schema: JSON Schema for **kwargs validation.
        requires_optional: Tuple of optional dependency names, e.g. ``("pyxtal",)``.
    """

    name: str
    category: str
    callable: Callable
    description: str = ""
    output_type: type | None = None
    parameter_schema: dict | None = None
    requires_optional: tuple[str, ...] = ()


class BuilderRegistry:
    """Singleton registry for structure builder specs.

    Plugin entry point: ``'matsimpy.builders'``.
    """

    def __init__(self) -> None:
        self._specs: dict[str, BuilderSpec] = {}

    def register(self, spec: BuilderSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Builder {spec.name!r} is already registered")
        self._specs[spec.name] = spec

    def get(self, name: str) -> BuilderSpec:
        if name not in self._specs:
            raise KeyError(f"Builder {name!r} is not registered")
        return self._specs[name]

    def build(self, name: str, **kwargs):
        """Validate and call the builder, return a structure."""
        spec = self.get(name)
        validate_kwargs(spec.parameter_schema, kwargs)
        return spec.callable(**kwargs)

    def list_all(self) -> list[BuilderSpec]:
        return list(self._specs.values())

    def list_by_category(self, category: str) -> list[BuilderSpec]:
        return [s for s in self._specs.values() if s.category == category]


registry = BuilderRegistry()
__all__ = ["BuilderSpec", "BuilderRegistry", "registry"]
