"""DeepSeek API provider — OpenAI-compatible chat completions.

Supports:
- deepseek-v4-pro (recommended)
- deepseek-v4-flash (fast)
- deepseek-chat (deprecated 2026/07/24)
- deepseek-reasoner (deprecated 2026/07/24)

Endpoints:
- OpenAI-compatible: POST /v1/chat/completions
- Anthropic-compatible: POST /anthropic/v1/messages (future)
"""

from __future__ import annotations
import json
import os
import requests
from .conversation import ChatMessage, ToolCall, ChatResponse

# Available models
MODELS = {
    "deepseek-v4-pro": "Most capable model — best for tool use and complex reasoning",
    "deepseek-v4-flash": "Fast and affordable — good for simple queries",
    "deepseek-chat": "DEPRECATED — will be removed 2026/07/24",
    "deepseek-reasoner": "DEPRECATED — will be removed 2026/07/24",
}

DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider:
    """OpenAI-compatible client for DeepSeek API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DeepSeek API key required. Set DEEPSEEK_API_KEY env var "
                "or pass api_key to DeepSeekProvider()."
            )
        self.model = model or os.getenv("MATSIMPY_AI_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._endpoint = f"{self.base_url}/v1/chat/completions"

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> ChatResponse:
        """Send chat completion request. Returns response with any tool calls.

        Uses OpenAI-compatible endpoint: POST {base_url}/v1/chat/completions
        """
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            self._endpoint,
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        msg_data = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        tool_calls = []
        if "tool_calls" in msg_data and msg_data["tool_calls"]:
            for tc in msg_data["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, KeyError):
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=args,
                ))

        message = ChatMessage(
            role=msg_data.get("role", "assistant"),
            content=msg_data.get("content", "") or "",
            tool_calls=[{
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            } for tc in tool_calls] if tool_calls else None,
        )

        return ChatResponse(
            message=message,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    @classmethod
    def list_models(cls) -> dict:
        return MODELS


__all__ = ["DeepSeekProvider", "MODELS", "DEFAULT_MODEL"]
