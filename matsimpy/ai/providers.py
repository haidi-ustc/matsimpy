"""Provider protocol and provider exports for MatSimPy AI."""

from __future__ import annotations

from typing import Protocol

from .conversation import ChatMessage, ChatResponse
from .provider import DEFAULT_BASE_URL, DEFAULT_MODEL, MODELS, DeepSeekProvider


class ChatProvider(Protocol):
    """Minimal chat provider interface used by AgentRuntime."""

    model: str

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> ChatResponse:
        """Return the next assistant response for the given messages."""


__all__ = [
    "ChatProvider",
    "DeepSeekProvider",
    "MODELS",
    "DEFAULT_MODEL",
    "DEFAULT_BASE_URL",
]
