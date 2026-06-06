"""Transformation skill — operations on existing structures."""

from matsimpy.transformation.registry import registry
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "transformation"
SKILL_DESCRIPTION = "Structure transformations: geometric, lattice, atomic, chemical, structural"


def get_functions() -> list[FunctionDef]:
    funcs = []
    for spec in registry.list_all():
        params = spec.parameter_schema or {"type": "object", "properties": {}}
        if "required" not in params:
            props = params.get("properties", {})
            required = [k for k, v in props.items() if "default" not in v]
            if required:
                params = dict(params, required=required)
        funcs.append(FunctionDef(
            name=spec.name,
            description=spec.description,
            parameters=params,
            callable=spec.callable,
            skill=SKILL_NAME,
            help_text=getattr(spec.callable, "__doc__", spec.description),
        ))
    return funcs
