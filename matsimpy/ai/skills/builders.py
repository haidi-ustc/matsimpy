"""Builder skill — built from BuilderRegistry with real function signatures."""

import inspect
import typing
from matsimpy.builders.registry import registry
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "builders"
SKILL_DESCRIPTION = "Structure builders: prototypes, surfaces, alloys, defects, nanotubes, interfaces"
SKILL_KEYWORDS: list[str] = [
    "slab", "surface", "adsorbate", "vacancy", "defect", "alloy",
    "nanotube", "prototype", "fcc", "bcc", "hcp", "interstitial",
    "interface", "build", "create",
]


def _resolve_annotation(ann) -> str | None:
    """Resolve typing annotation to a JSON Schema type string."""
    if ann is None or ann is inspect.Parameter.empty:
        return None
    origin = typing.get_origin(ann)
    args = typing.get_args(ann)

    # Union types: pick the simplest type
    if origin in (typing.Union,):
        if type(None) in args:
            # Optional[X] — use the other type
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return _resolve_annotation(non_none[0])
            return None
        # Multiple types — use the first
        return _resolve_annotation(args[0] if args else ann)

    # Direct type
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

    return None


def _sig_to_schema(fn) -> dict:
    """Build JSON Schema from actual function signature using type annotations."""
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return {"type": "object", "properties": {}}

    props = {}
    required = []
    for name, param in sig.parameters.items():
        if name in ("self", "kwargs", "args"):
            continue

        json_type = _resolve_annotation(param.annotation)
        prop = {"type": json_type} if json_type else {}

        # Handle common structural params specially
        if name in ("structure", "bulk", "substrate", "film", "bottom", "top", "other"):
            prop = {"description": "A Crystal or Molecule structure object"}

        if param.default is not inspect.Parameter.empty and param.default is not None:
            if isinstance(param.default, (str, int, float, bool)):
                prop["default"] = param.default
        elif param.default is None:
            pass  # None default = optional, don't add to required
        else:
            required.append(name)

        props[name] = prop

    return {
        "type": "object",
        "properties": props,
        "required": required if required else [],
    }


def get_functions() -> list[FunctionDef]:
    funcs = []
    for spec in registry.list_all():
        fn = spec.callable
        schema = _sig_to_schema(fn)
        desc = spec.description or (fn.__doc__ or "").split("\n")[0].strip()
        funcs.append(FunctionDef(
            name=spec.name,
            description=desc,
            parameters=schema,
            callable=fn,
            skill=SKILL_NAME,
            help_text=fn.__doc__ or desc,
        ))
    return funcs
