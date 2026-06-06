"""CLI entry point for MatSimPy AI REPL."""

import os
import typer
from .engine import AIEngine
from .skill import SkillManager, Skill
from .provider import DEFAULT_MODEL

app = typer.Typer()


@app.command()
def main(
    workspace: str = typer.Option(
        None, "--workspace", "-w",
        help="Working directory for file operations (default: ~/.matsimpy/ai/workspace)",
    ),
    model: str = typer.Option(
        None, "--model", "-m",
        help=f"DeepSeek model (default: {DEFAULT_MODEL})",
    ),
    api_key: str = typer.Option(
        None, "--api-key", "-k",
        help="DeepSeek API key (default: $DEEPSEEK_API_KEY)",
    ),
    base_url: str = typer.Option(
        None, "--base-url", "-b",
        help="API base URL (default: https://api.deepseek.com)",
    ),
):
    """Launch the MatSimPy AI REPL — interactive materials science assistant."""
    engine = AIEngine(
        api_key=api_key,
        model=model or os.getenv("MATSIMPY_AI_MODEL", DEFAULT_MODEL),
        base_url=base_url,
        workspace_path=workspace,
    )
    _register_all_skills(engine.skill_manager)
    engine.skill_manager.load("core")
    engine.repl()


def _register_all_skills(sm: SkillManager) -> None:
    from .skills import core, builders, transformation, analysis, io, storage
    for mod in (core, builders, transformation, analysis, io, storage):
        sm.register(Skill(mod.SKILL_NAME, mod.SKILL_DESCRIPTION, mod.get_functions()))


if __name__ == "__main__":
    app()
