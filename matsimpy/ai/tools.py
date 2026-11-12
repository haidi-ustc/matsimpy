"""AI tools built from Python functions.

A :class:`Tool` is derived from a function: its name, its signature and type
hints (the JSON Schema of the parameters) and its docstring (the descriptions).
There is no second definition to keep in sync.  :class:`ToolCatalog` collects
tools from modules (functions marked with :func:`matsimpy.utils.tooling.tool`),
from single functions, from skills and from MCP servers.  :class:`ToolExecutor`
validates the arguments of a call, converts them to Python objects, runs the
function and turns the result into JSON.

Structures do not travel through the model.  A tool that returns a structure
stores it in the executor and returns a reference such as ``"structure:1"``
with a summary; a parameter annotated with a structure type accepts that
reference (or a structure file in the workspace).
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import inspect
import json
import math
import os
import re
import types
import typing
from collections.abc import Callable, Iterable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..core import Crystal, Lattice, Molecule, Structure
from ..utils.tooling import tool_marker
from .workspace import Workspace

__all__ = [
    "DEFAULT_TOOL_MODULES",
    "Tool",
    "ToolCatalog",
    "ToolContext",
    "ToolError",
    "ToolExecutor",
    "ToolResult",
    "ToolSchemaError",
    "parse_docstring",
]

DEFAULT_TOOL_MODULES: tuple[str, ...] = (
    "matsimpy.builders",
    "matsimpy.builders.bulk",
    "matsimpy.transformation",
    "matsimpy.io",
    "matsimpy.symmetry",
    "matsimpy.analysis",
    "matsimpy.ai.builtin_tools",
)
"""Modules scanned for ``@tool`` functions by :meth:`ToolCatalog.default`."""

_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_REF = re.compile(r"^structure:([1-9][0-9]*)$")
# unannotated parameters with these names take a structure
_STRUCTURE_NAMES = {"structure", "crystal", "molecule"}
STRUCTURE_REF_DESCRIPTION = (
    "A structure: a reference such as 'structure:1' returned by an earlier tool, "
    "or the path of a structure file in the workspace."
)


class ToolError(Exception):
    """Raised by a tool to report a failure; the message is shown to the model."""


class ToolSchemaError(ValueError):
    """A function cannot be described as a tool (e.g. a required parameter of an unsupported type)."""


# --------------------------------------------------------------------------- docstrings

_SECTION = re.compile(r"^(Args|Arguments|Parameters|Params|Keyword Args|Other Parameters|Returns?|Yields?|Raises|"
                      r"Examples?|Notes?|See Also|References|Attributes|Warnings?|Warns|Methods)\s*:?\s*$")
_PARAM_SECTIONS = {"args", "arguments", "parameters", "params", "keyword args", "other parameters"}
_ENTRY = re.compile(r"^\**(\w+)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$")
_SPHINX_PARAM = re.compile(r"^:param\s+(?:[^:]*\s)?(\w+)\s*:\s*(.*)$")


def parse_docstring(doc: str | None) -> tuple[str, dict[str, str], str]:
    """Split a Google, NumPy or Sphinx docstring into (summary, parameter docs, returns doc).

    The summary is the text before the first section.  In a parameter section an
    entry is a line at the section's first indentation (``name: text``,
    ``name (type): text`` or NumPy's ``name : type``); deeper lines continue it.
    """
    lines = inspect.cleandoc(doc or "").splitlines()
    summary: list[str] = []
    params: dict[str, str] = {}
    returns: list[str] = []
    section: str | None = None
    entry_indent: int | None = None
    current: str | None = None
    numpy_entry = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        underline = i + 1 < len(lines) and len(lines[i + 1].strip()) >= 3 and set(lines[i + 1].strip()) == {"-"}
        header = _SECTION.match(stripped)
        if header and indent == 0 and (stripped.endswith(":") or underline):
            section, entry_indent, current = header.group(1).lower(), None, None
            numpy_entry = underline
            i += 2 if underline else 1
            continue
        sphinx = _SPHINX_PARAM.match(stripped)
        if sphinx:
            current, section = sphinx.group(1), "sphinx"
            params[current] = sphinx.group(2).strip()
        elif stripped.startswith((":return:", ":returns:")):
            section, current = "returns", None
            returns.append(stripped.split(":", 2)[-1].strip())
        elif section is None:
            summary.append(line)
        elif section in _PARAM_SECTIONS:
            if not stripped:
                pass
            elif entry_indent is None or indent <= entry_indent:
                entry_indent = indent
                match = _ENTRY.match(stripped)
                if match:
                    current = match.group(1)
                    # NumPy "name : type" has the type after the colon, the text below
                    params[current] = "" if numpy_entry else match.group(3).strip()
                else:
                    current = None
            elif current is not None:
                params[current] = f"{params[current]} {stripped}".strip()
        elif section == "sphinx" and current is not None and stripped and indent > 0:
            params[current] = f"{params[current]} {stripped}".strip()
        elif section in {"returns", "return", "yields", "yield"} and stripped:
            returns.append(stripped)
        i += 1
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(summary).strip())
    return text, params, " ".join(returns)


# --------------------------------------------------------------------------- schemas


def _is_structure_type(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, Structure)


def _union_args(annotation: Any) -> tuple | None:
    origin = typing.get_origin(annotation)
    if origin is typing.Union or (hasattr(types, "UnionType") and isinstance(annotation, types.UnionType)):
        return typing.get_args(annotation)
    return None


def _schema_for(annotation: Any) -> tuple[dict, str | None]:
    """JSON Schema of a type, and the conversion kind (structure, structures, lattice, path)."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}, None
    if typing.get_origin(annotation) is typing.Annotated:
        return _schema_for(typing.get_args(annotation)[0])
    if annotation is None or annotation is type(None):
        return {"type": "null"}, None
    if annotation is bool:
        return {"type": "boolean"}, None
    if annotation is int:
        return {"type": "integer"}, None
    if annotation is float:
        return {"type": "number"}, None
    if annotation is str:
        return {"type": "string"}, None
    if annotation in (Path, os.PathLike) or typing.get_origin(annotation) is os.PathLike:
        return {"type": "string"}, "path"
    if _is_structure_type(annotation):
        return {"type": "string", "description": STRUCTURE_REF_DESCRIPTION}, "structure"
    if annotation is Lattice:
        return {
            "type": "array",
            "description": "Lattice: three lattice vectors [[ax,ay,az],[bx,by,bz],[cx,cy,cz]] in Angstrom, "
            "or the parameters [a, b, c, alpha, beta, gamma] (Angstrom, degrees).",
        }, "lattice"
    if annotation is np.ndarray or getattr(annotation, "__name__", "") in {"ArrayLike", "NDArray"}:
        return {"type": "array"}, None
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return {"enum": [member.value for member in annotation]}, None

    members = _union_args(annotation)
    if members is not None:
        present = [member for member in members if member is not type(None)]
        if all(_is_structure_type(member) for member in present):
            return _schema_for(present[0])
        if len(present) == 1:
            schema, kind = _schema_for(present[0])
            if kind is not None or not schema:  # e.g. Lattice | None: converted, None means "not given"
                return schema, kind
            return {"anyOf": [schema, {"type": "null"}]}, None
        if any(_is_structure_type(member) for member in present) and set(present) - {str} == {
                member for member in present if _is_structure_type(member)}:
            # str | Crystal | Molecule (e.g. an adsorbate given by name or as a structure)
            return {"type": "string", "description": "A name, or " + STRUCTURE_REF_DESCRIPTION[2:]}, "structure_or_string"
        schemas = []
        for member in present:
            try:
                schema, kind = _schema_for(member)
            except ToolSchemaError:
                continue  # e.g. int | list[int] | AtomSelection: the model uses the JSON members
            if kind is not None:
                raise ToolSchemaError(f"cannot mix {kind} with other types in {annotation}")
            if not schema:
                return {}, None
            if schema not in schemas:
                schemas.append(schema)
        if not schemas:
            raise ToolSchemaError(f"unsupported type {annotation}")
        if len(present) < len(members):
            schemas.append({"type": "null"})
        return (schemas[0] if len(schemas) == 1 else {"anyOf": schemas}), None

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Literal:
        values = list(args)
        kinds = {type(value) for value in values}
        schema: dict = {"enum": values}
        if kinds <= {str}:
            schema["type"] = "string"
        elif kinds <= {int}:
            schema["type"] = "integer"
        return schema, None
    import collections.abc as abc

    sequence_origins = {list, tuple, set, frozenset, abc.Sequence, abc.Iterable, abc.Collection,
                        abc.MutableSequence, abc.Set}
    if annotation in (list, tuple, set, frozenset) or origin in sequence_origins:
        item_types = [arg for arg in args if arg is not Ellipsis]
        if not item_types:
            return {"type": "array"}, None
        if len(set(item_types)) == 1 or origin is not tuple:
            item, kind = _schema_for(item_types[0])
            schema = {"type": "array", "items": item} if item else {"type": "array"}
            if origin is tuple and Ellipsis not in args:
                schema["minItems"] = schema["maxItems"] = len(item_types)
            if kind == "structure":
                schema["items"] = {"type": "string"}
                schema["description"] = "Structures: references such as 'structure:1', or structure file paths."
                return schema, "structures"
            if kind is not None:
                raise ToolSchemaError(f"unsupported item type in {annotation}")
            return schema, None
        items = [_schema_for(arg)[0] for arg in item_types]
        return {"type": "array", "prefixItems": items, "minItems": len(items), "maxItems": len(items)}, None
    if annotation in (dict,) or origin in (dict, abc.Mapping, abc.MutableMapping):
        schema = {"type": "object"}
        if len(args) == 2:
            value, kind = _schema_for(args[1])
            if kind is not None:
                raise ToolSchemaError(f"unsupported value type in {annotation}")
            if value:
                schema["additionalProperties"] = value
        return schema, None
    raise ToolSchemaError(f"unsupported type {getattr(annotation, '__name__', annotation)!r}")


