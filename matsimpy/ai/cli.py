"""CLI entry point for MatSimPy AI REPL."""

from .engine import AIEngine
from .skill import SkillManager, Skill, FunctionDef


def main():
    """Launch the AI REPL with all skills pre-registered."""
    engine = AIEngine()
    _register_all_skills(engine.skill_manager)
    engine.skill_manager.load("core")
    engine.repl()


def _register_all_skills(sm: SkillManager) -> None:
    """Register all available skills with the SkillManager."""
    # Import skill modules and register
    from .skills import core, builders, transformation, analysis, io, storage

    for mod in (core, builders, transformation, analysis, io, storage):
        name = mod.SKILL_NAME
        desc = mod.SKILL_DESCRIPTION
        funcs = mod.get_functions()
        sm.register(Skill(name, desc, funcs))


if __name__ == "__main__":
    main()
