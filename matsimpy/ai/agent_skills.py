"""Safe parsing for standard Agent Skills directories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, BinaryIO

import yaml


MAX_SKILL_BYTES = 1024 * 1024
_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillValidationError(ValueError):
    """Raised when a standard skill manifest is invalid or unsafe."""


@dataclass(frozen=True)
class SkillManifest:
    """Parsed metadata and instructions from a standard Agent Skill."""

    name: str
    description: str
    root: Path
    body: str
    compatibility: str | None
    allowed_tools: str | None
    metadata: Mapping[str, Any]


def _validation_error(path: Path, message: str) -> SkillValidationError:
    return SkillValidationError(f"Invalid skill at {path}: {message}")


def _read_skill_file(root: Path) -> tuple[Path, str]:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise _validation_error(root, f"cannot resolve skill root: {exc}") from exc
    if not resolved_root.is_dir():
        raise _validation_error(root, "skill root must be a directory")

    skill_path = resolved_root / "SKILL.md"
    try:
        resolved_skill_path = skill_path.resolve(strict=True)
        if not resolved_skill_path.is_relative_to(resolved_root):
            raise _validation_error(skill_path, "SKILL.md resolves outside skill root")
        with resolved_skill_path.open("rb") as skill_file:
            content_bytes = _read_bounded(skill_file)
        if len(content_bytes) > MAX_SKILL_BYTES:
            raise _validation_error(
                skill_path,
                f"SKILL.md exceeds the {MAX_SKILL_BYTES}-byte size limit",
            )
        content = content_bytes.decode("utf-8", errors="strict")
    except SkillValidationError:
        raise
    except UnicodeDecodeError as exc:
        raise _validation_error(skill_path, f"SKILL.md is not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise _validation_error(skill_path, f"cannot read SKILL.md: {exc}") from exc
    return resolved_root, content


def _read_bounded(skill_file: BinaryIO) -> bytes:
    """Read only enough bytes to determine whether the size limit is exceeded."""

    return skill_file.read(MAX_SKILL_BYTES + 1)


def _parse_frontmatter(path: Path, content: str) -> tuple[dict[str, Any], str]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise _validation_error(path, "SKILL.md must start with YAML frontmatter")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as exc:
        raise _validation_error(path, "YAML frontmatter has no closing delimiter") from exc

    yaml_text = "\n".join(lines[1:closing_index])
    try:
        documents = list(yaml.safe_load_all(yaml_text))
    except yaml.YAMLError as exc:
        raise _validation_error(path, f"invalid YAML frontmatter: {exc}") from exc
    if len(documents) != 1:
        raise _validation_error(path, "frontmatter must contain exactly one YAML document")
    manifest = documents[0]
    if not isinstance(manifest, dict):
        raise _validation_error(path, "frontmatter must be a mapping")

    body_lines = lines[closing_index + 1 :]
    if body_lines and body_lines[0] == "---":
        raise _validation_error(path, "multiple YAML documents are not allowed")
    body = "\n".join(body_lines).strip()
    return manifest, body


def _required_string(manifest: dict[str, Any], field: str, path: Path) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        raise _validation_error(path, f"{field!r} is a required non-empty string")
    return value


def _optional_string(manifest: dict[str, Any], field: str, path: Path) -> str | None:
    value = manifest.get(field)
    if value is not None and not isinstance(value, str):
        raise _validation_error(path, f"{field!r} must be a string")
    return value


def parse_skill(path: Path) -> SkillManifest:
    """Parse and validate ``path/SKILL.md`` without following escaping links."""

    root, content = _read_skill_file(Path(path))
    manifest, body = _parse_frontmatter(root / "SKILL.md", content)

    name = _required_string(manifest, "name", path)
    if len(name) > 64 or _NAME_PATTERN.fullmatch(name) is None:
        raise _validation_error(
            path,
            "'name' must be 1-64 lowercase letters, digits, or single hyphens",
        )
    description = _required_string(manifest, "description", path)
    if len(description) > 1024:
        raise _validation_error(path, "'description' must not exceed 1024 characters")
    if name != root.name:
        raise _validation_error(
            path,
            f"'name' must match resolved skill directory name {root.name!r}",
        )

    compatibility = _optional_string(manifest, "compatibility", path)
    if compatibility is not None and len(compatibility) > 500:
        raise _validation_error(path, "'compatibility' must not exceed 500 characters")
    allowed_tools = _optional_string(manifest, "allowed-tools", path)
    metadata = manifest.get("metadata", {})
    if not isinstance(metadata, dict):
        raise _validation_error(path, "'metadata' must be a mapping")

    return SkillManifest(
        name=name,
        description=description,
        root=root,
        body=body,
        compatibility=compatibility,
        allowed_tools=allowed_tools,
        metadata=MappingProxyType(dict(metadata)),
    )
