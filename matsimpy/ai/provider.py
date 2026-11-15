"""Chat messages and the LLM provider.

:class:`ChatProvider` is the interface the agent needs: one ``chat`` call that
takes messages and tool schemas and returns the next assistant message.
:class:`DeepSeekProvider` implements it for DeepSeek and any other
OpenAI-compatible chat-completions API: requests go to ``<base_url>/chat/completions``.

DeepSeek models think before they answer.  The reasoning comes back as
``reasoning_content``.  DeepSeek's documentation requires the reasoning of every earlier
assistant message to be sent back when a request carries tools (it may answer 400
otherwise), so :class:`ChatMessage` keeps it and sessions save it.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ChatResponse",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DeepSeekProvider",
    "EFFORTS",
    "MODELS",
    "ToolCall",
]

MODELS = {
    "deepseek-v4-pro": "Most capable model; best for tool use and complex reasoning",
    "deepseek-flash": "Fast and affordable; good for simple tasks (deepseek-v4-flash is a legacy alias)",
}
EFFORTS = ("off", "low", "high", "max")
"""Reasoning effort: ``off`` turns thinking off; ``None`` keeps the server default (high)."""
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"


@dataclass
class ChatMessage:
    """One message of a conversation, in the OpenAI chat format."""

    role: str  # system | user | assistant | tool
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    reasoning_content: str | None = None
    """The model's reasoning (DeepSeek thinking mode); must be sent back with tools."""

    def to_dict(self) -> dict:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.reasoning_content:
            data["reasoning_content"] = self.reasoning_content
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> ChatMessage:
        return cls(data["role"], data.get("content") or "", data.get("tool_calls"), data.get("tool_call_id"),
                   data.get("reasoning_content"))

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls("system", content)

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls("user", content)

    @classmethod
    def assistant(cls, content: str, tool_calls: list[ToolCall] | None = None,
                  reasoning_content: str | None = None) -> ChatMessage:
        calls = [call.to_dict() for call in tool_calls] if tool_calls else None
        return cls("assistant", content, calls, reasoning_content=reasoning_content or None)

    @classmethod
    def tool(cls, content: str, tool_call_id: str) -> ChatMessage:
        return cls("tool", content, tool_call_id=tool_call_id)


@dataclass
class ToolCall:
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: dict

    def to_dict(self) -> dict:
        return {"id": self.id, "type": "function",
                "function": {"name": self.name, "arguments": json.dumps(self.arguments)}}


@dataclass
class ChatResponse:
    """The model's next message."""

    message: ChatMessage
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"  # stop | tool_calls | length
    usage: dict[str, int] = field(default_factory=dict)


class ChatProvider(Protocol):
    """What the agent needs from an LLM."""

    model: str

    def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> ChatResponse:
        """The next assistant message for ``messages``, optionally calling ``tools``."""


class DeepSeekProvider:
    """Client for DeepSeek or another OpenAI-compatible chat-completions API.

    Args:
        api_key: Default ``$DEEPSEEK_API_KEY``.
        model: Default ``$MATSIMPY_AI_MODEL``, else :data:`DEFAULT_MODEL`.
        base_url: API root; ``/chat/completions`` is appended, as in the OpenAI SDK
            (so an OpenAI-style root ends in ``/v1``).  Default ``$MATSIMPY_AI_BASE_URL``,
            else :data:`DEFAULT_BASE_URL`.
        reasoning_effort: One of :data:`EFFORTS`; default ``$MATSIMPY_AI_EFFORT``, else the
            server default.  Lower effort answers faster.
        request_timeout: Seconds to wait for one reply.
        max_retries: Retries after a connection error, a timeout, 429 or a 5xx reply.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        *,
        reasoning_effort: str | None = None,
        request_timeout: float = 300,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key required: set DEEPSEEK_API_KEY or pass api_key")
        self.model = model or os.getenv("MATSIMPY_AI_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.getenv("MATSIMPY_AI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        effort = reasoning_effort or os.getenv("MATSIMPY_AI_EFFORT") or None
        if effort is not None and effort not in EFFORTS:
            raise ValueError(f"reasoning_effort must be one of {', '.join(EFFORTS)}, got {effort!r}")
        self.reasoning_effort = effort
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self._sleep = time.sleep

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def payload(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> dict[str, Any]:
        """The request body."""
        payload: dict[str, Any] = {"model": self.model, "messages": [m.to_dict() for m in messages]}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if self.reasoning_effort == "off":
            payload["thinking"] = {"type": "disabled"}
        elif self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        return payload

    def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> ChatResponse:
        import requests

        payload = self.payload(messages, tools)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                response = requests.post(self.endpoint, json=payload, headers=headers, timeout=self.request_timeout)
            except (requests.ConnectionError, requests.Timeout):
                if last:
                    raise
                self._sleep(2 ** attempt)
                continue
            if response.status_code in RETRY_STATUS and not last:
                self._sleep(_retry_after(response) or 2 ** attempt)
                continue
            if response.status_code >= 400:
                # the body says what is wrong (bad model name, missing reasoning_content, ...)
                raise RuntimeError(f"HTTP {response.status_code} from {self.endpoint}: {response.text[:500]}")
            return parse_chat_completion(response.json())
        raise AssertionError("unreachable")


def _retry_after(response) -> float | None:
    try:
        return min(float(response.headers.get("Retry-After", "")), 60.0)
    except ValueError:
        return None


def parse_chat_completion(data: dict) -> ChatResponse:
    """A :class:`ChatResponse` from an OpenAI-format chat-completion body."""
    choice = data["choices"][0]
    message = choice["message"]
    calls = []
    for item in message.get("tool_calls") or []:
        try:
            arguments = json.loads(item["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {"__invalid_json__": item["function"].get("arguments")}
        calls.append(ToolCall(item["id"], item["function"]["name"], arguments if isinstance(arguments, dict) else {}))
    usage = {key: value for key, value in (data.get("usage") or {}).items() if isinstance(value, int)}
    return ChatResponse(
        ChatMessage.assistant(message.get("content") or "", calls, message.get("reasoning_content")),
        calls,
        choice.get("finish_reason") or "stop",
        usage,
    )
