"""Tools derived from Python functions: schemas, catalog, and execution."""

from __future__ import annotations

import enum
import importlib
import inspect
import json
import pkgutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pytest

import matsimpy
from matsimpy.ai.tools import (
    Tool,
    ToolCatalog,
    ToolContext,
    ToolError,
    ToolExecutor,
    ToolSchemaError,
    parse_docstring,
    validate,
)
from matsimpy.core import Crystal, Lattice, Molecule, Structure
from matsimpy.utils.tooling import tool, tool_marker


# --------------------------------------------------------------------------- docstrings


def test_parse_google_docstring():
    summary, params, returns = parse_docstring("""Build a slab.

    Second paragraph.

    Args:
        bulk: The bulk crystal,
            continued here.
        layers (int): Number of layers.
        **kwargs: Ignored.

    Returns:
        Crystal: the slab.

    Examples:
        >>> build(x)
    """)
    assert summary == "Build a slab.\n\nSecond paragraph."
    assert params == {"bulk": "The bulk crystal, continued here.", "layers": "Number of layers.",
                      "kwargs": "Ignored."}
    assert returns == "Crystal: the slab."


def test_parse_numpy_and_sphinx_docstrings():
    _, params, returns = parse_docstring("""Sum.

    Parameters
    ----------
    x : float
        The x value.
    y : int
        The y
        value.

    Returns
    -------
    float
    """)
    assert params == {"x": "The x value.", "y": "The y value."}
    assert returns == "float"
    _, params, returns = parse_docstring(":param a: alpha\n:param int b: beta\n:returns: gamma")
    assert params == {"a": "alpha", "b": "beta"} and returns == "gamma"


# --------------------------------------------------------------------------- schemas


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


def sample(
    structure: Crystal,
    count: int,
    scale: float = 1.5,
    name: str = "x",
    flag: bool = False,
    mode: Literal["a", "b"] = "a",
    color: Color = Color.RED,
    vector: list[float] | None = None,
    triple: tuple[int, int, int] = (1, 1, 1),
    mapping: dict[str, float] | None = None,
    lattice: Lattice | None = None,
    path: Path | None = None,
    number_or_list: float | list[float] = 1.0,
    others: list[Structure] | None = None,
    context: ToolContext | None = None,
    hidden: object = None,
    *args,
    **kwargs,
) -> None:
    """Sample function.

    Args:
        structure: The input.
        count: How many.
    """


def test_schema_from_signature_and_docstring():
    t = Tool.from_function(sample)
    props = t.parameters["properties"]
    assert t.name == "sample" and t.description == "Sample function."
    assert t.parameters["required"] == ["structure", "count"]
    assert t.parameters["additionalProperties"] is False
    assert props["structure"]["type"] == "string"
    assert props["structure"]["description"].startswith("The input. A structure: a reference")
    assert props["count"] == {"type": "integer", "description": "How many."}
    assert props["scale"] == {"type": "number", "default": 1.5}
    assert props["flag"] == {"type": "boolean", "default": False}
    assert props["mode"] == {"enum": ["a", "b"], "type": "string", "default": "a"}
    assert props["color"] == {"enum": ["red", "blue"]}  # an Enum default is not JSON
    assert props["vector"] == {"anyOf": [{"type": "array", "items": {"type": "number"}}, {"type": "null"}]}
    assert props["triple"] == {"type": "array", "items": {"type": "integer"}, "minItems": 3, "maxItems": 3,
                               "default": [1, 1, 1]}
    assert props["mapping"]["anyOf"][0] == {"type": "object", "additionalProperties": {"type": "number"}}
    assert props["lattice"]["type"] == "array"
    assert props["path"]["type"] == "string"
    assert props["number_or_list"]["anyOf"] == [{"type": "number"}, {"type": "array", "items": {"type": "number"}}]
    assert props["others"]["items"] == {"type": "string"}
    # the context is injected, *args/**kwargs and unsupported optional parameters are hidden
    assert not {"context", "hidden", "args", "kwargs"} & set(props)
    assert t.context_param == "context"
    assert t.kinds == {"structure": "structure", "lattice": "lattice", "path": "path", "others": "structures"}


