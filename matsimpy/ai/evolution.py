"""Generate reusable workflow skill drafts from successful AI traces."""

from __future__ import annotations

import json
import re
from typing import Any

from .session_store import SessionStore

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class EvolutionManager:
    """Manage semi-automatic skill draft evolution from validated sessions."""

    def __init__(self, store: SessionStore):
        self.store = store

    def draft_from_trace(
        self,
        session_id: int,
        user_request: str,
        final_response: str,
        validation_status: str,
    ) -> dict | None:
        """Create a draft skill from a successful trace with reusable tool evidence."""
        if validation_status != "success":
            return None

        tool_calls = self._successful_tool_calls(session_id)
        if len(tool_calls) < 2:
            return None

        tools = [call["tool_name"] for call in tool_calls]
        name = self._unique_draft_name(_slug(user_request))
        trigger_keywords = _keywords(user_request)
        body = self._draft_body(user_request, final_response, validation_status, tool_calls)
        metadata = {
            "tools": tools,
            "source_request": user_request,
            "validation_status": validation_status,
            "final_response": final_response,
        }

        self.store.save_skill_draft(
            name=name,
            status="draft",
            source_session_id=session_id,
            trigger_keywords=trigger_keywords,
            body=body,
            metadata=metadata,
        )

        drafts = self.store.list_skill_drafts(None)
        for draft in drafts:
            if draft["name"] == name:
                return draft
        return {
            "name": name,
            "status": "draft",
            "source_session_id": session_id,
            "trigger_keywords": trigger_keywords,
            "body": body,
            "metadata": metadata,
        }

    def _unique_draft_name(self, base_name: str) -> str:
        existing_names = {draft["name"] for draft in self.store.list_skill_drafts(None)}
        if base_name not in existing_names:
            return base_name

        suffix = 2
        while f"{base_name}-{suffix}" in existing_names:
            suffix += 1
        return f"{base_name}-{suffix}"

    def approve(self, name: str) -> None:
        """Approve a generated skill draft."""
        self.store.set_skill_draft_status(name, "approved")

    def reject(self, name: str) -> None:
        """Archive a generated skill draft."""
        self.store.set_skill_draft_status(name, "archived")

    def _successful_tool_calls(self, session_id: int) -> list[dict]:
        rows = self.store.conn.execute(
            """
            SELECT tool_name, arguments_json, result_json, status
            FROM tool_calls
            WHERE session_id = ? AND status = ?
            ORDER BY id
            """,
            (session_id, "success"),
        ).fetchall()
        return [
            {
                "tool_name": row["tool_name"],
                "arguments": _json_load(row["arguments_json"], {}),
                "result": _json_load(row["result_json"], {}),
                "status": row["status"],
            }
            for row in rows
        ]

    @staticmethod
    def _draft_body(
        user_request: str,
        final_response: str,
        validation_status: str,
        tool_calls: list[dict],
    ) -> str:
        lines = [
            f"# {_title(user_request)}",
            "",
            "## Source request",
            user_request,
            "",
            "## Procedure",
        ]
        for index, call in enumerate(tool_calls, 1):
            lines.append(f"{index}. Run `{call['tool_name']}` with arguments:")
            lines.append(f"   `{json.dumps(call['arguments'], sort_keys=True, default=str)}`")
            lines.append("   Expected evidence:")
            lines.append(f"   `{json.dumps(call['result'], sort_keys=True, default=str)}`")

        lines.extend(
            [
                "",
                "## Validation evidence",
                f"- Status: {validation_status}",
                f"- Final response: {final_response}",
            ]
        )
        return "\n".join(lines) + "\n"


def _json_load(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _keywords(text: str) -> list[str]:
    seen = set()
    result = []
    for token in _TOKEN_RE.findall(text.lower()):
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result[:12]


def _slug(text: str) -> str:
    keywords = _keywords(text)
    if not keywords:
        return "generated-skill"
    return "-".join(keywords[:8])


def _title(text: str) -> str:
    words = _keywords(text)
    if not words:
        return "Generated Skill Draft"
    return " ".join(word.capitalize() for word in words[:8])


__all__ = ["EvolutionManager"]
