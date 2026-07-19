"""Tests for AI chat provider boundary."""

from matsimpy.ai.conversation import ChatMessage, ChatResponse
from matsimpy.ai.providers import ChatProvider, DeepSeekProvider


class FakeProvider:
    model = "fake-model"

    def chat(self, messages, tools=None, tool_choice="auto"):
        return ChatResponse(
            message=ChatMessage.assistant("done"),
            tool_calls=[],
            finish_reason="stop",
        )


def test_fake_provider_matches_protocol():
    provider: ChatProvider = FakeProvider()
    response = provider.chat([ChatMessage.user("hello")])
    assert response.finish_reason == "stop"
    assert response.message.content == "done"


def test_deepseek_provider_is_exported_from_providers():
    assert DeepSeekProvider.__name__ == "DeepSeekProvider"


def test_deepseek_provider_uses_configurable_request_timeout(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]}

    def post(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("matsimpy.ai.provider.requests.post", post)
    provider = DeepSeekProvider(api_key="test", request_timeout=30)
    provider.chat([ChatMessage.user("hello")])
    assert captured["timeout"] == 30
