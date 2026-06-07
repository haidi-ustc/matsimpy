"""Agent memory — user.md, agent.md, soul.md, memory.md persistence."""

from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path.home() / ".matsimpy" / "ai" / "memory"

FILES = {
    "user.md": "# User Preferences\n\n<!-- Add your preferences, project context, and conventions here -->\n\n",
    "agent.md": "# Agent Capabilities\n\n<!-- Auto-generated: loaded skills, defaults, known limitations -->\n\n",
    "soul.md": "# Agent Personality\n\n"
               "You are a helpful materials science AI assistant.\n\n"
               "## Tone\n- Professional but approachable\n"
               "## Style\n- Concise, use bullet points for results\n"
               "## Defaults\n- Prefer CIF for crystal output, XYZ for molecules\n",
    "memory.md": "# Memory\n\n<!-- Auto-appended: learned facts, corrections, patterns -->\n\n",
}


class MemoryValidationError(ValueError):
    """Raised when a memory entry is invalid or unsafe."""


class AgentMemory:
    """Persistent agent memory across sessions."""

    def __init__(self, base_dir: Path | None = None, max_entry_chars: int = 2000):
        self.dir = Path(base_dir) if base_dir else MEMORY_DIR
        self.max_entry_chars = max_entry_chars
        self.dir.mkdir(parents=True, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self) -> None:
        for name, default_content in FILES.items():
            path = self.dir / name
            if not path.exists():
                path.write_text(default_content)

    def read(self, name: str) -> str:
        """Read a memory file. Name without .md extension or with."""
        if not name.endswith(".md"):
            name = f"{name}.md"
        path = self.dir / name
        if not path.exists():
            return ""
        return path.read_text()

    def write(self, name: str, content: str) -> None:
        """Overwrite a memory file."""
        if not name.endswith(".md"):
            name = f"{name}.md"
        (self.dir / name).write_text(content)

    def append(self, name: str, content: str) -> None:
        """Append to a memory file."""
        if not name.endswith(".md"):
            name = f"{name}.md"
        path = self.dir / name
        existing = path.read_text() if path.exists() else ""
        path.write_text(existing + content + "\n")

    def _validate_entry(self, content: str) -> str:
        entry = content.strip()
        if not entry:
            raise MemoryValidationError("memory entry is empty")

        unsafe_phrases = (
            "ignore previous instructions",
            "reveal secrets",
            "print environment",
            "show api key",
            "show token",
        )
        normalized = entry.casefold()
        if any(phrase in normalized for phrase in unsafe_phrases):
            raise MemoryValidationError("memory entry is unsafe")
        if len(entry) > self.max_entry_chars:
            raise MemoryValidationError("memory entry is too large")

        return entry

    def add(self, name: str, content: str) -> None:
        """Add a validated memory entry as a markdown bullet."""
        entry = self._validate_entry(content)
        existing = self.read(name)
        bullet = f"- {entry}"
        if any(line.strip() == bullet for line in existing.splitlines()):
            raise MemoryValidationError("duplicate memory entry")
        self.append(name, bullet)

    def replace(self, name: str, old_text: str, content: str) -> None:
        """Replace the first occurrence of old text with validated content."""
        entry = self._validate_entry(content)
        existing = self.read(name)
        if old_text not in existing:
            raise MemoryValidationError("memory text not found")
        self.write(name, existing.replace(old_text, entry, 1))

    def remove(self, name: str, old_text: str) -> None:
        """Remove the first occurrence of old text from a memory file."""
        existing = self.read(name)
        if old_text not in existing:
            raise MemoryValidationError("memory text not found")
        self.write(name, existing.replace(old_text, "", 1))

    def append_learning(self, entry: dict) -> None:
        """Append a learning entry to memory.md."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        outcome = entry.get("outcome", "unknown")
        insight = entry.get("insight", "")
        tools = ", ".join(entry.get("tools_used", []))
        intent = entry.get("user_intent", "")[:150]

        markdown = f"\n## {ts} — {outcome}\n"
        markdown += f"- **Intent**: {intent}\n"
        if tools:
            markdown += f"- **Tools**: {tools}\n"
        if insight:
            markdown += f"- **Insight**: {insight}\n"
        self.append("memory", markdown)

    def get_soul_prompt(self) -> str:
        """Get soul.md content for system prompt injection."""
        return self.read("soul")

    @property
    def summary(self) -> dict:
        """Summary of all memory files."""
        return {
            name.stem: len(name.read_text().split("\n"))
            for name in self.dir.glob("*.md")
        }


__all__ = ["AgentMemory", "MemoryValidationError"]
