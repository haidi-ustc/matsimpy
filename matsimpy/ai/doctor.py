"""``matsimpy-ai doctor``: check the agent's configuration.

Offline by default.  ``network=True`` also asks the provider for its model list
and connects to each configured MCP server.  Exception texts of provider
requests are not shown, because HTTP errors can contain credentials.
"""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .mcp import USER_CONFIG, MCPClient, load_config
from .provider import DEFAULT_BASE_URL
from .skills import SkillLibrary
from .tools import ToolCatalog
from .workspace import DEFAULT_WORKSPACE

__all__ = ["Diagnostic", "Doctor", "render_diagnostics"]


@dataclass(frozen=True)
class Diagnostic:
    """One check: ``pass``, ``warn`` or ``fail``, with a summary and what to do."""

    code: str
    status: str
    summary: str
    action: str = ""


class Doctor:
    """Run the checks for a workspace."""

    def __init__(
        self,
        *,
        workspace: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
        mcp_config: Sequence[str | Path] | None = None,
        skills: SkillLibrary | None = None,
        tool_modules: Sequence[str] = (),
        network_probe: Callable[[], None] | None = None,
    ) -> None:
        self.workspace = Path(workspace).expanduser() if workspace else DEFAULT_WORKSPACE
        self.environ = os.environ if environ is None else environ
        self.mcp_config = list(mcp_config) if mcp_config is not None else [USER_CONFIG, self.workspace / "mcp.json"]
        self.skills = skills or SkillLibrary(self.workspace)
        self.tool_modules = tuple(tool_modules)
        self.network_probe = network_probe or self._probe_provider

    def run(self, network: bool = False) -> list[Diagnostic]:
        results = [
            self._api_key(),
            self._writable("workspace", self.workspace),
            self._tools(),
            *self._skills(),
            *self._mcp(network),
            self._package("requests", "provider-client", "Install the 'ai' extra: pip install 'MatSimPy[ai]'."),
            self._package("prompt_toolkit", "terminal-ui", "Install the 'repl' extra for history and completion."),
        ]
        if network:
            results.append(self._network())
        return results

    def _api_key(self) -> Diagnostic:
        if self.environ.get("DEEPSEEK_API_KEY"):
            return Diagnostic("provider-api-key", "pass", "DEEPSEEK_API_KEY is set")
        return Diagnostic("provider-api-key", "warn", "DEEPSEEK_API_KEY is not set",
                          "Set it before running the agent.")

    @staticmethod
    def _writable(code: str, path: Path) -> Diagnostic:
        existing = path
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        if os.access(existing, os.W_OK):
            return Diagnostic(code, "pass", f"{path} is writable")
        return Diagnostic(code, "fail", f"{path} is not writable", "Choose another workspace with --workspace.")

    def _tools(self) -> Diagnostic:
        try:
            catalog = ToolCatalog.default(self.tool_modules)
        except Exception as exc:
            return Diagnostic("tools", "fail", f"tool catalog failed: {type(exc).__name__}: {exc}")
        if catalog.skipped:
            skipped = "; ".join(f"{name}: {reason}" for name, reason in catalog.skipped.items())
            return Diagnostic("tools", "warn", f"{len(catalog)} tools; skipped {skipped}",
                              "Fix the annotations of the skipped functions.")
        return Diagnostic("tools", "pass", f"{len(catalog)} tools")

    def _skills(self) -> list[Diagnostic]:
        skills = self.skills.discover()
        results = [Diagnostic("skills", "pass", f"{len(skills)} skills: {', '.join(s.name for s in skills)}")]
        for path, problem in self.skills.problems.items():
            results.append(Diagnostic("skills", "warn", f"skipped {path}: {problem}", "Fix or remove the skill."))
        drafts = self.skills.drafts() if "user" in self.skills.roots else []
        if drafts:
            results.append(Diagnostic("skill-drafts", "warn", f"awaiting approval: {', '.join(d.name for d in drafts)}",
                                      "Review with /drafts, then /approve or /reject."))
        return results

    def _mcp(self, network: bool) -> list[Diagnostic]:
        try:
            servers = load_config(self.mcp_config)
        except ValueError as exc:
            return [Diagnostic("mcp-config", "fail", str(exc), "Fix mcp.json.")]
        if not servers:
            return [Diagnostic("mcp-config", "pass", "no MCP servers configured")]
        results = [Diagnostic("mcp-config", "pass", f"servers: {', '.join(servers)}")]
        for name, config in servers.items():
            if not config.enabled:
                results.append(Diagnostic(f"mcp:{name}", "pass", "disabled"))
            elif not network:
                where = config.command if config.transport == "stdio" else config.url
                results.append(Diagnostic(f"mcp:{name}", "pass", f"{config.transport} {where} (not connected; "
                                          "use --network to test)"))
            else:
                try:
                    with MCPClient(config) as client:
                        count = len(client.list_tools())
                    results.append(Diagnostic(f"mcp:{name}", "pass",
                                              f"connected (protocol {client.protocol_version}), {count} tools"))
                except Exception as exc:
                    results.append(Diagnostic(f"mcp:{name}", "fail", f"cannot connect: {exc}",
                                              "Check the command or URL in mcp.json."))
        return results

    @staticmethod
    def _package(module: str, code: str, action: str) -> Diagnostic:
        if importlib.util.find_spec(module) is not None:
            return Diagnostic(code, "pass", f"{module} installed")
        return Diagnostic(code, "warn", f"{module} not installed", action)

    def _network(self) -> Diagnostic:
        if not self.environ.get("DEEPSEEK_API_KEY"):
            return Diagnostic("provider-network", "warn", "not checked: no API key")
        try:
            self.network_probe()
        except Exception:  # deliberately not shown: may contain credentials
            return Diagnostic("provider-network", "fail", "provider request failed",
                              "Check the network, API key, base URL and model.")
        return Diagnostic("provider-network", "pass", "provider reachable")

    def _probe_provider(self) -> None:
        import requests

        base_url = self.environ.get("MATSIMPY_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        response = requests.get(f"{base_url}/models",
                                headers={"Authorization": f"Bearer {self.environ['DEEPSEEK_API_KEY']}"}, timeout=10)
        response.raise_for_status()


def render_diagnostics(diagnostics: Sequence[Diagnostic]) -> str:
    lines = []
    for item in diagnostics:
        line = f"[{item.status.upper()}] {item.code}: {item.summary}"
        if item.action:
            line += f" — {item.action}"
        lines.append(line)
    return "\n".join(lines)
