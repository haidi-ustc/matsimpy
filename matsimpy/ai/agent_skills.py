"""Safe parsing for standard Agent Skills directories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
from types import MappingProxyType
from typing import Any, BinaryIO, Iterable

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


@dataclass(frozen=True)
class SkillSummary:
    """Metadata disclosed while a skill remains inactive."""

    name: str
    description: str
    source: str
    compatibility: str | None
    allowed_tools: tuple[str, ...]


@dataclass(frozen=True)
class SkillDiagnostic:
    """A non-fatal issue found while indexing skills."""

    code: str
    message: str
    skill_name: str | None = None


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


class SkillLibrary:
    """Discover skill metadata and load instructions only on activation."""

    _SOURCES = ("packaged", "user", "workspace")

    def __init__(
        self,
        *,
        packaged: Path | None = None,
        user: Path | None = None,
        workspace: Path | None = None,
        available_tools: Mapping[str, Any] | Iterable[str] | None = None,
    ) -> None:
        self._roots = {
            "packaged": Path(packaged) if packaged is not None else None,
            "user": Path(user) if user is not None else None,
            "workspace": Path(workspace) if workspace is not None else None,
        }
        if available_tools is None:
            self.available_tools: Mapping[str, Any] = MappingProxyType({})
            self._validate_tools = False
        elif isinstance(available_tools, Mapping):
            self.available_tools = MappingProxyType(dict(available_tools))
            self._validate_tools = True
        else:
            self.available_tools = MappingProxyType(
                {name: None for name in available_tools}
            )
            self._validate_tools = True
        self.diagnostics: list[SkillDiagnostic] = []
        self.loaded_resources: list[tuple[str, str]] = []
        self.activated: dict[str, SkillManifest] = {}
        self._summaries: dict[str, SkillSummary] = {}
        self._skill_paths: dict[str, Path] = {}
        self._discovered = False

    def discover(self) -> list[SkillSummary]:
        """Index skills by metadata, applying source precedence."""

        self.diagnostics.clear()
        self._summaries.clear()
        self._skill_paths.clear()
        for source in self._SOURCES:
            root = self._roots[source]
            if root is None or not root.exists():
                continue
            level: dict[str, tuple[SkillSummary, Path]] = {}
            for skill_path in sorted(root.iterdir(), key=lambda item: item.name):
                if not skill_path.is_dir():
                    continue
                manifest = parse_skill(skill_path)
                if manifest.name in level:
                    raise SkillValidationError(
                        f"duplicate skill {manifest.name!r} in {source} source"
                    )
                allowed_tools = self._restrict_tools(manifest, source)
                summary = SkillSummary(
                    name=manifest.name,
                    description=manifest.description,
                    source=source,
                    compatibility=manifest.compatibility,
                    allowed_tools=allowed_tools,
                )
                level[manifest.name] = (summary, manifest.root)

            for name, (summary, path) in level.items():
                previous = self._summaries.get(name)
                if previous is not None:
                    self.diagnostics.append(
                        SkillDiagnostic(
                            code="skill-shadowed",
                            skill_name=name,
                            message=(
                                f"{source} skill {name!r} shadows "
                                f"{previous.source} skill"
                            ),
                        )
                    )
                self._summaries[name] = summary
                self._skill_paths[name] = path
        self._discovered = True
        return sorted(self._summaries.values(), key=lambda item: item.name)

    def _restrict_tools(
        self, manifest: SkillManifest, source: str
    ) -> tuple[str, ...]:
        if not manifest.allowed_tools:
            return ()
        try:
            requested = tuple(shlex.split(manifest.allowed_tools))
        except ValueError as exc:
            raise _validation_error(
                manifest.root / "SKILL.md", f"invalid 'allowed-tools': {exc}"
            ) from exc
        if not self._validate_tools:
            return requested
        allowed = tuple(name for name in requested if name in self.available_tools)
        for name in requested:
            if name not in self.available_tools:
                self.diagnostics.append(
                    SkillDiagnostic(
                        code="unknown-allowed-tool",
                        skill_name=manifest.name,
                        message=(
                            f"{source} skill {manifest.name!r} requests unknown "
                            f"tool {name!r}"
                        ),
                    )
                )
        return allowed

    def search(self, query: str) -> list[SkillSummary]:
        """Search disclosed skill names and descriptions."""

        self._ensure_discovered()
        terms = query.casefold().split()
        return [
            summary
            for summary in sorted(self._summaries.values(), key=lambda item: item.name)
            if all(
                term in f"{summary.name} {summary.description}".casefold()
                for term in terms
            )
        ]

    def activate(self, name: str) -> SkillManifest:
        """Explicitly load the full instructions for a discovered skill."""

        self._ensure_discovered()
        try:
            skill_path = self._skill_paths[name]
        except KeyError as exc:
            raise KeyError(f"unknown skill {name!r}") from exc
        manifest = parse_skill(skill_path)
        self.activated[name] = manifest
        return manifest

    def read_resource(self, name: str, relative_path: str) -> str:
        """Explicitly read a UTF-8 resource contained by a discovered skill."""

        self._ensure_discovered()
        try:
            root = self._skill_paths[name]
        except KeyError as exc:
            raise KeyError(f"unknown skill {name!r}") from exc
        requested = Path(relative_path)
        if requested.is_absolute():
            raise ValueError("resource path resolves outside skill root")
        candidate = (root / requested).resolve(strict=False)
        if not candidate.is_relative_to(root):
            raise ValueError("resource path resolves outside skill root")
        try:
            resource = candidate.resolve(strict=True)
        except OSError as exc:
            raise ValueError(f"cannot resolve skill resource: {exc}") from exc
        if not resource.is_relative_to(root) or not resource.is_file():
            raise ValueError("resource path resolves outside skill root")
        try:
            with resource.open("rb") as resource_file:
                content = _read_bounded(resource_file)
            if len(content) > MAX_SKILL_BYTES:
                raise ValueError(
                    f"resource exceeds the {MAX_SKILL_BYTES}-byte size limit"
                )
            text = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(f"skill resource is not valid UTF-8: {exc}") from exc
        except OSError as exc:
            raise ValueError(f"cannot read skill resource: {exc}") from exc
        self.loaded_resources.append((name, relative_path))
        return text

    def _ensure_discovered(self) -> None:
        if not self._discovered:
            self.discover()
