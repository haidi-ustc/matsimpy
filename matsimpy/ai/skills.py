"""Agent Skills: instructions loaded only when they are needed.

A skill is a directory with a ``SKILL.md`` file: YAML frontmatter (``name``,
``description``, optional ``license``, ``compatibility``, ``allowed-tools`` and
``metadata``) followed by Markdown instructions.  It may contain other files
(references, templates, data) and a ``tools.py`` whose ``@tool`` functions
become tools while the skill is active.

Loading is progressive:

1. :meth:`SkillLibrary.discover` reads only the frontmatter of each skill, so
   the agent can list many skills by name and description.
2. :meth:`SkillLibrary.activate` reads the instructions and loads ``tools.py``.
3. :meth:`SkillLibrary.read_resource` reads one more file, on request.

Skills come from three places, later ones shadowing earlier ones with the same
name: the skills packaged with MatSimPy, the user's skills
(``~/.matsimpy/ai/skills``) and the workspace's skills
(``<workspace>/.matsimpy/skills``).  :meth:`~SkillLibrary.install`,
:meth:`~SkillLibrary.remove` and :func:`validate` manage them.  A draft (for
example one the agent proposes) is kept apart and is not discoverable until
it is approved.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from .tools import Tool, ToolCatalog

__all__ = [
    "PACKAGED_SKILLS",
    "USER_SKILLS",
    "Skill",
    "SkillError",
    "SkillLibrary",
    "SkillSummary",
    "validate",
]

PACKAGED_SKILLS = Path(__file__).resolve().parent / "builtin_skills"
USER_SKILLS = Path.home() / ".matsimpy" / "ai" / "skills"
SKILL_FILE = "SKILL.md"
TOOLS_FILE = "tools.py"
DRAFTS = ".drafts"
MAX_FILE_BYTES = 1024 * 1024
_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_KNOWN_FIELDS = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}


class SkillError(ValueError):
    """A skill is invalid, missing, or cannot be installed or removed."""


@dataclass(frozen=True)
class SkillSummary:
    """What is known about a skill before it is activated."""

    name: str
    description: str
    source: str  # packaged | user | workspace | draft
    path: Path


@dataclass(frozen=True)
class Skill:
    """An activated skill: its instructions, resource files and tools."""

    name: str
    description: str
    source: str
    path: Path
    instructions: str
    resources: tuple[str, ...]
    """Files of the skill other than SKILL.md and tools.py, relative to its directory."""
    tools: tuple[Tool, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


# --------------------------------------------------------------------------- parsing


def _read_text(path: Path) -> str:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise SkillError(f"{path} is larger than {MAX_FILE_BYTES} bytes")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SkillError(f"{path} is not UTF-8 text") from exc


def _frontmatter_text(path: Path, *, body: bool) -> tuple[str, str]:
    """YAML text of the frontmatter and, if ``body``, the instructions."""
    with path.open(encoding="utf-8") as handle:
        if handle.readline().rstrip("\r\n") != "---":
            raise SkillError(f"{path}: must start with '---' and YAML frontmatter")
        lines = []
        size = 0
        for line in handle:
            if line.rstrip("\r\n") == "---":
                break
            size += len(line)
            if size > 64 * 1024:
                raise SkillError(f"{path}: frontmatter is too long")
            lines.append(line)
        else:
            raise SkillError(f"{path}: frontmatter has no closing '---'")
        rest = handle.read(MAX_FILE_BYTES + 1) if body else ""
    if len(rest) > MAX_FILE_BYTES:
        raise SkillError(f"{path}: instructions are larger than {MAX_FILE_BYTES} bytes")
    return "".join(lines), rest.strip()


def _metadata(directory: Path, *, body: bool = False) -> tuple[dict[str, Any], str]:
    """Checked frontmatter of the skill in ``directory`` and, if ``body``, its instructions."""
    skill_file = directory / SKILL_FILE
    if not skill_file.is_file():
        raise SkillError(f"{directory}: no {SKILL_FILE}")
    try:
        text, instructions = _frontmatter_text(skill_file, body=body)
    except UnicodeDecodeError:
        raise SkillError(f"{skill_file} is not UTF-8 text") from None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SkillError(f"{skill_file}: invalid YAML frontmatter: {exc}") from None
    if not isinstance(data, dict):
        raise SkillError(f"{skill_file}: frontmatter must be a mapping")
    name = data.get("name")
    if not isinstance(name, str) or not _NAME.match(name) or len(name) > 64:
        raise SkillError(f"{skill_file}: 'name' must be lowercase letters, digits and single hyphens "
                         f"(at most 64 characters), got {name!r}")
    if name != directory.name:
        raise SkillError(f"{skill_file}: 'name' {name!r} must equal the directory name {directory.name!r}")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise SkillError(f"{skill_file}: 'description' must be non-empty text of at most 1024 characters")
    for key in ("license", "compatibility", "allowed-tools"):
        if key in data and not isinstance(data[key], str):
            raise SkillError(f"{skill_file}: {key!r} must be a string")
    if len(data.get("compatibility") or "") > 500:
        raise SkillError(f"{skill_file}: 'compatibility' must be at most 500 characters")
    if not isinstance(data.get("metadata", {}), dict):
        raise SkillError(f"{skill_file}: 'metadata' must be a mapping")
    return data, instructions


def validate(path: str | Path) -> list[str]:
    """Problems that keep the skill directory ``path`` from being installed (empty if none).

    Checks the frontmatter, that every file is inside the directory (no links
    pointing out), and that ``tools.py`` is valid Python with at least one
    ``@tool`` function.  ``tools.py`` is parsed, not run.
    """
    directory = Path(path)
    problems = []
    try:
        _metadata(directory, body=True)
    except (SkillError, OSError) as exc:
        problems.append(str(exc))
    root = directory.resolve()
    for item in directory.rglob("*"):
        if item.is_symlink() and not item.resolve().is_relative_to(root):
            problems.append(f"{item.relative_to(directory)} links outside the skill")
    tools_file = directory / TOOLS_FILE
    if tools_file.is_file():
        try:
            tree = ast.parse(tools_file.read_text(encoding="utf-8"), filename=str(tools_file))
        except (SyntaxError, UnicodeDecodeError) as exc:
            problems.append(f"{TOOLS_FILE}: {exc}")
        else:
            marked = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                      and any("tool" in ast.unparse(d) for d in node.decorator_list)]
            if not marked:
                problems.append(f"{TOOLS_FILE} has no @tool functions")
    return problems


def _load_tools(name: str, path: Path) -> tuple[Tool, ...]:
    """The ``@tool`` functions of ``path/tools.py``, as tools from ``skill:<name>``."""
    tools_file = path / TOOLS_FILE
    if not tools_file.is_file():
        return ()
    module_name = f"matsimpy_skill_{name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, tools_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise SkillError(f"skill {name!r}: {TOOLS_FILE} failed to load: {type(exc).__name__}: {exc}") from exc
    catalog = ToolCatalog()
    catalog.add_module(module)
    if catalog.skipped:
        raise SkillError(f"skill {name!r}: {TOOLS_FILE}: {'; '.join(catalog.skipped.values())}")
    return tuple(Tool.from_function(tool.function, source=f"skill:{name}") for tool in catalog.values())


# --------------------------------------------------------------------------- library


class SkillLibrary:
    """Discover, activate, install and remove skills."""

    def __init__(
        self,
        workspace: str | Path | None = None,
        *,
        user: str | Path | None = USER_SKILLS,
        packaged: str | Path | None = PACKAGED_SKILLS,
    ) -> None:
        self.roots: dict[str, Path] = {}
        for source, root in (("packaged", packaged), ("user", user),
                             ("workspace", Path(workspace) / ".matsimpy" / "skills" if workspace else None)):
            if root is not None:
                self.roots[source] = Path(root).expanduser()
        self.problems: dict[str, str] = {}
        """Skill directories that were skipped by :meth:`discover`, with the reason."""

    @property
    def install_root(self) -> Path:
        """Where :meth:`install` puts skills: the user root (or the workspace root without one)."""
        root = self.roots.get("user") or self.roots.get("workspace")
        if root is None:
            raise SkillError("no user or workspace skill directory configured")
        return root

    @property
    def drafts_root(self) -> Path:
        return self.install_root / DRAFTS

    # discovery ---------------------------------------------------------------
    def discover(self) -> list[SkillSummary]:
        """Every available skill, by name.  Reads only the frontmatter."""
        found: dict[str, SkillSummary] = {}
        self.problems = {}
        for source, root in self.roots.items():
            for directory in self._skill_dirs(root):
                try:
                    data, _ = _metadata(directory)
                except (SkillError, OSError) as exc:
                    self.problems[str(directory)] = str(exc)
                    continue
                found[data["name"]] = SkillSummary(data["name"], data["description"].strip(), source, directory)
        return sorted(found.values(), key=lambda item: item.name)

    @staticmethod
    def _skill_dirs(root: Path) -> list[Path]:
        if not root.is_dir():
            return []
        return sorted(d for d in root.iterdir() if d.is_dir() and not d.name.startswith((".", "_")))

    def get(self, name: str) -> SkillSummary:
        for summary in self.discover():
            if summary.name == name:
                return summary
        raise SkillError(f"unknown skill {name!r}")

    def search(self, query: str) -> list[SkillSummary]:
        words = query.casefold().split()
        return [s for s in self.discover() if all(w in f"{s.name} {s.description}".casefold() for w in words)]

    def activate(self, name: str) -> Skill:
        """Read the skill's instructions and load its tools."""
        summary = self.get(name)
        return self._skill(summary)

    def _skill(self, summary: SkillSummary) -> Skill:
        data, instructions = _metadata(summary.path, body=True)
        root = summary.path.resolve()
        resources = tuple(sorted(
            str(item.relative_to(summary.path)) for item in summary.path.rglob("*")
            if item.is_file() and item.name not in {SKILL_FILE, TOOLS_FILE}
            and "__pycache__" not in item.parts and item.resolve().is_relative_to(root)
        ))
        return Skill(
            name=summary.name,
            description=summary.description,
            source=summary.source,
            path=summary.path,
            instructions=instructions,
            resources=resources,
            tools=_load_tools(summary.name, summary.path),
            allowed_tools=tuple((data.get("allowed-tools") or "").split()),
            metadata=MappingProxyType(dict(data.get("metadata") or {})),
        )

    def read_resource(self, name: str, relative_path: str) -> str:
        """The text of one file of the skill (inside its directory, UTF-8, at most 1 MiB)."""
        root = self.get(name).path.resolve()
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root):
            raise SkillError(f"{relative_path!r} is outside skill {name!r}")
        if not path.is_file():
            raise SkillError(f"skill {name!r} has no file {relative_path!r}")
        return _read_text(path)

    # management --------------------------------------------------------------
    def install(self, source: str | Path, *, draft: bool = False, replace: bool = False) -> SkillSummary:
        """Copy a skill directory (or a .zip of one) into the user skills, or into the drafts.

        The skill is validated first.  An installed skill with the same name is
        only replaced with ``replace=True``.
        """
        source = Path(source).expanduser()
        with tempfile.TemporaryDirectory() as scratch:
            if source.is_file() and source.suffix == ".zip":
                source = _unzip(source, Path(scratch))
            if not source.is_dir():
                raise SkillError(f"{source} is not a skill directory or .zip file")
            problems = validate(source)
            if problems:
                raise SkillError(f"invalid skill {source}: " + "; ".join(problems))
            data, _ = _metadata(source)
            target = (self.drafts_root if draft else self.install_root) / data["name"]
            if target.exists():
                if not replace:
                    raise SkillError(f"skill {data['name']!r} is already installed at {target} (use replace)")
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return SkillSummary(data["name"], data["description"].strip(), "draft" if draft else "user", target)

    def remove(self, name: str) -> Path:
        """Delete an installed user or workspace skill.  Packaged skills cannot be removed."""
        for source in ("workspace", "user"):
            root = self.roots.get(source)
            if root is not None and (root / name / SKILL_FILE).is_file():
                shutil.rmtree(root / name)
                return root / name
        raise SkillError(f"no installed user or workspace skill {name!r}")

    def create_draft(self, name: str, description: str, instructions: str) -> SkillSummary:
        """Write a new draft skill (SKILL.md only).  It must be approved before it can be used."""
        if not _NAME.match(name or ""):
            raise SkillError(f"invalid skill name {name!r}: use lowercase letters, digits and hyphens")
        directory = self.drafts_root / name
        if directory.exists() or any(s.name == name for s in self.discover()):
            raise SkillError(f"a skill or draft named {name!r} already exists")
        frontmatter = yaml.safe_dump({"name": name, "description": description}, sort_keys=False,
                                     allow_unicode=True)
        directory.mkdir(parents=True)
        (directory / SKILL_FILE).write_text(f"---\n{frontmatter}---\n\n{instructions.strip()}\n", encoding="utf-8")
        problems = validate(directory)
        if problems:
            shutil.rmtree(directory)
            raise SkillError("; ".join(problems))
        return SkillSummary(name, description.strip(), "draft", directory)

    def drafts(self) -> list[SkillSummary]:
        summaries = []
        for directory in self._skill_dirs(self.drafts_root):
            try:
                data, _ = _metadata(directory)
            except (SkillError, OSError):
                continue
            summaries.append(SkillSummary(data["name"], data["description"].strip(), "draft", directory))
        return summaries

    def draft(self, name: str) -> Skill:
        """A draft's content, for review."""
        for summary in self.drafts():
            if summary.name == name:
                data, instructions = _metadata(summary.path, body=True)
                return Skill(name, summary.description, "draft", summary.path, instructions, ())
        raise SkillError(f"no draft skill {name!r}")

    def approve(self, name: str) -> SkillSummary:
        """Move a draft into the user skills, which makes it discoverable."""
        draft = self.drafts_root / name
        if not (draft / SKILL_FILE).is_file():
            raise SkillError(f"no draft skill {name!r}")
        summary = self.install(draft)
        shutil.rmtree(draft)
        return summary

    def reject(self, name: str) -> None:
        """Delete a draft."""
        draft = self.drafts_root / name
        if not draft.is_dir():
            raise SkillError(f"no draft skill {name!r}")
        shutil.rmtree(draft)


def _unzip(archive: Path, scratch: Path) -> Path:
    """Extract ``archive`` safely and return the skill directory in it."""
    with zipfile.ZipFile(archive) as handle:
        for member in handle.namelist():
            target = (scratch / member).resolve()
            if not target.is_relative_to(scratch.resolve()):
                raise SkillError(f"{archive}: entry {member!r} points outside the archive")
        handle.extractall(scratch)
    if (scratch / SKILL_FILE).is_file():
        raise SkillError(f"{archive}: SKILL.md must be inside a directory named after the skill")
    candidates = [d for d in scratch.iterdir() if (d / SKILL_FILE).is_file()]
    if len(candidates) != 1:
        raise SkillError(f"{archive}: expected one skill directory, found {len(candidates)}")
    return candidates[0]
