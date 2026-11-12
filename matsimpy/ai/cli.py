"""``matsimpy-ai``: the interactive agent, one-shot tasks, and management commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from .doctor import Doctor, render_diagnostics
from .provider import DEFAULT_MODEL

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, no_args_is_help=False)
skills_app = typer.Typer(help="Manage skills.")
tools_app = typer.Typer(help="Inspect tools.")
mcp_app = typer.Typer(help="MCP server and client.")
app.add_typer(skills_app, name="skills")
app.add_typer(tools_app, name="tools")
app.add_typer(mcp_app, name="mcp")

WORKSPACE = typer.Option(None, "--workspace", "-w", help="Workspace directory (default ~/.matsimpy/ai/workspace).")
TOOL_MODULES = typer.Option([], "--tools", "-t", help="Extra module with @tool functions (repeatable).")


def build_agent(workspace=None, model=None, api_key=None, base_url=None, tool_modules=(), verbose=True):
    """The agent of the CLI: DeepSeek provider, default tools, skills, MCP servers and memory."""
    from .agent import Agent
    from .memory import AgentMemory
    from .provider import DeepSeekProvider
    from .terminal import format_event

    def show(event: str, data: dict) -> None:
        line = format_event(event, data)
        if line and (verbose or event == "warning"):
            print(line, file=sys.stderr)

    return Agent(DeepSeekProvider(api_key, model, base_url), workspace=workspace, tool_modules=tool_modules,
                 memory=AgentMemory(), on_event=show)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    workspace: Optional[str] = WORKSPACE,
    model: Optional[str] = typer.Option(None, "--model", "-m", help=f"Model (default {DEFAULT_MODEL})."),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key (default $DEEPSEEK_API_KEY)."),
    base_url: Optional[str] = typer.Option(None, "--base-url", "-b", help="OpenAI-compatible API base URL."),
    command: Optional[str] = typer.Option(None, "--command", "-c", help="Run one request and exit."),
    resume: Optional[str] = typer.Option(None, "--resume", "-r", help="Resume a saved session."),
    tool_modules: list[str] = TOOL_MODULES,
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Do not show tool calls."),
    raw: bool = typer.Option(False, "--raw", help="Print answers as Markdown source (the default when piped)."),
) -> None:
    """Chat with the MatSimPy agent, or run one request with -c.

    \b
    Examples:
        matsimpy-ai -c "build fcc Cu with a=3.61 and save it as cu.cif"
        matsimpy-ai -w ~/project --resume 20261112-101500-ab12
        matsimpy-ai doctor
        matsimpy-ai mcp serve
    """
    if ctx.invoked_subcommand is not None:
        return
    from .repl import ReplController
    from .terminal import create_terminal, markdown_printer

    try:
        agent = build_agent(workspace, model, api_key, base_url, tool_modules, verbose=not quiet)
    except ValueError as exc:  # e.g. no API key
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)
    with agent:
        if resume:
            agent.resume(resume)
        if command:
            result = agent.run(command)
            if result.status == "error":
                typer.echo(f"Error: {result.response}", err=True)
            else:
                markdown_printer(markdown=False if raw else None)(result.response)
            raise typer.Exit(0 if result.status == "success" else 1)
        create_terminal(ReplController(agent), markdown=False if raw else None).run()


@app.command("doctor")
def doctor_command(
    workspace: Optional[str] = WORKSPACE,
    network: bool = typer.Option(False, "--network", help="Also contact the provider and the MCP servers."),
    tool_modules: list[str] = TOOL_MODULES,
) -> None:
    """Check the API key, workspace, tools, skills and MCP configuration."""
    diagnostics = Doctor(workspace=workspace, tool_modules=tool_modules).run(network=network)
    typer.echo(render_diagnostics(diagnostics))
    if any(item.status == "fail" for item in diagnostics):
        raise typer.Exit(1)


# skills --------------------------------------------------------------------


def _library(workspace):
    from .skills import SkillLibrary
    from .workspace import Workspace

    return SkillLibrary(Workspace(workspace).path)


@skills_app.command("list")
def skills_list(workspace: Optional[str] = WORKSPACE) -> None:
    """List available skills and drafts."""
    library = _library(workspace)
    for skill in library.discover():
        typer.echo(f"{skill.name} ({skill.source}): {skill.description}")
    for draft in library.drafts():
        typer.echo(f"{draft.name} (draft, needs approval): {draft.description}")
    for path, problem in library.problems.items():
        typer.echo(f"skipped {path}: {problem}", err=True)


@skills_app.command("install")
def skills_install(path: Path, replace: bool = typer.Option(False, "--replace"),
                   workspace: Optional[str] = WORKSPACE) -> None:
    """Install a skill directory or .zip into ~/.matsimpy/ai/skills."""
    summary = _run(lambda: _library(workspace).install(path, replace=replace))
    typer.echo(f"Installed {summary.name} in {summary.path}")


@skills_app.command("remove")
def skills_remove(name: str, workspace: Optional[str] = WORKSPACE) -> None:
    """Remove an installed skill."""
    path = _run(lambda: _library(workspace).remove(name))
    typer.echo(f"Removed {path}")


@skills_app.command("validate")
def skills_validate(path: Path) -> None:
    """Check a skill directory without installing it."""
    from .skills import validate

    problems = validate(path)
    typer.echo("\n".join(problems) if problems else "Valid.")
    if problems:
        raise typer.Exit(1)


@skills_app.command("approve")
def skills_approve(name: str, workspace: Optional[str] = WORKSPACE) -> None:
    """Approve a draft skill."""
    summary = _run(lambda: _library(workspace).approve(name))
    typer.echo(f"Approved {summary.name}")


@skills_app.command("reject")
def skills_reject(name: str, workspace: Optional[str] = WORKSPACE) -> None:
    """Delete a draft skill."""
    _run(lambda: _library(workspace).reject(name))
    typer.echo(f"Deleted draft {name}")


def _run(action):
    from .skills import SkillError

    try:
        return action()
    except SkillError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


# tools ---------------------------------------------------------------------


@tools_app.command("list")
def tools_list(query: Optional[str] = typer.Argument(None), tool_modules: list[str] = TOOL_MODULES) -> None:
    """List tools, or those matching QUERY."""
    from .tools import ToolCatalog

    catalog = ToolCatalog.default(tool_modules)
    tools = catalog.search(query, limit=50) if query else catalog.values()
    for tool in tools:
        typer.echo(f"{tool.name}: {tool.summary()}")


@tools_app.command("show")
def tools_show(name: str, tool_modules: list[str] = TOOL_MODULES) -> None:
    """Show a tool's description and JSON schema."""
    from .tools import ToolCatalog

    catalog = ToolCatalog.default(tool_modules)
    if name not in catalog:
        typer.echo(f"Error: unknown tool {name!r}", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(catalog[name].openai_schema()["function"], indent=2))


