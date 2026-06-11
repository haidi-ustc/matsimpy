"""
TransformationRegistry — singleton registry for all TransformationSpecs.

Supports registration, lookup by name/category/structure type, parameter
validation, and plan execution.
"""

from __future__ import annotations

from ..exceptions import RegistryError
from ..utils.schema_validation import validate_kwargs
from .spec import TransformationSpec


class TransformationRegistry:
    """Singleton registry for transformation specs.

    Usage::

        from matsimpy.transformation.registry import registry
        from matsimpy.transformation.spec import TransformationSpec

        spec = TransformationSpec(
            name="translate",
            category="geometric",
            callable=translate,
            applicable_types=(Crystal, Molecule),
            ...
        )
        registry.register(spec)

        # Lookup
        spec = registry.get("translate")

        # Execute with type validation
        result = registry.apply("translate", crystal, vector=[1, 0, 0])

    Plugin entry point: ``'matsimpy.transformations'``.
    """

    def __init__(self) -> None:
        self._specs: dict[str, TransformationSpec] = {}

    # ------------------------------------------------------------------
    def register(self, spec: TransformationSpec) -> None:
        """Register a transformation spec.

        Raises:
            RegistryError: If a spec with the same name already exists.
        """
        if spec.name in self._specs:
            raise RegistryError(
                f"Transformation {spec.name!r} is already registered"
            )
        self._specs[spec.name] = spec

    # ------------------------------------------------------------------
    def get(self, name: str) -> TransformationSpec:
        """Look up a spec by name.

        Raises:
            KeyError: If not found.
        """
        if name not in self._specs:
            raise KeyError(f"Transformation {name!r} is not registered")
        return self._specs[name]

    # ------------------------------------------------------------------
    def list_all(self) -> list[TransformationSpec]:
        """Return all registered specs."""
        return list(self._specs.values())

    # ------------------------------------------------------------------
    def list_by_category(self, category: str) -> list[TransformationSpec]:
        """Return specs matching *category*."""
        return [s for s in self._specs.values() if s.category == category]

    # ------------------------------------------------------------------
    def list_applicable(self, structure_type: type) -> list[TransformationSpec]:
        """Return specs applicable to *structure_type*."""
        return [
            s for s in self._specs.values()
            if structure_type in s.applicable_types
        ]

    # ------------------------------------------------------------------
    def apply(self, name: str, structure, **kwargs):
        """Look up spec and apply the transformation with *kwargs*.

        Validates that the structure type matches the spec's
        applicable_types before calling.

        Args:
            name: Registered transformation name.
            structure: Crystal or Molecule to transform.
            **kwargs: Passed to the transformation function.

        Returns:
            Transformed structure (new object).

        Raises:
            KeyError: If *name* is not registered.
            TypeError: If *structure* type is not applicable.
        """
        spec = self.get(name)

        if not isinstance(structure, spec.applicable_types):
            allowed = ", ".join(t.__name__ for t in spec.applicable_types)
            raise TypeError(
                f"Transformation {name!r} expects {allowed}, "
                f"got {type(structure).__name__}"
            )

        validate_kwargs(spec.parameter_schema, kwargs)
        return spec.callable(structure, **kwargs)

    # ------------------------------------------------------------------
    def apply_plan(self, plan, structure):
        """Execute a TransformationPlan sequentially.

        Args:
            plan: TransformationPlan with steps to execute.
            structure: Starting structure.

        Returns:
            Transformed structure after all steps.
        """
        result = structure
        for step in plan.steps:
            result = self.apply(step.spec_name, result, **step.params)
        return result


# Module-level singleton
registry = TransformationRegistry()


__all__ = ["TransformationRegistry", "registry"]
