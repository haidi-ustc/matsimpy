"""Agent memory — user.md, agent.md, soul.md, memory.md persistence."""

from __future__ import annotations
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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

MUTABLE_TARGETS = {"memory", "user", "agent"}
STRUCTURED_MEMORY_FILE = "entries.json"
_FINGERPRINT_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class MemoryValidationError(ValueError):
    """Raised when a memory entry is invalid or unsafe."""


@dataclass(frozen=True)
class MemoryEntry:
    """A durable fact with deduplication and provenance metadata."""

    content: str
    fingerprint: str
    confidence: float
    source_trace_ids: tuple[int, ...]
    supersedes: str | None = None
    superseded_by: str | None = None
    created_at: str = ""


def normalized_fingerprint(content: str) -> str:
    """Return a stable fingerprint insensitive to case and punctuation."""
    normalized = " ".join(_FINGERPRINT_TOKEN_RE.findall(content.casefold()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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
        if "\n" in entry or "\r" in entry:
            raise MemoryValidationError("memory entry must be a single line")

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

    def _validate_target(self, name: str) -> str:
        target = name.strip()
        if not target:
            raise MemoryValidationError("memory target is empty")
        if os.path.isabs(target) or "/" in target or "\\" in target or ".." in target:
            raise MemoryValidationError("invalid memory target")
        if target.endswith(".md"):
            target = target[:-3]
        if target not in MUTABLE_TARGETS:
            raise MemoryValidationError("invalid memory target")
        return target

    def _validate_selector(self, old_text: str) -> None:
        if not old_text.strip():
            raise MemoryValidationError("memory selector is empty")

    def _sanitize_learning_field(
        self,
        value: object,
        max_chars: int | None = None,
    ) -> str:
        """Render automatic learning fields as safe single-line markdown text."""
        text = " ".join(str(value).split())
        text = text.replace("#", "").replace("- ", "")
        text = " ".join(text.split()).strip()
        if max_chars is not None:
            return text[:max_chars].strip()
        return text

    def add(self, name: str, content: str) -> None:
        """Add a validated memory entry as a markdown bullet."""
        target = self._validate_target(name)
        entry = self._validate_entry(content)
        existing = self.read(target)
        bullet = f"- {entry}"
        if any(line.strip() == bullet for line in existing.splitlines()):
            raise MemoryValidationError("duplicate memory entry")
        self.append(target, bullet)

    def replace(self, name: str, old_text: str, content: str) -> None:
        """Replace the first occurrence of old text with validated content."""
        target = self._validate_target(name)
        entry = self._validate_entry(content)
        self._validate_selector(old_text)
        existing = self.read(target)
        if old_text not in existing:
            raise MemoryValidationError("memory text not found")
        self.write(target, existing.replace(old_text, entry, 1))

    def remove(self, name: str, old_text: str) -> None:
        """Remove the first occurrence of old text from a memory file."""
        target = self._validate_target(name)
        self._validate_selector(old_text)
        existing = self.read(target)
        if old_text not in existing:
            raise MemoryValidationError("memory text not found")
        self.write(target, existing.replace(old_text, "", 1))

    def append_learning(self, entry: dict) -> None:
        """Append a learning entry to memory.md."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        outcome = self._sanitize_learning_field(entry.get("outcome", "unknown"), 40)
        insight = self._sanitize_learning_field(entry.get("insight", ""))
        tools = ", ".join(
            self._sanitize_learning_field(tool)
            for tool in entry.get("tools_used", [])
        )
        intent = self._sanitize_learning_field(entry.get("user_intent", ""), 150)

        markdown = f"\n## {ts} — {outcome}\n"
        markdown += f"- **Intent**: {intent}\n"
        if tools:
            markdown += f"- **Tools**: {tools}\n"
        if insight:
            markdown += f"- **Insight**: {insight}\n"
        self.append("memory", markdown)

    def remember(
        self,
        content: str,
        *,
        confidence: float = 1.0,
        source_trace_ids: list[int] | tuple[int, ...] = (),
        supersedes: str | None = None,
    ) -> MemoryEntry:
        """Persist a structured fact, rejecting duplicates and unsafe corrections."""
        validated = self._validate_entry(content)
        if not 0.0 <= confidence <= 1.0:
            raise MemoryValidationError("memory confidence must be between 0 and 1")
        fingerprint = normalized_fingerprint(validated)
        entries = self.structured_entries(include_superseded=True)
        if any(entry.fingerprint == fingerprint for entry in entries):
            raise MemoryValidationError("duplicate memory entry")

        if supersedes is not None:
            matches = [
                entry for entry in entries
                if entry.fingerprint == supersedes and entry.superseded_by is None
            ]
            if not matches:
                raise MemoryValidationError("memory entry to supersede was not found or is inactive")

        new_entry = MemoryEntry(
            content=validated,
            fingerprint=fingerprint,
            confidence=float(confidence),
            source_trace_ids=tuple(int(trace_id) for trace_id in source_trace_ids),
            supersedes=supersedes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        updated = []
        for entry in entries:
            if entry.fingerprint == supersedes:
                entry = MemoryEntry(**{**asdict(entry), "superseded_by": fingerprint})
            updated.append(entry)
        updated.append(new_entry)
        self._write_structured_entries(updated)
        return new_entry

    def structured_entries(self, include_superseded: bool = False) -> list[MemoryEntry]:
        """Load structured facts, hiding superseded entries by default."""
        path = self.dir / STRUCTURED_MEMORY_FILE
        if not path.exists():
            return []
        raw: Any = json.loads(path.read_text())
        if not isinstance(raw, list):
            raise MemoryValidationError("structured memory ledger is malformed")
        entries = [
            MemoryEntry(
                content=item["content"],
                fingerprint=item["fingerprint"],
                confidence=float(item["confidence"]),
                source_trace_ids=tuple(item.get("source_trace_ids", ())),
                supersedes=item.get("supersedes"),
                superseded_by=item.get("superseded_by"),
                created_at=item.get("created_at", ""),
            )
            for item in raw
        ]
        if include_superseded:
            return entries
        return [entry for entry in entries if entry.superseded_by is None]

    def _write_structured_entries(self, entries: list[MemoryEntry]) -> None:
        payload = [
            {**asdict(entry), "source_trace_ids": list(entry.source_trace_ids)}
            for entry in entries
        ]
        path = self.dir / STRUCTURED_MEMORY_FILE
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)

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


__all__ = [
    "AgentMemory",
    "MemoryEntry",
    "MemoryValidationError",
    "normalized_fingerprint",
]
