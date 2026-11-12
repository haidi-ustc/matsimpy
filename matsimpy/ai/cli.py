"""CLI entry point for MatSimPy AI REPL."""

import os
import typer
from .doctor import Doctor, render_diagnostics
from .agent import Agent
from .memory import AgentMemory
from .repl import ReplController
from .runtime import RUNTIME_SYSTEM_PROMPT
from .skill import SkillManager, Skill
from .provider import DEFAULT_MODEL, DeepSeekProvider
from .terminal import create_terminal

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
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
    if ctx.invoked_subcommand is not None:
        return
    _run_agent(workspace, model, api_key, base_url, command, verbose)


def build_agent(workspace=None, model=None, api_key=None, base_url=None) -> Agent:
    """The CLI's agent: DeepSeek provider, all builtin skills (``core`` loaded), soul.md prompt."""
    memory = AgentMemory()
    soul = memory.get_soul_prompt()
    skills = SkillManager()
    _register_all_skills(skills)
    if "core" in skills._skills:
        skills.load("core")
    return Agent(
        workspace=workspace,
        provider=DeepSeekProvider(api_key, model or os.getenv("MATSIMPY_AI_MODEL", DEFAULT_MODEL), base_url),
        skill_manager=skills,
        memory=memory,
        system_prompt=f"{RUNTIME_SYSTEM_PROMPT}\n\n{soul}" if soul.strip() else RUNTIME_SYSTEM_PROMPT,
        verbose_hook=print,  # tool-progress lines, as in 0.8.x
        source="cli",
    )


def _run_agent(workspace, model, api_key, base_url, command, verbose) -> None:
    agent = build_agent(workspace, model, api_key, base_url)
    if command:
        if verbose:
            print(f"[model: {agent.provider.model}]")
            print(f"[workspace: {agent.workspace.path}]")
        print(agent.run(command).response)
    else:
        agent.workspace.enter()
        create_terminal(ReplController.for_agent(agent)).run()


@app.command("doctor")
def doctor_command(
    workspace: str = typer.Option(
        None, "--workspace", "-w", help="Workspace path to inspect."
    ),
    network: bool = typer.Option(
        False,
        "--network",
        help="Make one provider connectivity request (may incur provider usage).",
    ),
) -> None:
    """Check agent configuration; remains offline unless --network is supplied."""

    typer.echo(render_diagnostics(Doctor(workspace=workspace).run(network=network)))


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
