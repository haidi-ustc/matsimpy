"""FunctionExecutor — validates and executes LLM function calls."""

from __future__ import annotations
import json
import numpy as np
from .skill import SkillManager, FunctionDef
from .conversation import ToolCall

# Module-level store for the last live structure (used by IO skill)
_last_structure = None


def get_last_structure():
    global _last_structure
    return _last_structure


def set_last_structure(s):
    global _last_structure
    _last_structure = s


class FunctionExecutor:
    """Validates parameters and executes function calls from LLM tool use."""

    def __init__(self, skill_manager: SkillManager):
        self.skill_manager = skill_manager
        self._call_count = 0
        self._max_calls = 50

    def execute(self, tool_call: ToolCall) -> dict:
        """Execute a tool call. Returns result dict."""
        if self._call_count >= self._max_calls:
            return {"error": "Maximum tool call depth exceeded"}
        self._call_count += 1

        fn_def = self.skill_manager.find_function(tool_call.name)
        if not fn_def:
            return {"error": f"Unknown function: {tool_call.name}"}

        errors = self._validate(fn_def, tool_call.arguments)
        if errors:
            return {"error": f"Invalid parameters: {'; '.join(errors)}"}

        try:
            result = fn_def.callable(**tool_call.arguments)
            return self._serialize(result)
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    def _validate(self, fn_def: FunctionDef, args: dict) -> list[str]:
        """Validate args against FunctionDef.parameters JSON Schema."""
        errors = []
        schema = fn_def.parameters or {}
        required = schema.get("required", [])
        props = schema.get("properties", {})

        for key in required:
            if key not in args:
                errors.append(f"Missing required parameter: {key}")

        for key, value in args.items():
            if key not in props:
                continue
            prop = props[key]
            expected_type = prop.get("type")
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Parameter '{key}' must be a string")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Parameter '{key}' must be a number")
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Parameter '{key}' must be an integer")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Parameter '{key}' must be an array")

        return errors

    def _serialize(self, result) -> dict:
        """Convert matsimpy objects to JSON-serializable dicts. Store live structure."""
        # Store live structure object for write operations (module-level)
        if hasattr(result, "formula") and hasattr(result, "species"):
            global _last_structure
            _last_structure = result

        if result is None:
            return {"result": None}
        if isinstance(result, (str, int, float, bool)):
            return {"result": result}
        if isinstance(result, dict):
            return result
        if isinstance(result, np.ndarray):
            return {"result": result.tolist()}
        if isinstance(result, (list, tuple)):
            return {"result": list(result)}
        if hasattr(result, "as_dict"):
            return result.as_dict()
        if hasattr(result, "formula"):
            d = {
                "formula": str(result.formula),
                "num_atoms": len(result),
            }
            if hasattr(result, "lattice") and result.lattice is not None:
                d["lattice"] = {
                    "a": float(result.lattice.a),
                    "b": float(result.lattice.b),
                    "c": float(result.lattice.c),
                }
            return d
        return {"result": str(result)}


__all__ = ["FunctionExecutor"]