def test_schemas_are_valid_openai_and_mcp_definitions():
    t = Tool.from_function(sample)
    assert t.openai_schema()["type"] == "function"
    assert t.openai_schema()["function"]["parameters"] == dict(t.parameters)
    assert t.mcp_schema()["inputSchema"] == dict(t.parameters)
    json.dumps(t.openai_schema())  # JSON-compatible
    # the returned copies cannot change the tool
    t.openai_schema()["function"]["parameters"]["properties"].clear()
    assert t.parameters["properties"]


def test_required_parameter_of_unsupported_type_is_an_error():
    def bad(callback: callable):  # noqa: ANN001
        """Bad."""

    def also_bad(x: object):
        """Bad."""

    with pytest.raises(ToolSchemaError, match="parameter 'x'"):
        Tool.from_function(also_bad)
    with pytest.raises(ToolSchemaError):
        Tool.from_function(lambda y, /: y)  # positional-only


def test_marker_overrides_name_description_paths_and_exclude():
    @tool(name="renamed", paths=("filename",), exclude=("debug",))
    def original(filename: str, debug: bool = False) -> None:
        """Original summary."""

    assert tool_marker(original).name == "renamed"
    t = Tool.from_function(original)
    assert t.name == "renamed"
    assert t.kinds == {"filename": "path"}
    assert "debug" not in t.parameters["properties"]
    with pytest.raises(ToolSchemaError, match="no parameters named"):
        Tool.from_function(original, paths=("missing",))
    with pytest.raises(ToolSchemaError, match="invalid tool name"):
        Tool.from_function(original, name="bad name")


def test_the_marker_does_not_change_the_function():
    def f(x: int) -> int:
        """Double."""
        return 2 * x

    assert tool(f) is f and f(2) == 4


def test_function_edits_change_the_tool(tmp_path, monkeypatch):
    """The function is the only definition: edit it, refresh, and the tool follows."""
    module = tmp_path / "my_tools.py"
    module.write_text(textwrap.dedent('''
        from matsimpy.utils.tooling import tool

        @tool
        def greet(name: str) -> str:
            """Say hello."""
            return "hello " + name
    '''))
    monkeypatch.syspath_prepend(str(tmp_path))
    catalog = ToolCatalog()
    catalog.add_module("my_tools")
    assert catalog["greet"].description == "Say hello."
    assert catalog["greet"].parameters["required"] == ["name"]

    module.write_text(textwrap.dedent('''
        from matsimpy.utils.tooling import tool

        @tool
        def greet(name: str, times: int = 1) -> str:
            """Say hello several times.

            Args:
                times: How often.
            """
            return " ".join(["hello " + name] * times)
    '''))
    importlib.invalidate_caches()
    catalog.refresh(reload=True)
    assert catalog["greet"].description == "Say hello several times."
    assert catalog["greet"].parameters["properties"]["times"] == {
        "type": "integer", "description": "How often.", "default": 1}
    sys.modules.pop("my_tools", None)


# --------------------------------------------------------------------------- catalog


def test_default_catalog_builds_every_marked_library_function():
    catalog = ToolCatalog.default()
    assert catalog.skipped == {}
    expected = {"from_prototype", "random_crystal", "read_structure", "write_structure", "make_supercell",
                "create_vacancy", "translate", "apply_strain", "analyze_symmetry", "get_prototype",
                "create_crystal", "create_molecule", "analyze_bonds", "calculate_lennard_jones",
                "store_structure", "retrieve_structure", "write_vasp_input"}
    assert expected <= set(catalog)
    for t in catalog.values():
        assert t.description and t.parameters["type"] == "object"


def test_every_marked_function_in_the_package_is_in_the_default_catalog():
    """A @tool function that is not exported from a scanned module would silently be missed."""
    catalog = ToolCatalog.default()
    functions = {id(t.function) for t in catalog.values()}
    missing = []
    for info in pkgutil.walk_packages(matsimpy.__path__, "matsimpy."):
        if info.name.startswith(("matsimpy.ai.builtin_skills", "matsimpy.ai.cli")):
            continue
        try:
            module = importlib.import_module(info.name)
        except ImportError:
            continue  # optional dependency
        for name, value in vars(module).items():
            if inspect.isfunction(value) and tool_marker(value) and value.__module__ == info.name \
                    and id(value) not in functions:
                missing.append(f"{info.name}.{name}")
    assert not missing


