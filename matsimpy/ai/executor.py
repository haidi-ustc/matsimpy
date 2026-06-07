"""FunctionExecutor — validates and executes LLM function calls.

Pipeline design:
  Serialize:   Crystal/Molecule returned → stored in session registry with opaque ID
               → LLM receives dict with _obj_ref + human-readable summary
  Deserialize: LLM passes dict to next function → executor resolves _obj_ref
               → live object injected before function call
  Auto-retry:  TypeError about Crystal/Molecule → auto-resolve dict args, retry,
               learn the adaptation for future calls
"""

from __future__ import annotations
import json
import numpy as np
from .skill import SkillManager, FunctionDef
from .conversation import ToolCall


class FunctionExecutor:
    """Validates parameters and executes function calls from LLM tool use.

    Maintains a session-scoped object registry so that Crystal/Molecule
    objects survive the serialize→LLM→deserialize round-trip without
    losing their identity.

    Learns from TypeError failures: when a function receives a serialized
    dict instead of a live Crystal/Molecule, the executor auto-retries
    with resolved args and remembers the adaptation for the session.
    """

    def __init__(self, skill_manager: SkillManager):
        self.skill_manager = skill_manager
        self._call_count = 0
        self._max_calls = 50
        self._registry: dict[int, object] = {}   # _obj_ref → live object
        self._next_id = 1
        self._adaptations: dict[str, set[str]] = {}  # fn_name → {arg_keys to deserialize}
        self._retry_count: dict[str, int] = {}        # fn_name → auto-retry attempts
        self._max_retries: int = 3                    # max auto-retries per function per session

    # ── public API ──────────────────────────────────────────────────

    def execute(self, tool_call: ToolCall) -> dict:
        """Execute a tool call. Returns result dict (always JSON-safe)."""
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
            resolved = self._resolve_refs(tool_call.arguments)
            resolved = self._apply_adaptations(tool_call.name, resolved)
            result = fn_def.callable(**resolved)
            return self._serialize(result)
        except TypeError as e:
            return self._auto_retry(fn_def, tool_call, e)
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    # ── auto-retry + skill evolution ─────────────────────────────────

    def _auto_retry(self, fn_def: FunctionDef, tool_call: ToolCall, error: TypeError) -> dict:
        """If a TypeError mentions Crystal/Molecule, try resolving dict args to
        live objects and retry. On success, record the adaptation.
        Limited to _max_retries per function per session."""
        fn_name = tool_call.name

        # Retry limit — prevent infinite loops when the LLM can't produce valid args
        count = self._retry_count.get(fn_name, 0)
        if count >= self._max_retries:
            return {"error": f"TypeError: {error} — auto-retry limit reached ({self._max_retries})"}
        self._retry_count[fn_name] = count + 1

        msg = str(error).lower()
        if not ("crystal" in msg or "molecule" in msg or "structure" in msg):
            return {"error": f"TypeError: {error}"}

        # Find arguments (dicts or bare ints) that could be structure references
        resolved = dict(tool_call.arguments)
        adapted_keys: set[str] = set()

        for key, value in tool_call.arguments.items():
            obj = self._try_resolve_structure(value)
            if obj is not None:
                resolved[key] = obj
                adapted_keys.add(key)

        if not adapted_keys:
            return {"error": f"TypeError: {error} — couldn't auto-resolve, pass a live structure"}

        # Retry with resolved args
        try:
            result = fn_def.callable(**resolved)
        except Exception as e:
            return {"error": f"TypeError: {error} — auto-retry also failed: {e}"}

        # Success! Record the adaptation, reset retry count
        if fn_name not in self._adaptations:
            self._adaptations[fn_name] = set()
        self._adaptations[fn_name] |= adapted_keys
        self._retry_count[fn_name] = 0  # reset on success

        print(f"  🔄 learned: {fn_name}({', '.join(adapted_keys)}) auto-deserialized")
        return self._serialize(result)

    def _try_resolve_structure(self, value: dict):
        """Try to resolve a dict (or bare int) to a live Crystal or Molecule.
        Returns None if not a structure. Bare integers are looked up in the registry
        (LLM might extract just the ref number from _obj_ref)."""
        # Bare integer → look up in registry (LLM extracted the _obj_ref number)
        if isinstance(value, int) and value in self._registry:
            return self._registry[value]
        if not isinstance(value, dict):
            return None
        # Check _obj_ref first
        if "_obj_ref" in value:
            ref = value["_obj_ref"]
            obj = self._registry.get(ref)
            if obj is not None:
                return obj
        # Check MSONable dict
        if "@module" in value and "@class" in value:
            return self._from_dict(value)
        return None

    def _apply_adaptations(self, fn_name: str, args: dict) -> dict:
        """Pre-emptively resolve args that were previously learned to need deserialization."""
        if fn_name not in self._adaptations:
            return args
        result = dict(args)
        for key in self._adaptations[fn_name]:
            if key in result:
                obj = self._try_resolve_structure(result[key])
                if obj is not None:
                    result[key] = obj
        return result

    # ── reference resolution (deserialize) ──────────────────────────

    def _resolve_refs(self, args: dict) -> dict:
        """Walk arguments and resolve any _obj_ref back to live objects."""
        resolved = {}
        for key, value in args.items():
            resolved[key] = self._resolve_one(value)
        return resolved

    def _resolve_one(self, value):
        """Resolve a single value — dicts with _obj_ref become live objects."""
        if isinstance(value, dict) and "_obj_ref" in value:
            ref = value["_obj_ref"]
            obj = self._registry.get(ref)
            if obj is not None:
                return obj
        # Also handle legacy serialized dicts without _obj_ref
        if isinstance(value, dict) and "@module" in value and "@class" in value:
            return self._from_dict(value)
        return value

    def _from_dict(self, d: dict):
        """Reconstruct a live Crystal or Molecule from a legacy MSONable dict."""
        cls_name = d.get("@class", "")
        if cls_name == "Crystal":
            from matsimpy.core import Crystal
            return Crystal.from_dict(d)
        elif cls_name == "Molecule":
            from matsimpy.core import Molecule
            return Molecule.from_dict(d)
        return d

    # ── serialization ───────────────────────────────────────────────

    def _serialize(self, result) -> dict:
        """Convert result to a JSON-safe dict. Structure objects get
        stored in the registry and replaced with a lightweight reference."""
        if self._is_structure(result):
            ref = self._next_id
            self._next_id += 1
            self._registry[ref] = result
            return self._structure_summary(result, ref)

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
            return self._structure_summary(result)
        return {"result": str(result)}

    def _structure_summary(self, obj, ref: int | None = None) -> dict:
        """Build a human-readable summary dict. If ref is given, include _obj_ref.

        The dict is designed so the LLM passes it AS-IS to the next function.
        The _note field tells the LLM NOT to extract individual values.
        """
        d: dict = {
            "_note": "⚠️ pass this entire dict as the structure argument — do NOT extract values",
            "formula": str(obj.formula),
            "num_atoms": len(obj),
        }
        if ref is not None:
            d["_obj_ref"] = ref
        if hasattr(obj, "lattice") and obj.lattice is not None:
            d["lattice"] = {
                "a": round(float(obj.lattice.a), 4),
                "b": round(float(obj.lattice.b), 4),
                "c": round(float(obj.lattice.c), 4),
                "alpha": round(float(obj.lattice.alpha), 2),
                "beta": round(float(obj.lattice.beta), 2),
                "gamma": round(float(obj.lattice.gamma), 2),
            }
        if hasattr(obj, "pbc") and obj.pbc is not None:
            d["pbc"] = list(obj.pbc)
        return d

    @staticmethod
    def _is_structure(obj) -> bool:
        return hasattr(obj, "formula") and hasattr(obj, "species")

    # ── validation ──────────────────────────────────────────────────

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
            # Allow dict for structure parameters (they carry _obj_ref)
            if expected_type == "string" and not isinstance(value, (str, dict)):
                errors.append(f"Parameter '{key}' must be a string")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Parameter '{key}' must be a number")
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Parameter '{key}' must be an integer")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Parameter '{key}' must be an array")

        return errors


# ── module-level accessors (used by IO skill) ──

_active_executor: FunctionExecutor | None = None


def get_last_structure():
    """Return the most recently serialized structure from the active executor."""
    if _active_executor is not None and _active_executor._registry:
        # Return the highest-ID object (most recently stored)
        max_id = max(_active_executor._registry.keys())
        return _active_executor._registry[max_id]
    return None


def set_last_structure(s):
    """Store a structure in the active executor's registry."""
    global _active_executor
    if _active_executor is not None:
        ref = _active_executor._next_id
        _active_executor._next_id += 1
        _active_executor._registry[ref] = s


def _set_active_executor(exe: FunctionExecutor) -> None:
    """Register the active executor (called by AIEngine)."""
    global _active_executor
    _active_executor = exe


__all__ = ["FunctionExecutor", "get_last_structure", "set_last_structure", "_set_active_executor"]
