"""Builder skill — structure constructors and modifiers."""

from matsimpy.builders.registry import registry
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "builders"
SKILL_DESCRIPTION = "Structure builders: prototypes, surfaces, alloys, defects, nanotubes, interfaces"


def get_functions() -> list[FunctionDef]:
    funcs = []
    for spec in registry.list_all():
        params = spec.parameter_schema or {"type": "object", "properties": {}}
        # Ensure required fields are present
        if "required" not in params:
            # Infer required from properties without defaults
            props = params.get("properties", {})
            required = [k for k, v in props.items()
                       if "default" not in v and k not in ("structure", "substrate", "film", "bottom", "top")]
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