def test_search_add_remove_and_duplicates():
    catalog = ToolCatalog.default()
    assert catalog.search("supercell")[0].name == "make_supercell"
    assert "generate_slab" in [t.name for t in catalog.search("slab surface")]
    assert catalog.search("zzzz") == []

    def make_supercell(x: int) -> int:
        """Another tool with a taken name."""
        return x

    with pytest.raises(ValueError, match="duplicate tool name"):
        catalog.add(make_supercell)
    catalog.add(make_supercell, replace=True)
    assert catalog["make_supercell"].function is make_supercell
    catalog.add(Tool.from_function(make_supercell, name="extra", source="skill:x"))
    assert catalog.remove_source("skill:x") == ["extra"]


# --------------------------------------------------------------------------- execution


@pytest.fixture
def executor(tmp_path):
    return ToolExecutor(ToolCatalog.default(), tmp_path)


def test_structures_pass_between_calls_as_references(executor, tmp_path):
    built = executor.call("from_prototype", {"prototype": "rocksalt", "species": ["Na", "Cl"],
                                             "lattice_constant": 5.64})
    assert built.ok and built.value["structure_ref"] == "structure:1"
    assert built.value["formula"] == "NaCl" and built.value["num_atoms"] == 2
    assert built.value["volume"] == pytest.approx(5.64 ** 3 / 4, rel=1e-4)

    supercell = executor.call("make_supercell", {"crystal": "structure:1", "scaling_matrix": [2, 1, 1]})
    assert supercell.value["structure_ref"] == "structure:2" and supercell.value["num_atoms"] == 4

    written = executor.call("write_structure", {"structure": "structure:2", "filename": "nacl.cif"})
    assert written.value == {"status": "ok", "filename": "nacl.cif"}
    assert (tmp_path / "nacl.cif").is_file()

    # a structure file in the workspace is accepted wherever a structure is
    symmetry = executor.call("get_prototype", {"crystal": "nacl.cif"})
    assert symmetry.content() == {"result": "AB_cF8_225_a_b"}
    # the dict a result was returned in is accepted too
    assert executor.call("get_prototype", {"crystal": built.value}).ok is False  # validation: must be a string
    assert executor.resolve({"structure_ref": "structure:1"}) is executor.objects["structure:1"]


def test_failures_are_results_with_clear_messages(executor):
    missing = executor.call("from_prototype", {"prototype": "fcc", "species": "Cu"})
    assert not missing.ok and missing.error == "invalid arguments: missing required 'lattice_constant'"

    wrong = executor.call("from_prototype", {"prototype": 1, "species": "Cu", "lattice_constant": "x"})
    assert "prototype: expected string, got integer" in wrong.error
    assert "lattice_constant: expected one of" in wrong.error

    extra = executor.call("translate", {"structure": "structure:1", "vector": [0, 0, 1], "speed": 3})
    assert "unknown 'speed'" in extra.error

    raised = executor.call("from_prototype", {"prototype": "unobtainium", "species": "Cu", "lattice_constant": 3})
    assert raised.error.startswith("ValueError: Unknown prototype 'unobtainium'")

    unknown_ref = executor.call("translate", {"structure": "structure:7", "vector": [0, 0, 1]})
    assert unknown_ref.error == "unknown structure reference 'structure:7' (known: none yet)"

    unknown_tool = executor.call("translat", {})
    assert unknown_tool.error.startswith("unknown tool 'translat'; similar tools: translate")
    assert unknown_tool.content() == {"error": unknown_tool.error}


def test_paths_stay_in_the_workspace(executor, tmp_path):
    executor.call("create_molecule", {"species": ["H", "H"], "positions": [[0, 0, 0], [0.74, 0, 0]]})
    outside = executor.call("write_structure", {"structure": "structure:1", "filename": "../h2.xyz"})
    assert "outside the workspace" in outside.error
    absolute = executor.call("write_structure", {"structure": "structure:1", "filename": "/tmp/h2.xyz"})
    assert "outside the workspace" in absolute.error
    nested = executor.call("write_structure", {"structure": "structure:1", "filename": "out/h2.xyz"})
    assert nested.ok is False or (tmp_path / "out" / "h2.xyz").is_file()

    free = ToolExecutor(executor.catalog, tmp_path / "ws", confine_paths=False)
    free.call("create_molecule", {"species": ["H"], "positions": [[0, 0, 0]]})
    assert free.call("write_structure", {"structure": "structure:1", "filename": str(tmp_path / "h.xyz")}).ok