def _type_hints(function: Callable) -> dict[str, Any]:
    try:
        return typing.get_type_hints(function, include_extras=True)
    except Exception:
        hints = {}
        namespace = getattr(function, "__globals__", {})
        for name, annotation in getattr(function, "__annotations__", {}).items():
            if isinstance(annotation, str):
                try:
                    annotation = eval(annotation, dict(namespace))  # noqa: S307 - annotations of trusted code
                except Exception:
                    continue
            hints[name] = annotation
        return hints


def _json_default(value: Any) -> Any:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return inspect.Parameter.empty
    if isinstance(value, float) and not math.isfinite(value):
        return inspect.Parameter.empty
    return list(value) if isinstance(value, tuple) else value


def _context_annotation(annotation: Any) -> bool:
    """``ToolContext`` or ``ToolContext | None``."""
    members = _union_args(annotation) or (annotation,)
    return any(member is ToolContext or member == "ToolContext" for member in members)


# --------------------------------------------------------------------------- Tool


@dataclass(frozen=True)
class Tool:
    """An AI tool: name, description, JSON Schema of the arguments, and the function to call."""

    name: str
    description: str
    parameters: Mapping[str, Any]
    function: Callable[..., Any] = field(repr=False, compare=False)
    source: str = ""
    kinds: Mapping[str, str] = field(default_factory=dict, repr=False)
    """Parameters converted by the executor: ``structure``, ``structures``, ``lattice`` or ``path``."""
    context_param: str | None = None
    """Parameter that receives the :class:`ToolContext`, if the function takes one."""
    help: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not _NAME.match(self.name):
            raise ToolSchemaError(f"invalid tool name {self.name!r}: use letters, digits, '_' or '-' (max 64)")
        if self.parameters.get("type") != "object":
            raise ToolSchemaError(f"tool {self.name!r}: parameters must be an object schema")

    @classmethod
    def from_function(
        cls,
        function: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        paths: Iterable[str] = (),
        exclude: Iterable[str] = (),
        source: str | None = None,
    ) -> Tool:
        """Describe ``function`` as a tool.  Explicit arguments override its ``@tool`` marker."""
        marker = tool_marker(function)
        if marker is not None:
            name = name or marker.name
            description = description or marker.description
            paths = (*marker.paths, *paths)
            exclude = (*marker.exclude, *exclude)
        paths, exclude = set(paths), set(exclude)
        summary, param_docs, returns = parse_docstring(inspect.getdoc(function))
        tool_name = name or function.__name__
        signature = inspect.signature(function)
        hints = _type_hints(function)
        unknown = (paths | exclude) - set(signature.parameters)
        if unknown:
            raise ToolSchemaError(f"tool {tool_name!r}: no parameters named {sorted(unknown)}")

        properties: dict[str, dict] = {}
        required: list[str] = []
        kinds: dict[str, str] = {}
        context_param = None
        for pname, param in signature.parameters.items():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD) or pname in {"self", "cls"}:
                continue
            annotation = hints.get(pname, param.annotation)
            if _context_annotation(annotation):
                context_param = pname
                continue
            if pname in exclude:
                if param.default is param.empty:
                    raise ToolSchemaError(f"tool {tool_name!r}: cannot exclude required parameter {pname!r}")
                continue
            if param.kind is param.POSITIONAL_ONLY:
                raise ToolSchemaError(f"tool {tool_name!r}: positional-only parameter {pname!r}")
            try:
                if annotation is param.empty and pname in _STRUCTURE_NAMES:
                    schema, kind = _schema_for(Structure)
                elif annotation is param.empty and param.default not in (param.empty, None):
                    schema, kind = _schema_for(type(param.default))
                else:
                    schema, kind = _schema_for(annotation)
            except ToolSchemaError as exc:
                if param.default is param.empty:
                    raise ToolSchemaError(f"tool {tool_name!r}, parameter {pname!r}: {exc}") from None
                continue  # an optional parameter the model cannot fill keeps its default
            if pname in paths:
                schema, kind = {"type": "string", "description": "Path in the workspace."}, "path"
            schema = dict(schema)
            doc = param_docs.get(pname)
            if doc:
                schema["description"] = f"{doc} {schema['description']}" if kind == "structure" and schema.get(
                    "description") else doc
            if param.default is param.empty:
                required.append(pname)
            else:
                default = _json_default(param.default)
                if default is not param.empty and default is not None:
                    schema["default"] = default
            if kind is not None:
                kinds[pname] = kind
            properties[pname] = schema

        text = description or summary or f"Call {tool_name}."
        if returns and description is None:
            text = f"{text}\n\nReturns: {returns}"
        parameters = {"type": "object", "properties": properties, "required": required,
                      "additionalProperties": False}
        module = getattr(function, "__module__", "") or ""
        return cls(
            name=tool_name,
            description=text.strip(),
            parameters=parameters,
            function=function,
            source=source if source is not None else module,
            kinds=kinds,
            context_param=context_param,
            help=inspect.getdoc(function) or text,
        )

    def openai_schema(self) -> dict:
        """The tool in the OpenAI / DeepSeek ``tools`` format."""
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": deepcopy(dict(self.parameters))}}

    def mcp_schema(self) -> dict:
        """The tool in the MCP ``tools/list`` format."""
        return {"name": self.name, "description": self.description, "inputSchema": deepcopy(dict(self.parameters))}

    def summary(self) -> str:
        """First line of the description."""
        return self.description.splitlines()[0] if self.description else ""


