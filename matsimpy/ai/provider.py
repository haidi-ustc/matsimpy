"""Chat messages and the LLM provider.

:class:`ChatProvider` is the interface the agent needs: one ``chat`` call that
takes messages and tool schemas and returns the next assistant message.
:class:`DeepSeekProvider` implements it for DeepSeek and any other
OpenAI-compatible ``/v1/chat/completions`` endpoint (``base_url``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ChatResponse",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DeepSeekProvider",
    "MODELS",
    "ToolCall",
]

MODELS = {
    "deepseek-v4-pro": "Most capable model; best for tool use and complex reasoning",
    "deepseek-v4-flash": "Fast and affordable; good for simple tasks",
}
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"


@dataclass
class ChatMessage:
    """One message of a conversation, in the OpenAI chat format."""

    role: str  # system | user | assistant | tool
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> ChatMessage:
        return cls(data["role"], data.get("content") or "", data.get("tool_calls"), data.get("tool_call_id"))

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls("system", content)

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls("user", content)

    @classmethod
    def assistant(cls, content: str, tool_calls: list[ToolCall] | None = None) -> ChatMessage:
        calls = [call.to_dict() for call in tool_calls] if tool_calls else None
        return cls("assistant", content, calls)

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
    """Client for DeepSeek or another OpenAI-compatible chat-completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        request_timeout: float = 120,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key required: set DEEPSEEK_API_KEY or pass api_key")
        self.model = model or os.getenv("MATSIMPY_AI_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.getenv("MATSIMPY_AI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.request_timeout = request_timeout

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> ChatResponse:
        import requests

        payload: dict[str, Any] = {"model": self.model, "messages": [m.to_dict() for m in messages]}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        response = requests.post(
            self.endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return parse_chat_completion(response.json())


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
        ChatMessage.assistant(message.get("content") or "", calls),
        calls,
        choice.get("finish_reason") or "stop",
        usage,
    )
