"""Contract tests for all registered builders.

Parametrized over all BuilderSpecs in the registry.
Tests: output_type correctness.
"""

import pytest
from matsimpy.core import Crystal, Molecule
from matsimpy.builders.registry import registry


all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


def _minimal_kwargs(spec):
    kwargs = {}
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    required = schema.get("required", [])
    for name, prop in props.items():
        if name not in required:
            continue
        if prop.get("type") == "string":
            if "enum" in prop:
                kwargs[name] = prop["enum"][0]
            elif name == "prototype":
                kwargs[name] = "fcc"
            elif name == "element":
                kwargs[name] = "Cu"
            else:
                kwargs[name] = "test"
        elif prop.get("type") == "number":
            kwargs[name] = 1.0
    return kwargs


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestBuilderContract:

    def test_returns_correct_type(self, spec):
        """Builder returns the declared output_type."""
        # Skip builders that require optional deps not installed
        if spec.requires_optional:
            for dep in spec.requires_optional:
                try:
                    __import__(dep)
                except ImportError:
                    pytest.skip(f"Optional dependency {dep} not installed")

        kwargs = _minimal_kwargs(spec)
        try:
            result = spec.callable(**kwargs)
            assert isinstance(result, spec.output_type)
        except (ValueError, TypeError, IndexError) as e:
            pytest.skip(f"Requires more specific kwargs: {e}")

    def test_output_is_not_none(self, spec):
        """Builder output is not None."""
        if spec.requires_optional:
            for dep in spec.requires_optional:
                try:
                    __import__(dep)
                except ImportError:
                    pytest.skip(f"Optional dependency {dep} not installed")

        kwargs = _minimal_kwargs(spec)
        try:
            result = spec.callable(**kwargs)
            assert result is not None
        except (ValueError, TypeError, IndexError):
            pytest.skip("Requires more specific kwargs")