# mcp -----------------------------------------------------------------------


@mcp_app.command("serve")
def mcp_serve(workspace: Optional[str] = typer.Option(None, "--workspace", "-w",
                                                     help="Directory for files (default: current directory)."),
              tool_modules: list[str] = TOOL_MODULES) -> None:
    """Serve MatSimPy's tools to MCP clients over stdio."""
    from .mcp import MCPServer
    from .tools import ToolCatalog

    MCPServer(ToolCatalog.default(tool_modules), workspace or Path.cwd()).serve()


@mcp_app.command("list")
def mcp_list(workspace: Optional[str] = WORKSPACE) -> None:
    """Connect to the configured MCP servers and list their tools."""
    from .mcp import USER_CONFIG, connect_servers, load_config
    from .workspace import Workspace

    servers = load_config([USER_CONFIG, Workspace(workspace).path / "mcp.json"])
    clients, errors = connect_servers(servers)
    for client in clients:
        with client:
            typer.echo(f"{client.name} ({client.config.transport}, protocol {client.protocol_version})")
            for tool in client.list_tools():
                typer.echo(f"  {tool['name']}: {(tool.get('description') or '').splitlines()[0][:100] if tool.get('description') else ''}")
    for name, error in errors.items():
        typer.echo(f"{name}: unavailable ({error})", err=True)


if __name__ == "__main__":
    app()
