"""Builder skill — built from BuilderRegistry with real function signatures."""

from matsimpy.builders.registry import registry
from matsimpy.ai.catalog import RegistryToolSource
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "builders"
SKILL_DESCRIPTION = "Structure builders: prototypes, surfaces, alloys, defects, nanotubes, interfaces"
SKILL_KEYWORDS: list[str] = [
    "slab", "surface", "adsorbate", "vacancy", "defect", "alloy",
    "nanotube", "prototype", "fcc", "bcc", "hcp", "interstitial",
    "interface", "build", "create",
    "rocksalt", "rock salt", "racksalt",
    "generate", "random", "pyxtal",
]


def get_functions() -> list[FunctionDef]:
    return RegistryToolSource(registry, SKILL_NAME).get_functions()