def test_lattice_argument_and_context_injection(executor, tmp_path):
    cubic = executor.call("create_crystal", {"species": ["Li", "F"], "positions": [[0, 0, 0], [.5, .5, .5]],
                                             "lattice": [4.02, 4.02, 4.02, 90, 90, 90]})
    vectors = executor.call("create_crystal", {"species": ["Li"], "positions": [[0, 0, 0]],
                                               "lattice": [[3, 0, 0], [0, 3, 0], [0, 0, 3]]})
    assert cubic.value["lattice"]["a"] == 4.02 and vectors.value["volume"] == pytest.approx(27)
    bad = executor.call("create_crystal", {"species": ["Li"], "positions": [[0, 0, 0]], "lattice": [1, 2]})
    assert "a lattice is three vectors" in bad.error

    stored = executor.call("store_structure", {"structure": "structure:1", "metadata": {"project": "demo"}})
    assert stored.ok and len(stored.value["doc_id"]) == 64
    assert executor.call("query_structures", {"metadata": {"project": "demo"}}).content() == {
        "result": [{"formula": "LiF", "num_atoms": 2}]}
    again = executor.call("retrieve_structure", {"doc_id": stored.value["doc_id"]})
    assert again.value["formula"] == "LiF" and again.value["structure_ref"] == "structure:3"
    # every executor (agent session) has its own database
    assert ToolExecutor(executor.catalog, tmp_path).call("query_structures", {"metadata": {}}).content() == {
        "result": []}


def test_results_become_json(tmp_path):
    @dataclass(frozen=True)
    class Info:
        value: float

    def numbers() -> dict:
        """Numbers."""
        return {"array": np.arange(3), "scalar": np.float64(1.5), "path": tmp_path / "a.txt",
                "info": Info(2.0), "nan": float("nan"), "set": {2, 1}, "molecule": Molecule(["H"], [[0, 0, 0]])}

    def big() -> str:
        """Big."""
        return "x" * 50

    executor = ToolExecutor(ToolCatalog([Tool.from_function(numbers), Tool.from_function(big)]), tmp_path,
                            max_result_chars=20)
    value = ToolExecutor(executor.catalog, tmp_path).call("numbers").value
    assert value["array"] == [0, 1, 2] and value["scalar"] == 1.5 and value["path"] == "a.txt"
    assert value["info"] == {"value": 2.0} and value["nan"] == "nan" and value["set"] == [1, 2]
    assert value["molecule"]["structure_ref"] == "structure:1"
    truncated = executor.call("big").value
    assert truncated["truncated"] is True and truncated["chars"] == 52


def test_tool_errors_and_objects_survive_export(executor, tmp_path):
    def picky(x: int) -> int:
        """Picky."""
        raise ToolError("x must be prime")

    executor.catalog.add(picky)
    assert executor.call("picky", {"x": 4}).error == "x must be prime"

    executor.call("from_prototype", {"prototype": "fcc", "species": "Cu", "lattice_constant": 3.61})
    executor.call("create_molecule", {"species": ["O", "H", "H"], "positions": [[0, 0, 0], [1, 0, 0], [0, 1, 0]]})
    saved = json.loads(json.dumps(executor.export_objects()))
    restored = ToolExecutor(executor.catalog, tmp_path)
    restored.import_objects(saved)
    assert isinstance(restored.objects["structure:1"], Crystal)
    assert isinstance(restored.objects["structure:2"], Molecule)
    assert restored.objects["structure:1"] == executor.objects["structure:1"]
    assert restored.store(Molecule(["H"], [[0, 0, 0]])) == "structure:3"


def test_validate_subset():
    schema = {"type": "object", "properties": {"n": {"type": "integer"}, "xs": {"type": "array", "items": {
        "type": "number"}}}, "required": ["n"], "additionalProperties": False}
    assert validate(schema, {"n": 1, "xs": [1, 2.5]}) == []
    assert validate(schema, {"n": True}) == ["n: expected integer, got boolean"]
    assert validate(schema, {"n": 1, "xs": [1, "a"]}) == ["xs[1]: expected number, got string"]
    assert validate(schema, {}) == ["missing required 'n'"]
