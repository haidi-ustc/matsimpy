"""The agent's workspace: the directory its tools read and write (default: the current directory)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from collections.abc import Iterator

_CWD_LOCK = RLock()


class Workspace:
    """The AI agent's working directory.

    Args:
        path: The directory; created if missing.  Default: the current directory,
            so files the agent writes land where it was started.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path).expanduser().resolve() if path else Path.cwd().resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        self._original_cwd = os.getcwd()

    def enter(self) -> str:
        """Change to workspace directory. Returns the path."""
        os.chdir(str(self.path))
        return str(self.path)

    def leave(self) -> None:
        """Restore original working directory."""
        os.chdir(self._original_cwd)

    @contextmanager
    def activate(self) -> Iterator[Workspace]:
        """Enter this workspace and restore the immediate caller's directory."""
        # Relative-path tools still require cwd compatibility. Serialize that
        # inherently process-global operation and always restore the caller.
        with _CWD_LOCK:
            previous = Path.cwd()
            os.chdir(self.path)
            try:
                yield self
            finally:
                os.chdir(previous)

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


__all__ = ["Workspace"]
