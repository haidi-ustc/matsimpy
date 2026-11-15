"""DeepSeek-backed agent tools: web search, page fetch, OCR and vision (HTTP mocked)."""

from __future__ import annotations

import base64
import json

import pytest

from matsimpy.ai.tools import ToolCatalog, ToolExecutor

# page text as the OCR API returned it for a two-line image (rich_layout_recognition)
LAYOUT_PAGE = ("<｜ref｜>text<｜/ref｜><｜box｜>[[42,305,415,394]]<｜/box｜> NaCl rocksalt \n"
               "<｜ref｜>text<｜/ref｜><｜box｜>[[42,572,586,661]]<｜/box｜> a = 5.64 Angstrom")


class Reply:
    def __init__(self, body, status=200):
        self.body, self.status_code, self.headers, self.text = body, status, {}, json.dumps(body)

    def json(self):
        return self.body


@pytest.fixture
def api(monkeypatch):
    """Fake DeepSeek: records requests and answers with the queued bodies."""
    sent, replies = [], []

    def post(url, headers, timeout, **kwargs):
        sent.append({"url": url, "headers": headers, **kwargs})
        return Reply(replies.pop(0))

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("MATSIMPY_DEEPSEEK_TOOLS_URL", raising=False)
    monkeypatch.setattr("requests.post", post)
    return sent, replies


@pytest.fixture
def executor(tmp_path):
    return ToolExecutor(ToolCatalog.default(), tmp_path)


def test_web_search(api, executor):
    sent, replies = api
    replies.append({"results": [
        {"title": "NaCl", "url": "https://a.org", "summary": "a = 5.6402 A", "snippet": "s", "date": None,
         "site_name": "A", "rerank_score": 2.1, "content": "x" * 5000},
        {"title": "B", "url": "https://b.org", "summary": "", "snippet": "only a snippet"},
    ]})
    result = executor.call("web_search", {"query": "NaCl lattice constant", "count": 2, "full_content": True})
    assert result.ok, result.error
    assert sent[0]["url"] == "https://api.deepseek.com/v1/tools/search"
    assert sent[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert sent[0]["json"] == {"query": "NaCl lattice constant", "count": 2, "need_content": True}
    first, second = result.value["results"]
    assert (first["url"], first["summary"], len(first["content"])) == ("https://a.org", "a = 5.6402 A", 3000)
    assert second["summary"] == "only a snippet" and "content" not in second


@pytest.mark.parametrize("arguments, error", [
    ({"query": "   "}, "1 to 128 characters"),
    ({"query": "x" * 129}, "1 to 128 characters"),
    ({"query": "NaCl", "count": 51}, "between 1 and 50"),
])
def test_web_search_rejects_bad_arguments_without_a_request(api, executor, arguments, error):
    result = executor.call("web_search", arguments)
    assert error in result.error and api[0] == []


def test_fetch_url_truncates_the_page(api, executor):
    sent, replies = api
    replies.append({"title": "Sodium chloride", "content": "# Sodium chloride\n" + "y" * 100})
    result = executor.call("fetch_url", {"url": "https://en.wikipedia.org/wiki/Sodium_chloride", "max_chars": 20})
    assert sent[0]["json"] == {"url": "https://en.wikipedia.org/wiki/Sodium_chloride"}
    assert result.value["content"] == "# Sodium chloride\nyy" and result.value["truncated"] is True
    assert "http:// or https://" in executor.call("fetch_url", {"url": "file:///etc/passwd"}).error


@pytest.mark.parametrize("layout, purpose, text", [
    (False, "text_recognition", "NaCl rocksalt\na = 5.64 Angstrom"),
    (True, "rich_layout_recognition", LAYOUT_PAGE),
])
def test_ocr_document(api, executor, tmp_path, layout, purpose, text):
    sent, replies = api
    (tmp_path / "scan.png").write_bytes(b"\x89PNG fake")
    replies.append({"object": "ocr.result", "page_count": 2, "pages": [
        {"index": 1, "text": "second", "finish_reason": "length"},
        {"index": 0, "text": LAYOUT_PAGE, "finish_reason": "stop"},
    ]})
    result = executor.call("ocr_document", {"path": "scan.png", "output": "scan.txt", "layout": layout})
    assert result.ok, result.error
    assert sent[0]["url"] == "https://api.deepseek.com/v1/tools/ocr"
    assert sent[0]["data"] == {"purpose": purpose} and sent[0]["files"]["file"][0] == "scan.png"
    expected = f"--- page 1 ---\n{text}\n\n--- page 2 ---\nsecond"
    assert result.value["text"] == expected and result.value["truncated"] is False
    assert result.value["incomplete_pages"] == [2]  # finish_reason "length": the page text is cut
    assert (tmp_path / "scan.txt").read_text() == expected + "\n"


def test_ocr_failures(api, executor, tmp_path):
    sent, replies = api
    (tmp_path / "locked.pdf").write_bytes(b"%PDF fake")
    replies.append({"error": {"message": "The file is password protected", "type": "invalid_request_error"}})
    # once recognition starts the status is 200, and a failure is an error body
    assert executor.call("ocr_document", {"path": "locked.pdf"}).error == "The file is password protected"
    assert executor.call("ocr_document", {"path": "missing.pdf"}).error.endswith("missing.pdf' does not exist")
    assert "outside the workspace" in executor.call("ocr_document", {"path": "/etc/hostname"}).error
    assert len(sent) == 1


def test_describe_image_sends_a_workspace_file_as_a_data_url(api, executor, tmp_path):
    sent, replies = api
    (tmp_path / "figure.png").write_bytes(b"\x89PNG fake")
    replies.append({"model": "deepseek-flash", "choices": [{"message": {"content": "a = 5.64 Angstrom"}}]})
    result = executor.call("describe_image", {"image": "figure.png", "question": "Which lattice constant?"})
    assert result.value == {"image": "figure.png", "model": "deepseek-flash", "answer": "a = 5.64 Angstrom"}
    body = sent[0]["json"]
    assert sent[0]["url"] == "https://api.deepseek.com/chat/completions" and body["model"] == "deepseek-flash"
    text, image = body["messages"][0]["content"]
    assert text == {"type": "text", "text": "Which lattice constant?"}
    assert image["image_url"]["url"] == "data:image/png;base64," + base64.b64encode(b"\x89PNG fake").decode()


def test_describe_image_passes_urls_through(api, executor):
    sent, replies = api
    replies.append({"choices": [{"message": {"content": "a plot"}}]})
    assert executor.call("describe_image", {"image": "https://example.org/fig.jpg"}).value["answer"] == "a plot"
    assert sent[0]["json"]["messages"][0]["content"][1]["image_url"]["url"] == "https://example.org/fig.jpg"
    assert executor.call("describe_image", {"image": "nope.png"}).error == "no image file 'nope.png'"


def test_the_tools_need_an_api_key(monkeypatch, executor):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert "DEEPSEEK_API_KEY" in executor.call("web_search", {"query": "NaCl"}).error
