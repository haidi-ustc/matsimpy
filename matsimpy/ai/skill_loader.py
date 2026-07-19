"""Load and save Claude-compatible .skill.md files."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import tempfile

import yaml

from matsimpy.ai.agent_skills import (
    MAX_SKILL_BYTES,
    SkillValidationError,
    validate_skill_name,
)

SKILLS_DIR = Path.home() / ".matsimpy" / "ai" / "skills" / "generated"
_UNSAFE_SKILL_NAME_RE = re.compile(r"[^a-z0-9-]+")
_SECRET_KEYS = {"api_key", "authorization", "token", "password", "secret"}


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


@dataclass(frozen=True)
class MigrationResult:
    """Outcome of converting one legacy generated skill."""

    source: Path
    destination: Path
    name: str
    status: str
    dry_run: bool

    @property
    def migrated(self) -> bool:
        """Whether this call created the standard skill."""

        return self.status == "migrated"


def _parse_legacy_for_migration(path: Path) -> tuple[dict, str]:
    try:
        with path.open("rb") as legacy_file:
            content_bytes = legacy_file.read(MAX_SKILL_BYTES + 1)
        if len(content_bytes) > MAX_SKILL_BYTES:
            raise SkillValidationError(
                f"Invalid legacy skill at {path}: exceeds the "
                f"{MAX_SKILL_BYTES}-byte size limit"
            )
        content = content_bytes.decode("utf-8", errors="strict")
    except SkillValidationError:
        raise
    except UnicodeDecodeError as exc:
        raise SkillValidationError(
            f"Invalid legacy skill at {path}: content is not valid UTF-8: {exc}"
        ) from exc
    except OSError as exc:
        raise SkillValidationError(f"Invalid legacy skill at {path}: {exc}") from exc
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", content, re.DOTALL)
    if match is None:
        raise SkillValidationError(
            f"Invalid legacy skill at {path}: expected YAML frontmatter"
        )
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise SkillValidationError(
            f"Invalid legacy skill at {path}: invalid YAML frontmatter: {exc}"
        ) from exc
    if not isinstance(metadata, dict):
        raise SkillValidationError(
            f"Invalid legacy skill at {path}: frontmatter must be a mapping"
        )
    _reject_secret_keys(metadata, path)
    return metadata, match.group(2)


def _reject_secret_keys(value: object, path: Path) -> None:
    pending = [value]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if isinstance(current, Mapping):
            if id(current) in visited:
                continue
            visited.add(id(current))
            for key, nested in current.items():
                if isinstance(key, str) and key.casefold() in _SECRET_KEYS:
                    raise SkillValidationError(
                        f"Invalid legacy skill at {path}: secret-bearing metadata "
                        f"key {key!r} is not allowed"
                    )
                pending.append(nested)
        elif isinstance(current, (list, tuple)):
            if id(current) in visited:
                continue
            visited.add(id(current))
            pending.extend(current)


def _standard_skill_content(metadata: dict, body: str, path: Path) -> tuple[str, str]:
    name = validate_skill_name(metadata.get("name"), path)
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SkillValidationError(
            f"Invalid legacy skill at {path}: 'description' is required"
        )
    if len(description) > 1024:
        raise SkillValidationError(
            f"Invalid legacy skill at {path}: 'description' exceeds 1024 characters"
        )
    standard = {
        "name": name,
        "description": description,
        "metadata": {
            "matsimpy": {
                key: value
                for key, value in metadata.items()
                if key not in {"name", "description"}
            }
        },
    }
    frontmatter = yaml.safe_dump(standard, sort_keys=False, allow_unicode=True)
    return name, f"---\n{frontmatter}---\n{body}"


def migrate_legacy_skill(
    path: Path, destination: Path, dry_run: bool = False
) -> MigrationResult:
    """Convert a legacy ``*.skill.md`` file to a standard skill directory.

    Existing byte-identical migrations are reported as idempotent. Any other
    existing destination is treated as a collision and is never overwritten.
    Migration only writes the manifest; it does not discover or activate it.
    """

    source = Path(path)
    destination_root = Path(destination)
    legacy_metadata, body = _parse_legacy_for_migration(source)
    name, content = _standard_skill_content(legacy_metadata, body, source)
    skill_path = destination_root / name / "SKILL.md"
    result_kwargs = {
        "source": source,
        "destination": skill_path,
        "name": name,
        "dry_run": dry_run,
    }

    if skill_path.exists():
        if skill_path.is_file() and skill_path.read_text(encoding="utf-8") == content:
            return MigrationResult(status="already_migrated", **result_kwargs)
        raise FileExistsError(f"Skill migration collision at {skill_path}")
    if skill_path.parent.exists():
        raise FileExistsError(f"Skill migration collision at {skill_path.parent}")
    if dry_run:
        return MigrationResult(status="planned", **result_kwargs)

    destination_root.mkdir(parents=True, exist_ok=True)
    try:
        skill_path.parent.mkdir()
    except FileExistsError as exc:
        raise FileExistsError(f"Skill migration collision at {skill_path.parent}") from exc
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".SKILL.md-", dir=skill_path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.link(temporary, skill_path)
        except FileExistsError as exc:
            raise FileExistsError(
                f"Skill migration collision at {skill_path}"
            ) from exc
        finally:
            temporary.unlink(missing_ok=True)
    except OSError:
        try:
            skill_path.parent.rmdir()
        except OSError:
            pass
        raise
    return MigrationResult(status="migrated", **result_kwargs)


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


__all__ = [
    "MigrationResult",
    "migrate_legacy_skill",
    "parse_skill_md",
    "save_skill_md",
    "list_generated_skills",
    "discover_builtin_skills",
    "SKILLS_DIR",
    "SKILLS_PKG",
]
