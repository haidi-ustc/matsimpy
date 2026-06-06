"""DeepSeek API provider — OpenAI-compatible chat completions."""

from __future__ import annotations
import json
import os
import requests
from .conversation import ChatMessage, ToolCall, ChatResponse


class DeepSeekProvider:
    """OpenAI-compatible client for DeepSeek API."""

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str | None = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DeepSeek API key required. Set DEEPSEEK_API_KEY env var "
                "or pass api_key to DeepSeekProvider()."
            )
        self.model = model

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> ChatResponse:
        """Send chat completion request. Returns response with any tool calls."""
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
            f"{self.BASE_URL}/chat/completions",
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


__all__ = ["DeepSeekProvider"]
