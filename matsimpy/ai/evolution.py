"""Generate reusable workflow skill drafts from successful AI traces."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Sequence

from .session_store import SessionStore
from .skill_loader import save_skill_md

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_LEARN_RE = re.compile(
    r"(?:\b(?:remember|learn)\s+this\b|"
    r"\b(?:remember|learn|save)\b.{0,32}\b(?:workflow|procedure|for next time|how to)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvolutionCandidate:
    """A reviewable learning candidate derived from trace evidence."""

    kind: Literal["skill", "memory"]
    rationale: str
    source_trace_ids: tuple[int, ...]
    payload: dict[str, Any]


SemanticEvaluator = Callable[[Sequence[Mapping[str, Any]]], EvolutionCandidate | None]


class EvolutionPolicy:
    """Classify reusable experience using deterministic evidence first."""

    def __init__(self, evaluator: SemanticEvaluator | None = None):
        self.evaluator = evaluator

    def classify(
        self,
        trace_history: Sequence[Mapping[str, Any]],
        correction: str | None = None,
        source_trace_id: int | None = None,
    ) -> EvolutionCandidate | None:
        successful = [
            trace for trace in trace_history
            if trace.get("validation_status") == "success"
        ]
        if correction is not None and correction.strip():
            if source_trace_id is not None:
                if (
                    isinstance(source_trace_id, bool)
                    or not isinstance(source_trace_id, int)
                    or source_trace_id <= 0
                ):
                    raise ValueError("source_trace_id must be a positive integer")
                provenance_ids = (source_trace_id,)
            elif trace_history:
                provenance_ids = _trace_ids([trace_history[-1]])
            else:
                provenance_ids = ()
            return EvolutionCandidate(
                "memory",
                "explicit user correction",
                provenance_ids,
                {
                    "content": correction.strip(),
                    "confidence": 1.0,
                    "provenance": "trace" if provenance_ids else "explicit_request",
                },
            )
        if not successful:
            return None

        latest = successful[-1]
        if _LEARN_RE.search(str(latest.get("user_request", ""))):
            return EvolutionCandidate(
                "skill",
                "explicit learn request",
                _trace_ids([latest]),
                {"tool_sequence": _tool_sequence(latest)},
            )

        if _is_recovery(latest):
            return EvolutionCandidate(
                "skill",
                "validated recovery from tool failure",
                _trace_ids([latest]),
                {"tool_sequence": _tool_sequence(latest)},
            )

        latest_sequence = tuple(_tool_sequence(latest))
        matches = [
            trace for trace in successful
            if latest_sequence and tuple(_tool_sequence(trace)) == latest_sequence
        ]
        if len(matches) >= 2:
            return EvolutionCandidate(
                "skill",
                "repeated validated workflow",
                _trace_ids(matches),
                {"tool_sequence": list(latest_sequence), "occurrences": len(matches)},
            )

        sequence = _tool_sequence(latest)
        if len(sequence) >= 3:
            return EvolutionCandidate(
                "skill",
                "nontrivial validated workflow",
                _trace_ids([latest]),
                {"tool_sequence": sequence},
            )

        if self.evaluator is not None:
            return self.evaluator(trace_history)
        return None


class EvolutionManager:
    """Manage semi-automatic skill draft evolution from validated sessions."""

    def __init__(
        self,
        store: SessionStore,
        policy: EvolutionPolicy | None = None,
    ):
        self.store = store
        self.policy = policy or EvolutionPolicy()

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

        tool_calls = self._tool_calls(session_id)
        trace_history = self._trace_history()
        if not any(trace.get("session_id") == session_id for trace in trace_history):
            trace_history.append({
                "trace_id": session_id,
                "session_id": session_id,
                "user_request": user_request,
                "validation_status": validation_status,
                "tool_calls": tool_calls,
            })
        candidate = self.policy.classify(trace_history)
        if candidate is None or candidate.kind != "skill":
            return None

        tool_calls = [call for call in tool_calls if call["status"] == "success"]

        tools = [call["tool_name"] for call in tool_calls]
        name = self._unique_draft_name(_slug(user_request))
        trigger_keywords = _keywords(user_request)
        body = self._draft_body(user_request, final_response, validation_status, tool_calls)
        metadata = {
            "tools": tools,
            "source_request": user_request,
            "validation_status": validation_status,
            "final_response": final_response,
            "evolution": {
                "kind": candidate.kind,
                "rationale": candidate.rationale,
                "source_trace_ids": list(candidate.source_trace_ids),
                "payload": candidate.payload,
            },
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
        draft = self._find_draft(name)
        if draft is None:
            raise KeyError(f"Unknown generated skill draft: {name}")

        self.store.set_skill_draft_status(name, "approved")
        metadata = draft.get("metadata", {})
        save_skill_md(
            name=name,
            description=metadata.get("description") or f"Generated skill draft for {name}",
            tools=_normalize_tools(metadata.get("tools", [])),
            trigger_keywords=draft.get("trigger_keywords", []),
            body=draft.get("body", ""),
            load_mode=metadata.get("load_mode", "auto_choice"),
            status="approved",
        )

    def reject(self, name: str) -> None:
        """Archive a generated skill draft."""
        self.store.set_skill_draft_status(name, "archived")

    def _find_draft(self, name: str) -> dict | None:
        for draft in self.store.list_skill_drafts(status=None):
            if draft["name"] == name:
                return draft
        return None

    def _tool_calls(self, session_id: int) -> list[dict]:
        rows = self.store.conn.execute(
            """
            SELECT tool_name, arguments_json, result_json, status
            FROM tool_calls
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
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

    def _trace_history(self) -> list[dict]:
        rows = self.store.conn.execute(
            """
            SELECT id, session_id, user_request, validation_status
            FROM task_traces
            ORDER BY id
            """
        ).fetchall()
        return [
            {
                "trace_id": row["id"],
                "session_id": row["session_id"],
                "user_request": row["user_request"],
                "validation_status": row["validation_status"],
                "tool_calls": self._tool_calls(row["session_id"]),
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


def _trace_ids(traces: Sequence[Mapping[str, Any]]) -> tuple[int, ...]:
    return tuple(
        int(trace["trace_id"])
        for trace in traces
        if trace.get("trace_id") is not None
    )


def _tool_sequence(trace: Mapping[str, Any]) -> list[str]:
    tools = trace.get("tools")
    if isinstance(tools, (list, tuple)):
        return [str(tool) for tool in tools]
    calls = trace.get("tool_calls", ())
    return [
        str(call.get("name", call.get("tool_name")))
        for call in calls
        if isinstance(call, Mapping)
        and call.get("status") == "success"
        and call.get("name", call.get("tool_name")) is not None
    ]


def _is_recovery(trace: Mapping[str, Any]) -> bool:
    calls = trace.get("tool_calls", ())
    failure_seen = False
    for call in calls:
        if not isinstance(call, Mapping):
            continue
        if call.get("status") == "failure":
            failure_seen = True
        elif failure_seen and call.get("status") == "success":
            return True
    return False


def _normalize_tools(tools: Any) -> list[dict]:
    if not isinstance(tools, list):
        return []

    normalized = []
    for tool in tools:
        if isinstance(tool, str):
            normalized.append({"function": tool})
        elif isinstance(tool, dict):
            if "function" in tool:
                normalized.append(tool)
            elif "name" in tool:
                normalized.append({**tool, "function": tool["name"]})
    return normalized


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


__all__ = ["EvolutionCandidate", "EvolutionManager", "EvolutionPolicy"]
