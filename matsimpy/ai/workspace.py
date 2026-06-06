"""Workspace manager — default working directory for file operations."""

import os
from pathlib import Path

DEFAULT_WORKSPACE = Path.home() / ".matsimpy" / "ai" / "workspace"


class Workspace:
    """Manages the AI agent's working directory."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path).expanduser().resolve() if path else DEFAULT_WORKSPACE
        self.path.mkdir(parents=True, exist_ok=True)
        self._original_cwd = os.getcwd()

    def enter(self) -> str:
        """Change to workspace directory. Returns the path."""
        os.chdir(str(self.path))
        return str(self.path)

    def leave(self) -> None:
        """Restore original working directory."""
        os.chdir(self._original_cwd)

    def resolve(self, filename: str) -> Path:
        """Resolve filename relative to workspace."""
        p = Path(filename)
        if p.is_absolute():
            return p
        return self.path / p

    def list_files(self, pattern: str = "*") -> list[str]:
        """List files in workspace matching glob pattern."""
        from glob import glob
        return [str(Path(f).relative_to(self.path)) for f in glob(str(self.path / pattern))]

    @property
    def home(self) -> str:
        return str(DEFAULT_WORKSPACE)


__all__ = ["Workspace"]
