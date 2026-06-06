"""General-purpose path expansion utilities."""

from __future__ import annotations

import os
from pathlib import Path


def expand_path(path: str) -> Path:
    """Expand user home directory (~) and environment variables ($VAR) in path.

    Args:
        path: Path string that may contain ~ or $VAR.

    Returns:
        Path: Expanded Path object.
    """
    expanded = os.path.expanduser(path)
    expanded = os.path.expandvars(expanded)
    return Path(expanded).expanduser()


__all__ = ["expand_path"]
