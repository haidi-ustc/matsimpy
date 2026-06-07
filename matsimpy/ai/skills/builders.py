"""Builder skill — built from BuilderRegistry with real function signatures."""

from matsimpy.builders.registry import registry
from matsimpy.ai.skill import FunctionDef
from matsimpy.ai.skills._schema import first_doc_line, sig_to_schema

SKILL_NAME = "builders"
SKILL_DESCRIPTION = "Structure builders: prototypes, surfaces, alloys, defects, nanotubes, interfaces"
SKILL_KEYWORDS: list[str] = [
    "slab", "surface", "adsorbate", "vacancy", "defect", "alloy",
    "nanotube", "prototype", "fcc", "bcc", "hcp", "interstitial",
    "interface", "build", "create",
]


def get_functions() -> list[FunctionDef]:
    funcs = []
    for spec in registry.list_all():
        fn = spec.callable
        schema = sig_to_schema(fn)
        desc = spec.description or first_doc_line(fn)
        funcs.append(FunctionDef(
            name=spec.name,
            description=desc,
            parameters=schema,
            callable=fn,
            skill=SKILL_NAME,
            help_text=fn.__doc__ or desc,
        ))
    return funcs