# --------------------------------------------------------------------------- catalog


class ToolCatalog(Mapping[str, Tool]):
    """Tools by name.

    Tools come from modules (every ``@tool`` function in the module's public
    namespace), from single functions (:meth:`add`), and from skills and MCP
    servers (:meth:`extend`).  Schemas are built when a tool is added;
    :meth:`refresh` rebuilds the module tools, so an edited function is picked
    up without restarting.
    """

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        self._modules: list[str] = []
        self.skipped: dict[str, str] = {}
        """Marked functions that could not be described as tools, with the reason."""
        self.extend(tools)

    @classmethod
    def default(cls, modules: Iterable[str] = ()) -> ToolCatalog:
        """The library's tools (:data:`DEFAULT_TOOL_MODULES`) plus those of ``modules``."""
        catalog = cls()
        for module in (*DEFAULT_TOOL_MODULES, *modules):
            catalog.add_module(module)
        return catalog

    # Mapping
    def __getitem__(self, name: str) -> Tool:
        return self._tools[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

    @property
    def modules(self) -> tuple[str, ...]:
        return tuple(self._modules)

    def add(self, item: Tool | Callable[..., Any], *, replace: bool = False, **overrides: Any) -> Tool:
        """Add a :class:`Tool` or a function (described with :meth:`Tool.from_function`)."""
        tool = item if isinstance(item, Tool) else Tool.from_function(item, **overrides)
        existing = self._tools.get(tool.name)
        if existing is not None and not replace and existing.function is not tool.function:
            raise ValueError(f"duplicate tool name {tool.name!r} ({existing.source} and {tool.source})")
        self._tools[tool.name] = tool
        return tool

    def extend(self, tools: Iterable[Tool], *, replace: bool = False) -> None:
        for tool in tools:
            self.add(tool, replace=replace)

    def remove(self, name: str) -> None:
        del self._tools[name]

    def remove_source(self, source: str) -> list[str]:
        """Remove every tool from ``source`` (e.g. ``"skill:name"`` or ``"mcp:server"``)."""
        names = [name for name, tool in self._tools.items() if tool.source == source]
        for name in names:
            del self._tools[name]
        return names

    def add_module(self, module: str | types.ModuleType, *, reload: bool = False) -> list[Tool]:
        """Add every ``@tool`` function in the module's public namespace."""
        if isinstance(module, str):
            module = importlib.import_module(module)
        if reload:
            module = importlib.reload(module)
        if module.__name__ not in self._modules:
            self._modules.append(module.__name__)
        names = getattr(module, "__all__", None) or [n for n in dir(module) if not n.startswith("_")]
        added = []
        for attribute in names:
            function = getattr(module, attribute, None)
            if tool_marker(function) is None:
                continue
            key = f"{getattr(function, '__module__', '')}.{getattr(function, '__qualname__', attribute)}"
            try:
                added.append(self.add(Tool.from_function(function, source=module.__name__)))
            except (ToolSchemaError, ValueError) as exc:
                self.skipped[key] = str(exc)
        return added

    def refresh(self, *, reload: bool = False) -> None:
        """Rebuild the tools of every added module from the current functions.

        With ``reload``, modules outside the ``matsimpy`` package (your own tool
        modules) are re-imported first, so edits to their files take effect.
        MatSimPy's own modules are not reloaded: that would replace classes other
        modules still use; restart to pick up changes to MatSimPy itself.
        """
        for name in self._modules:
            self.remove_source(name)
        for name in list(self._modules):
            library = name == "matsimpy" or name.startswith("matsimpy.")
            self.add_module(name, reload=reload and not library)

    def search(self, query: str, limit: int = 10) -> list[Tool]:
        """Tools whose name, description or source match the words of ``query``, best first."""
        words = [word for word in re.split(r"[\s_,;/-]+", query.casefold()) if word]
        scored = []
        for tool in self._tools.values():
            name = tool.name.casefold()
            text = f"{tool.description} {tool.source}".casefold()
            score = sum(3 * (word in name) + (word in text) for word in words)
            if score:
                scored.append((-score, tool.name, tool))
        return [tool for *_, tool in sorted(scored)[:limit]]


# --------------------------------------------------------------------------- execution


@dataclass(frozen=True)
class ToolResult:
    """Outcome of one tool call."""

    name: str
    arguments: Mapping[str, Any]
    ok: bool
    value: Any = None
    """JSON-compatible result (``None`` on failure)."""
    error: str | None = None

    def content(self) -> dict:
        """The result as sent to the model."""
        if not self.ok:
            return {"error": self.error}
        return self.value if isinstance(self.value, dict) else {"result": self.value}

    def as_dict(self) -> dict:
        return {"name": self.name, "arguments": dict(self.arguments), "ok": self.ok,
                "result": self.content()}


@dataclass
class ToolContext:
    """Passed to a tool function that has a parameter annotated ``ToolContext``.

    Not part of the tool's schema.  ``state`` is per-executor storage for tools
    (e.g. a session database); keys should be the tool or skill name.
    """

    workspace: Path
    state: dict[str, Any]
    executor: ToolExecutor


class ToolExecutor:
    """Run tool calls: validate, convert arguments, call, convert the result to JSON.

    Holds the structures returned during a session (``structure:N``).  Paths are
    resolved in ``workspace``; paths outside it are rejected unless
    ``confine_paths`` is false.
    """

    def __init__(
        self,
        catalog: ToolCatalog,
        workspace: str | Path | Workspace | None = None,
        *,
        confine_paths: bool = True,
        max_result_chars: int = 20_000,
    ) -> None:
        self.catalog = catalog
        self.workspace = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
        self.confine_paths = confine_paths
        self.max_result_chars = max_result_chars
        self.objects: dict[str, Structure] = {}
        self.state: dict[str, Any] = {}

    # objects -----------------------------------------------------------------
    def store(self, structure: Structure) -> str:
        """Keep a structure and return its reference."""
        ref = f"structure:{len(self.objects) + 1}"
        while ref in self.objects:
            ref = f"structure:{int(ref.split(':')[1]) + 1}"
        self.objects[ref] = structure
        return ref

    def resolve(self, value: Any) -> Structure:
        """A structure from a reference, a ``{"structure_ref": ...}`` dict or a workspace file."""
        if isinstance(value, Structure):
            return value
        if isinstance(value, Mapping) and "structure_ref" in value:
            value = value["structure_ref"]
        if not isinstance(value, str):
            raise ToolError(f"expected a structure reference such as 'structure:1', got {value!r}")
        if _REF.match(value):
            try:
                return self.objects[value]
            except KeyError:
                known = ", ".join(self.objects) or "none yet"
                raise ToolError(f"unknown structure reference {value!r} (known: {known})") from None
        path = self.path(value)
        if not path.is_file():
            raise ToolError(f"{value!r} is neither a structure reference nor a file in the workspace")
        from .. import io

        return io.read(str(path))

    def path(self, value: str) -> Path:
        """``value`` resolved in the workspace."""
        root = self.workspace.path
        path = Path(value).expanduser()
        path = (path if path.is_absolute() else root / path).resolve()
        if self.confine_paths and not path.is_relative_to(root):
            raise ToolError(f"path {value!r} is outside the workspace {root}")
        return path

    def summary(self, structure: Structure, ref: str | None = None) -> dict:
        """What the model sees of a structure."""
        data: dict[str, Any] = {}
        if ref is not None:
            data["structure_ref"] = ref
        data.update(type=type(structure).__name__, formula=str(structure.formula), num_atoms=len(structure))
        lattice = getattr(structure, "lattice", None)
        if lattice is not None:
            data["lattice"] = {key: round(float(getattr(lattice, key)), 5)
                               for key in ("a", "b", "c", "alpha", "beta", "gamma")}
            data["volume"] = round(float(lattice.volume), 5)
            data["pbc"] = [bool(flag) for flag in structure.pbc]
        return data

    # calls -------------------------------------------------------------------
    def call(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolResult:
        """Run one call.  Never raises for tool failures: they are returned as ``ok=False``."""
        arguments = dict(arguments or {})
        tool = self.catalog.get(name)
        if tool is None:
            close = [t.name for t in self.catalog.search(name.replace("_", " "), limit=5)]
            hint = f"; similar tools: {', '.join(close)}" if close else ""
            return ToolResult(name, arguments, False, error=f"unknown tool {name!r}{hint}")
        errors = validate(tool.parameters, arguments)
        if errors:
            return ToolResult(name, arguments, False, error="invalid arguments: " + "; ".join(errors))
        try:
            kwargs = self._convert(tool, arguments)
            with self.workspace.activate():
                value = tool.function(**kwargs)
            if value is None:
                # e.g. write_structure: report the files it was given
                written = {p: arguments[p] for p, kind in tool.kinds.items() if kind == "path" and p in arguments}
                return ToolResult(name, arguments, True, value={"status": "ok", **written})
            return ToolResult(name, arguments, True, value=self._jsonable_result(value))
        except ToolError as exc:
            return ToolResult(name, arguments, False, error=str(exc))
        except Exception as exc:  # the model is told what went wrong and can recover
            return ToolResult(name, arguments, False, error=f"{type(exc).__name__}: {exc}")

    def _convert(self, tool: Tool, arguments: dict) -> dict:
        kwargs = dict(arguments)
        for pname, kind in tool.kinds.items():
            if pname not in kwargs or kwargs[pname] is None:
                continue
            value = kwargs[pname]
            if kind == "structure":
                kwargs[pname] = self.resolve(value)
            elif kind == "structure_or_string":
                try:
                    kwargs[pname] = self.resolve(value)
                except ToolError:
                    pass  # a plain string argument
            elif kind == "structures":
                kwargs[pname] = [self.resolve(item) for item in value]
            elif kind == "path":
                kwargs[pname] = str(self.path(value))
            elif kind == "lattice":
                kwargs[pname] = _lattice(value)
        if tool.context_param:
            kwargs[tool.context_param] = ToolContext(self.workspace.path, self.state, self)
        return kwargs

    def _jsonable_result(self, value: Any) -> Any:
        result = self.jsonable(value)
        text = json.dumps(result)
        if len(text) > self.max_result_chars:
            return {"truncated": True, "chars": len(text), "preview": text[: self.max_result_chars]}
        return result

    def jsonable(self, value: Any) -> Any:
        """``value`` as JSON-compatible data; structures are stored and summarized."""
        if isinstance(value, Structure):
            return self.summary(value, self.store(value))
        if value is None or isinstance(value, (bool, int, str)):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else str(value)
        if isinstance(value, np.generic):
            return self.jsonable(value.item())
        if isinstance(value, np.ndarray):
            return self.jsonable(value.tolist())
        if isinstance(value, Path):
            try:
                return str(value.resolve().relative_to(self.workspace.path))
            except ValueError:
                return str(value)
        if isinstance(value, enum.Enum):
            return self.jsonable(value.value)
        if isinstance(value, Mapping):
            return {str(key): self.jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.jsonable(item) for item in value]
        if isinstance(value, (set, frozenset)):
            return sorted((self.jsonable(item) for item in value), key=str)
        if hasattr(value, "as_dict") and callable(value.as_dict):
            return self.jsonable(value.as_dict())
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return self.jsonable({f.name: getattr(value, f.name) for f in dataclasses.fields(value)})
        return repr(value)[:2000]

    # persistence -------------------------------------------------------------
    def export_objects(self) -> dict[str, dict]:
        """Stored structures as JSON-compatible dicts (for session files)."""
        return {ref: structure.as_dict() for ref, structure in self.objects.items()}

    def import_objects(self, data: Mapping[str, Mapping]) -> None:
        """Restore structures saved by :meth:`export_objects`."""
        for ref, item in data.items():
            cls = Molecule if item.get("@class") == "Molecule" else Crystal
            self.objects[ref] = cls.from_dict(dict(item))


def _lattice(value: Any) -> Lattice:
    array = np.asarray(value, dtype=float)
    if array.shape == (3, 3):
        return Lattice(array)
    if array.shape == (6,):
        return Lattice.from_parameters(*array)
    raise ToolError("a lattice is three vectors [[..],[..],[..]] or six parameters [a, b, c, alpha, beta, gamma]")


# --------------------------------------------------------------------------- validation

_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def validate(schema: Mapping[str, Any], value: Any, where: str = "") -> list[str]:
    """Errors of ``value`` against the subset of JSON Schema that tools use (empty if valid)."""
    errors: list[str] = []
    label = where or "arguments"
    if "anyOf" in schema:
        if all(validate(option, value, where) for option in schema["anyOf"]):
            kinds = [option.get("type", "any") for option in schema["anyOf"]]
            errors.append(f"{label}: expected one of {kinds}, got {_type_name(value)}")
        return errors
    expected = schema.get("type")
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        if not any(_TYPES.get(option, lambda v: True)(value) for option in options):
            return [f"{label}: expected {' or '.join(options)}, got {_type_name(value)}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{label}: must be one of {schema['enum']}, got {value!r}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{label}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{label}: allows at most {schema['maxItems']} items")
        if "prefixItems" in schema:
            for index, (item_schema, item) in enumerate(zip(schema["prefixItems"], value)):
                errors.extend(validate(item_schema, item, f"{label}[{index}]"))
        elif isinstance(schema.get("items"), Mapping):
            for index, item in enumerate(value):
                errors.extend(validate(schema["items"], item, f"{label}[{index}]"))
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"missing required {_join(where, key)!r}")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                errors.extend(validate(properties[key], item, _join(where, key)))
            elif extra is False:
                allowed = ", ".join(properties) or "none"
                errors.append(f"unknown {_join(where, key)!r} (allowed: {allowed})")
            elif isinstance(extra, Mapping):
                errors.extend(validate(extra, item, _join(where, key)))
    return errors


def _join(where: str, key: str) -> str:
    return f"{where}.{key}" if where else key


def _type_name(value: Any) -> str:
    for name, check in _TYPES.items():
        if check(value):
            return name
    return type(value).__name__
