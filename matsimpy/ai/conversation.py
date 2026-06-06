"""Chat message and tool call data classes for the AI module."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: str          # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: list | None = None       # assistant messages may have tool_calls
    tool_call_id: str | None = None      # tool messages must have this

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str, tool_calls: list | None = None) -> ChatMessage:
        return cls(role="assistant", content=content, tool_calls=tool_calls)

    @classmethod
    def tool(cls, content: str, tool_call_id: str) -> ChatMessage:
        return cls(role="tool", content=content, tool_call_id=tool_call_id)


@dataclass
class ToolCall:
    """An LLM-requested function call."""
    id: str
    name: str          # function name
    arguments: dict    # parsed JSON arguments


@dataclass
class ChatResponse:
    """Response from the LLM provider."""
    message: ChatMessage
    tool_calls: list   # list[ToolCall]
    finish_reason: str  # "stop" | "tool_calls" | "length"


__all__ = ["ChatMessage", "ToolCall", "ChatResponse"]
