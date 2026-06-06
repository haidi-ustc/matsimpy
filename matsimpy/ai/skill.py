"""FunctionDef, Skill, and SkillManager — progressive loading system."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class FunctionDef:
    """Complete description of a callable function for LLM tool use."""
    name: str
    description: str
    parameters: dict          # JSON Schema for parameters
    callable: Callable
    skill: str = ""
    help_text: str | None = None

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def get_help(self) -> str:
        if self.help_text:
            return self.help_text
        doc = getattr(self.callable, "__doc__", None)
        return doc or f"{self.name}: {self.description}"


# --- Keyword → Skill mapping for auto_load ---
_KEYWORD_MAP = {
    "slab": "builders", "surface": "builders", "adsorbate": "builders",
    "vacancy": "builders", "defect": "builders", "alloy": "builders",
    "nanotube": "builders", "prototype": "builders", "fcc": "builders",
    "bcc": "builders", "hcp": "builders", "interstitial": "builders",
    "interface": "builders", "build": "builders", "create": "builders",
    "translate": "transformation", "rotate": "transformation",
    "strain": "transformation", "scale": "transformation",
    "substitute": "transformation", "supercell": "transformation",
    "transform": "transformation", "move": "transformation",
    "bond": "analysis", "angle": "analysis", "dihedral": "analysis",
    "symmetry": "analysis", "connect": "analysis", "ring": "analysis",
    "topology": "analysis", "analyze": "analysis", "analysis": "analysis",
    "read": "io", "write": "io", "save": "io", "load": "io",
    "file": "io", "format": "io", "convert": "io", "io": "io",
    "store": "storage", "retrieve": "storage", "query": "storage",
    "database": "storage", "storage": "storage",
}


class Skill:
    """A named group of related FunctionDefs. Loaded progressively."""
    def __init__(self, name: str, description: str, functions: list[FunctionDef]):
        self.name = name
        self.description = description
        self.functions = functions
        self.loaded = False
        self.token_estimate = sum(
            len(f.description) + len(f.name) + len(str(f.parameters))
            for f in functions
        ) // 4  # rough token estimate


class SkillManager:
    """Manages progressive loading/unloading of skills."""

    def __init__(self, skills: dict[str, Skill] | None = None):
        self._skills: dict[str, Skill] = skills or {}
        self._active: set[str] = set()

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def load(self, name: str) -> list[FunctionDef]:
        if name not in self._skills:
            raise KeyError(f"Unknown skill: {name}")
        skill = self._skills[name]
        skill.loaded = True
        self._active.add(name)
        return skill.functions

    def unload(self, name: str) -> None:
        if name in self._active:
            self._active.discard(name)
            if name in self._skills:
                self._skills[name].loaded = False

    def get_tools(self) -> list[dict]:
        tools = []
        for name in self._active:
            skill = self._skills[name]
            for fn in skill.functions:
                tools.append(fn.to_openai_tool())
        return tools

    def find_function(self, name: str) -> FunctionDef | None:
        for skill_name in self._active:
            skill = self._skills[skill_name]
            for fn in skill.functions:
                if fn.name == name:
                    return fn
        return None

    def auto_load(self, message: str) -> list[str]:
        """Load skills based on keyword matching in user message."""
        msg_lower = message.lower()
        matched = set()
        for keyword, skill_name in _KEYWORD_MAP.items():
            if keyword in msg_lower:
                matched.add(skill_name)
        loaded = []
        for name in matched:
            if name not in self._active and name in self._skills:
                self.load(name)
                loaded.append(name)
        return loaded

    def list_skills(self) -> list[dict]:
        result = []
        for name, skill in self._skills.items():
            result.append({
                "name": name,
                "description": skill.description,
                "functions": len(skill.functions),
                "loaded": name in self._active,
                "tokens_approx": skill.token_estimate,
            })
        return result

    @property
    def active_skills(self) -> list[str]:
        return sorted(self._active)


__all__ = ["FunctionDef", "Skill", "SkillManager"]
