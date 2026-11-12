"""A scripted LLM provider for agent tests."""

from __future__ import annotations

import itertools
import json

import pytest

from matsimpy.ai.provider import ChatMessage, ChatResponse, ToolCall


class ScriptedProvider:
    """Replies from a script; records the messages and tool names of every request.

    Each script item is a string (a final answer), a list of ``(tool, arguments)``
    pairs (tool calls), an exception (raised), or a callable ``(messages) -> item``.
    """

    model = "scripted"

    def __init__(self, *script):
        self.script = list(script)
        self.requests: list[dict] = []
        self._ids = itertools.count(1)

    def chat(self, messages, tools=None):
        self.requests.append({"messages": [m.to_dict() for m in messages],
                              "tools": [t["function"]["name"] for t in tools or []]})
        if not self.script:
            raise AssertionError("the agent asked for more replies than scripted")
        item = self.script.pop(0)
        if callable(item) and not isinstance(item, type):
            item = item(messages)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, str):
            return ChatResponse(ChatMessage.assistant(item), [], "stop", {"prompt_tokens": 10, "completion_tokens": 2})
        calls = [ToolCall(f"call_{next(self._ids)}", name, arguments) for name, arguments in item]
        return ChatResponse(ChatMessage.assistant("", calls), calls, "tool_calls", {"prompt_tokens": 10})

    def tool_results(self, request_index: int) -> list[dict]:
        """The tool results the agent sent in a request."""
        return [json.loads(m["content"]) for m in self.requests[request_index]["messages"] if m["role"] == "tool"]


@pytest.fixture
def scripted():
    return ScriptedProvider
