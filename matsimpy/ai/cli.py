"""CLI entry point for MatSimPy AI REPL."""

import os
import typer
from .engine import AIEngine
from .skill import SkillManager, Skill
from .provider import DEFAULT_MODEL

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


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
    command: str = typer.Option(
        None, "--command", "-c",
        help="Run a single command and exit (non-interactive mode)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Verbose output — show reasoning, token usage, full tool results",
    ),
):
    """Launch the MatSimPy AI REPL — interactive materials science assistant.

    \b
    Examples:
        matsimpy-ai -c "create fcc Cu and save to cu.vasp"
        matsimpy-ai -w ~/my-project -m deepseek-v4-flash
        matsimpy-ai -v -c "analyze bonds in nacl.cif"
    """
    engine = AIEngine(
        api_key=api_key,
        model=model or os.getenv("MATSIMPY_AI_MODEL", DEFAULT_MODEL),
        base_url=base_url,
        workspace_path=workspace,
    )
    engine.verbose = verbose
    _register_all_skills(engine.skill_manager)
    engine.skill_manager.load("core")

    if command:
        if verbose:
            print(f"[model: {engine.provider.model}]")
            if workspace:
                print(f"[workspace: {engine.workspace.path}]")
        response = engine.chat(command)
        print(response)
    else:
        engine.repl()


def _register_all_skills(sm: SkillManager) -> None:
    """Register all discovered builtin skills. No hard-coded imports."""
    from .skill_loader import discover_builtin_skills

    discovered = discover_builtin_skills()
    if not discovered:
        import warnings
        warnings.warn("No builtin skills discovered — REPL will have no tools")
        return

    for s in discovered:
        skill = Skill(s["name"], s["description"], s["functions"])
        skill.keywords = s["keywords"]
        sm.register(skill)


if __name__ == "__main__":
    app()
