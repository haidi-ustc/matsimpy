"""Contracts for automatic LLM tool discovery from MatSimPy registries."""

from matsimpy.ai.catalog import RegistryToolSource
from matsimpy.builders.registry import BuilderRegistry, BuilderSpec
from matsimpy.core import Crystal


def _build_demo(species: str, count: int = 1):
    return species, count


def test_registry_source_discovers_new_specs_without_ai_module_changes():
    registry = BuilderRegistry()
    source = RegistryToolSource(
        registry=registry,
        skill="builders",
        schema_attribute="parameter_schema",
    )

    assert source.get_functions() == []

    registry.register(BuilderSpec(
        name="build_demo",
        category="bulk",
        callable=_build_demo,
        description="Build a demonstration structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "species": {"type": "string"},
                "count": {"type": "integer", "minimum": 1, "default": 1},
            },
            "required": ["species"],
        },
    ))

    functions = source.get_functions()

    assert [function.name for function in functions] == ["build_demo"]
    assert functions[0].callable is _build_demo
    assert functions[0].parameters["properties"]["count"]["minimum"] == 1


def test_registry_source_reads_current_schema_on_every_refresh():
    registry = BuilderRegistry()
    first = BuilderSpec(
        name="build_demo",
        category="bulk",
        callable=_build_demo,
        parameter_schema={
            "type": "object",
            "properties": {"species": {"type": "string"}},
            "required": ["species"],
        },
    )
    registry.register(first)
    source = RegistryToolSource(registry, "builders", "parameter_schema")

    assert "count" not in source.get_functions()[0].parameters["properties"]

    registry._specs["build_demo"] = BuilderSpec(
        name="build_demo",
        category="bulk",
        callable=_build_demo,
        parameter_schema=None,
    )

    refreshed = source.get_functions()[0].parameters
    assert refreshed["properties"]["count"]["type"] == "integer"
    assert refreshed["properties"]["count"]["default"] == 1


def test_builtin_builder_tools_preserve_registry_schema():
    from matsimpy.ai.skills.builders import get_functions
    from matsimpy.builders.registry import registry

    tool = next(function for function in get_functions() if function.name == "from_prototype")
    spec = registry.get("from_prototype")

    assert tool.parameters == spec.parameter_schema


def test_builtin_transformation_tools_preserve_registry_constraints():
    from matsimpy.ai.skills.transformation import get_functions
    from matsimpy.transformation.registry import registry

    tool = next(function for function in get_functions() if function.name == "translate")
    spec = registry.get("translate")

    for name, constraint in (spec.parameter_schema or {}).get("properties", {}).items():
        assert tool.parameters["properties"][name] == constraint

    assert tool.parameters["properties"]["structure"]["required"] == ["structure_ref"]
    assert "structure" in tool.parameters["required"]


def test_every_transformation_exposes_its_actual_domain_object_parameter():
    import inspect
    from matsimpy.ai.skills.transformation import get_functions
    from matsimpy.transformation.registry import registry

    tools = {function.name: function for function in get_functions()}
    for spec in registry.list_all():
        first = next(iter(inspect.signature(spec.callable).parameters))
        assert first in tools[spec.name].parameters["properties"], spec.name
        assert first in tools[spec.name].parameters["required"], spec.name


def test_prototype_schema_matches_supported_domain_inputs():
    from matsimpy.ai.skills.builders import get_functions

    tool = next(function for function in get_functions() if function.name == "from_prototype")
    species_options = tool.parameters["properties"]["species"]["oneOf"]
    lattice_options = tool.parameters["properties"]["lattice_constant"]["oneOf"]

    assert {option["type"] for option in species_options} == {"string", "array"}
    assert {option["type"] for option in lattice_options} == {"number", "array"}


def test_builder_skill_routes_named_prototypes_and_common_rocksalt_misspelling():
    from matsimpy.ai.skill_loader import discover_builtin_skills

    builders = next(item for item in discover_builtin_skills() if item["name"] == "builders")

    assert {"rocksalt", "rock salt", "racksalt", "generate", "random", "pyxtal"} <= set(
        builders["keywords"]
    )


def test_builtin_llm_tool_names_are_globally_unique():
    from collections import Counter
    from matsimpy.ai.skill_loader import discover_builtin_skills

    names = [
        function.name
        for skill in discover_builtin_skills()
        for function in skill["functions"]
    ]
    duplicates = {name for name, count in Counter(names).items() if count > 1}
    assert duplicates == set()


def test_builtin_skill_routing_keywords_are_globally_unique():
    from collections import Counter
    from matsimpy.ai.skill_loader import discover_builtin_skills

    keywords = [keyword for skill in discover_builtin_skills() for keyword in skill["keywords"]]
    duplicates = {keyword for keyword, count in Counter(keywords).items() if count > 1}
    assert duplicates == set()
