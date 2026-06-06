"""Load and save Claude-compatible .skill.md files."""

from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path.home() / ".matsimpy" / "ai" / "skills" / "generated"


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
) -> Path:
    """Save a skill as .skill.md file."""
    import yaml

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / f"{name}.skill.md"

    # Normalize name for filename
    safe_name = name.lower().replace(" ", "-").replace("_", "-")

    frontmatter = {
        "name": safe_name,
        "description": description,
        "category": "ai-generated",
        "version": "1.0.0",
        "load_mode": load_mode,
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
    path.write_text(content)
    return path


def list_generated_skills() -> list[dict]:
    """List all .skill.md files in the generated directory."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.skill.md")):
        parsed = parse_skill_md(path)
        if parsed:
            skills.append(parsed)
    return skills


__all__ = ["parse_skill_md", "save_skill_md", "list_generated_skills", "SKILLS_DIR"]
