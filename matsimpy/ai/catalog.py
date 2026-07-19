"""Automatic discovery adapters from MatSimPy registries to LLM tools."""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import inspect
from typing import Any

from .skill import FunctionDef
from .skills._schema import first_doc_line, sig_to_schema


@dataclass(frozen=True)
class RegistryToolSource:
    """Generate current LLM function definitions from a MatSimPy registry.

    The registry is queried on every call, so newly discovered plugins and updated
    specs are reflected without changes to the AI package.
    """

    registry: Any
    skill: str
    schema_attribute: str = "parameter_schema"
    include_signature_parameters: tuple[str, ...] = ()
    include_first_parameter: bool = False

    def get_functions(self) -> list[FunctionDef]:
        functions = []
        for spec in self.registry.list_all():
            fn = spec.callable
            explicit_schema = getattr(spec, self.schema_attribute, None)
            schema = (
                deepcopy(explicit_schema)
                if explicit_schema is not None
                else sig_to_schema(fn)
            )
            if explicit_schema is not None and (
                self.include_signature_parameters or self.include_first_parameter
            ):
                inferred = sig_to_schema(fn)
                included = list(self.include_signature_parameters)
                if self.include_first_parameter:
                    first = next(iter(inspect.signature(fn).parameters), None)
                    if first is not None:
                        included.append(first)
                for name in dict.fromkeys(included):
                    if name in inferred["properties"]:
                        schema.setdefault("properties", {})[name] = inferred["properties"][name]
                    if name in inferred["required"] and name not in schema.setdefault("required", []):
                        schema["required"].insert(0, name)
            description = getattr(spec, "description", "") or first_doc_line(fn)
            functions.append(FunctionDef(
                name=spec.name,
                description=description,
                parameters=schema,
                callable=fn,
                skill=self.skill,
                help_text=getattr(fn, "__doc__", None) or description,
            ))
        return functions


__all__ = ["RegistryToolSource"]
