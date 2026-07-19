"""Secret-safe, offline-by-default diagnostics for the AI agent."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import sqlite3

from .agent_skills import SkillLibrary, SkillValidationError
from .provider import DEFAULT_BASE_URL
from .session_store import STATE_DB, _SCHEMA_VERSION
from .workspace import DEFAULT_WORKSPACE


@dataclass(frozen=True)
class Diagnostic:
    """One structured, safely renderable diagnostic result."""

    code: str
    status: str
    summary: str
    action: str


class Doctor:
    """Inspect local agent configuration without contacting a provider by default."""

    def __init__(
        self,
        *,
        workspace: str | Path | None = None,
        state_dir: str | Path | None = None,
        database: str | Path | None = None,
        skill_roots: Sequence[str | Path] | None = None,
        environ: Mapping[str, str] | None = None,
        network_probe: Callable[[], None] | None = None,
    ) -> None:
        self.workspace = Path(workspace).expanduser() if workspace else DEFAULT_WORKSPACE
        self.state_dir = (
            Path(state_dir).expanduser()
            if state_dir is not None
            else STATE_DB.parent
        )
        self.database = (
            Path(database).expanduser()
            if database is not None
            else self.state_dir / STATE_DB.name
        )
        self.environ = os.environ if environ is None else environ
        self.skill_roots = (
            tuple(Path(root).expanduser() for root in skill_roots)
            if skill_roots is not None
            else (
                Path.home() / ".matsimpy" / "ai" / "skills",
                self.workspace / ".matsimpy" / "skills",
            )
        )
        self.network_probe = network_probe or self._probe_provider

    def run(self, network: bool = False) -> list[Diagnostic]:
        """Return diagnostics, making a provider request only when requested."""

        results = [
            self._provider_configuration(),
            self._presence_check("provider-model", "MATSIMPY_AI_MODEL"),
            self._presence_check("provider-base-url", "MATSIMPY_AI_BASE_URL"),
            self._path_check("workspace", self.workspace),
            self._path_check("state-directory", self.state_dir),
            self._skill_check(),
            self._database_check(),
            self._package_check("prompt_toolkit", "ui-prompt-toolkit"),
            self._package_check("rich", "ui-rich"),
        ]
        if network:
            results.append(self._network_check())
        return results

    def _provider_configuration(self) -> Diagnostic:
        if self.environ.get("DEEPSEEK_API_KEY"):
            return Diagnostic("provider-api-key", "pass", "configured", "")
        return Diagnostic(
            "provider-api-key",
            "warn",
            "missing",
            "Set DEEPSEEK_API_KEY before running agent commands or --network.",
        )

    def _presence_check(self, code: str, environment_name: str) -> Diagnostic:
        summary = "configured" if self.environ.get(environment_name) else "default"
        return Diagnostic(code, "pass", summary, "")

    @staticmethod
    def _path_check(code: str, path: Path) -> Diagnostic:
        target = path if path.exists() else Doctor._nearest_existing_parent(path)
        if target is not None and os.access(target, os.W_OK | os.X_OK):
            return Diagnostic(code, "pass", "writable", "")
        return Diagnostic(
            code,
            "fail",
            "not writable",
            f"Choose a writable {code} path or correct its permissions.",
        )

    @staticmethod
    def _nearest_existing_parent(path: Path) -> Path | None:
        candidate = path.absolute()
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        return candidate if candidate.exists() else None

    def _skill_check(self) -> Diagnostic:
        count = 0
        try:
            for root in self.skill_roots:
                if not root.exists():
                    continue
                count += len(SkillLibrary(workspace=root).discover())
        except (SkillValidationError, OSError, UnicodeError):
            return Diagnostic(
                "skills",
                "fail",
                "invalid skill metadata",
                "Run skill validation and repair or remove the invalid skill directory.",
            )
        return Diagnostic("skills", "pass", f"valid ({count} discovered)", "")

    def _database_check(self) -> Diagnostic:
        if not self.database.exists():
            return Diagnostic("database", "pass", "not created yet", "")
        try:
            uri = f"file:{self.database.resolve()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                row = connection.execute("SELECT version FROM schema_meta").fetchone()
            if row is None:
                raise sqlite3.DatabaseError("missing schema version")
            version = int(row[0])
        except (OSError, sqlite3.Error, TypeError, ValueError):
            return Diagnostic(
                "database",
                "fail",
                "incompatible or unreadable",
                "Back up the state database, then migrate or recreate it.",
            )
        if version > _SCHEMA_VERSION:
            return Diagnostic(
                "database",
                "fail",
                "schema is newer than this MatSimPy version",
                "Upgrade MatSimPy or use a compatible state database.",
            )
        return Diagnostic("database", "pass", "compatible", "")

    @staticmethod
    def _package_check(module: str, code: str) -> Diagnostic:
        if importlib.util.find_spec(module) is not None:
            return Diagnostic(code, "pass", "installed", "")
        return Diagnostic(
            code,
            "warn",
            "not installed",
            "Install MatSimPy with the 'repl' extra for the enhanced terminal UI.",
        )

    def _network_check(self) -> Diagnostic:
        if not self.environ.get("DEEPSEEK_API_KEY"):
            return Diagnostic(
                "provider-network",
                "warn",
                "not checked: API key missing",
                "Set DEEPSEEK_API_KEY and rerun doctor --network.",
            )
        try:
            self.network_probe()
        except Exception:  # Provider libraries expose unrelated exception families.
            # Exception text is deliberately discarded: HTTP clients may embed
            # authorization headers, URLs with credentials, or response bodies.
            return Diagnostic(
                "provider-network",
                "fail",
                "provider check failed",
                "Check connectivity, credentials, base URL, and model configuration.",
            )
        return Diagnostic("provider-network", "pass", "provider reachable", "")

    def _probe_provider(self) -> None:
        import requests

        base_url = self.environ.get("MATSIMPY_AI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {self.environ['DEEPSEEK_API_KEY']}"},
            timeout=10,
        )
        response.raise_for_status()


def render_diagnostics(diagnostics: Sequence[Diagnostic]) -> str:
    """Render diagnostics using only the bounded structured fields above."""

    lines = []
    for item in diagnostics:
        line = f"[{item.status.upper()}] {item.code}: {item.summary}"
        if item.action:
            line += f" — {item.action}"
        lines.append(line)
    return "\n".join(lines)


__all__ = ["Diagnostic", "Doctor", "render_diagnostics"]
