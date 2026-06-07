"""Load and save Claude-compatible .skill.md files."""

from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path.home() / ".matsimpy" / "ai" / "skills" / "generated"
_UNSAFE_SKILL_NAME_RE = re.compile(r"[^a-z0-9-]+")


def _safe_skill_name(name: str) -> str:
    """Return a filesystem-safe generated skill slug."""
    safe_name = _UNSAFE_SKILL_NAME_RE.sub("-", name.lower()).strip("-")
    return safe_name[:120].strip("-") or "generated-skill"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def parse_skill_md(path: Path) -> dict | None:
    """Parse a .skill.md file — returns dict with frontmatter + body."""
    if not path.exists():
        return None
    content = path.read_text()
    # Extract YAML frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return None
    frontmatter = match.group(1)
    body = match.group(2).strip()
    # Parse YAML
    import yaml
    try:
        meta = yaml.safe_load(frontmatter)
    except Exception:
        return None
    meta["body"] = body
    meta["path"] = str(path)
    return meta


def save_skill_md(
    name: str,
    description: str,
    tools: list[dict],
    trigger_keywords: list[str],
    body: str = "",
    load_mode: str = "auto_choice",
    status: str = "approved",
) -> Path:
    """Save a skill as .skill.md file."""
    import yaml

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_skill_name(name)

    frontmatter = {
        "name": safe_name,
        "description": description,
        "category": "ai-generated",
        "version": "1.0.0",
        "load_mode": load_mode,
        "status": status,
        "trigger_keywords": trigger_keywords,
        "tools": tools,
        "created_at": datetime.now().isoformat(),
        "usage_count": 0,
    }

    content = f"---\n{yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)}---\n\n"
    if body:
        content += body
    else:
        content += f"# {description}\n\n"
        content += "## Steps\n"
        for i, tool in enumerate(tools, 1):
            content += f"{i}. `{tool.get('function', '?')}`"
            if tool.get("args_template"):
                content += f" — args: {tool['args_template']}"
            content += "\n"

    path = SKILLS_DIR / f"{safe_name}.skill.md"
    if not _is_relative_to(path.resolve(), SKILLS_DIR.resolve()):
        raise ValueError(f"Generated skill path escapes SKILLS_DIR: {path}")
    path.write_text(content)
    return path


def list_generated_skills(status: str | None = "approved") -> list[dict]:
    """List generated .skill.md files, optionally filtered by status."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.skill.md")):
        parsed = parse_skill_md(path)
        if parsed and (status is None or parsed.get("status", "approved") == status):
            skills.append(parsed)
    return skills


import importlib
import warnings
from pathlib import Path

SKILLS_PKG = Path(__file__).resolve().parent / "skills"


def discover_builtin_skills() -> list[dict]:
    """Scan matsimpy/ai/skills/ for modules exporting SKILL_NAME.

    Returns a list of dicts with keys: name, description, keywords, functions.
    Files without SKILL_NAME are silently skipped (utility modules, __init__.py).
    Files with SKILL_NAME but missing required fields get a warning and are skipped.
    Duplicate skill names get a warning and are skipped (first module wins).
    """
    skills = []
    seen_names: set[str] = set()

    for path in sorted(SKILLS_PKG.glob("*.py")):
        if path.name.startswith("_"):
            continue

        try:
            mod = importlib.import_module(f"matsimpy.ai.skills.{path.stem}")
        except Exception as exc:
            warnings.warn(f"Failed to import {path.stem}: {exc}")
            continue

        if not hasattr(mod, "SKILL_NAME"):
            continue

        name = mod.SKILL_NAME

        # Check required fields
        if not hasattr(mod, "SKILL_DESCRIPTION"):
            warnings.warn(f"Skill '{name}' in {path.stem} missing SKILL_DESCRIPTION — skipping")
            continue

        if not hasattr(mod, "get_functions") or not callable(mod.get_functions):
            warnings.warn(f"Skill '{name}' in {path.stem} missing callable get_functions() — skipping")
            continue

        if name in seen_names:
            warnings.warn(f"Skill '{name}' redefined by {path.stem} — skipping (already registered)")
            continue

        seen_names.add(name)
        skills.append({
            "name": name,
            "description": mod.SKILL_DESCRIPTION,
            "keywords": list(getattr(mod, "SKILL_KEYWORDS", [])),
            "functions": mod.get_functions(),
        })

    # Ensure core is always first (it's the always-loaded base skill)
    skills.sort(key=lambda s: (s["name"] != "core", s["name"]))

    return skills


__all__ = ["parse_skill_md", "save_skill_md", "list_generated_skills", "discover_builtin_skills", "SKILLS_DIR", "SKILLS_PKG"]
