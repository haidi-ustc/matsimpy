"""Transformation skill — built from TransformationRegistry with real function signatures."""

from matsimpy.ai.catalog import RegistryToolSource
from matsimpy.transformation.registry import registry
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "transformation"
SKILL_DESCRIPTION = "Structure transformations: geometric, lattice, atomic, chemical, structural"
SKILL_KEYWORDS: list[str] = [
    "translate", "rotate", "strain", "scale", "substitute",
    "supercell", "transform", "move",
]


def get_functions() -> list[FunctionDef]:
    return RegistryToolSource(
        registry,
        SKILL_NAME,
        include_first_parameter=True,
    ).get_functions()
