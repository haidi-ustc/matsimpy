"""
TransformationSpec — structured metadata for transformation operations.

Each registered transformation function gets a TransformationSpec
describing its name, category, type constraints, behavioral guarantees,
parameter schema, and version.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TransformationSpec:
    """Metadata for a registered transformation.

    Attributes:
        name: Unique identifier, e.g. ``"translate"``, ``"create_vacancy"``.
        category: One of ``"geometric"``, ``"lattice"``, ``"atomic"``,
            ``"chemical"``, ``"structural"``.
        callable: The actual transformation function.
        description: One-line human-readable summary.
        applicable_types: Tuple of types the transform accepts,
            e.g. ``(Crystal, Molecule)`` or ``(Crystal,)``.
        output_type: The type returned (usually same as input).
        preserves_composition: True if species/counts are unchanged.
        preserves_lattice: True if the lattice matrix is unchanged.
        preserves_site_properties: True if per-atom properties survive.
        preserves_pbc: True if periodic boundary conditions are unchanged.
        parameter_schema: JSON Schema dict for **kwargs validation.
        version: Semver for this spec (not the function itself).
    """

    name: str
    category: str
    callable: Callable
    description: str = ""
    applicable_types: tuple = ()
    output_type: type | None = None
    preserves_composition: bool = True
    preserves_lattice: bool = True
    preserves_site_properties: bool = True
    preserves_pbc: bool = True
    parameter_schema: dict | None = None
    version: str = "1.0.0"


__all__ = ["TransformationSpec"]
