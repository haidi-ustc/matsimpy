"""Agent tools backed by DeepSeek's tool APIs: web search, page fetch, OCR and vision.

* ``web_search`` and ``fetch_url`` call the Search & Fetch APIs
  (https://api-docs.deepseek.com/guides/search/).  They are ordinary function tools,
  so they work with any chat model, and every call is visible in the session.
  (DeepSeek's server-side "web tools" are not used: they run only on
  ``deepseek-flash`` and cannot be declared next to function tools.)
* ``ocr_document`` calls the OCR API (https://api-docs.deepseek.com/guides/ocr) for a
  PDF, Word, PowerPoint or image file in the workspace.
* ``describe_image`` sends an image to the vision model ``deepseek-flash``
  (https://api-docs.deepseek.com/guides/vision), so the agent can read a figure
  even when its own model (``deepseek-v4-pro``) takes no images.

All four need ``DEEPSEEK_API_KEY`` and are billed by DeepSeek (search and fetch per
request, OCR per page, vision per token).  ``$MATSIMPY_DEEPSEEK_TOOLS_URL`` replaces the
API root ``https://api.deepseek.com``.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from ..utils.tooling import tool
from .provider import DEFAULT_BASE_URL, post_with_retries
from .tools import ToolContext, ToolError

__all__ = ["describe_image", "fetch_url", "ocr_document", "web_search"]

VISION_MODEL = "deepseek-flash"
OCR_PURPOSES = {False: "text_recognition", True: "rich_layout_recognition"}
MAX_IMAGE_BYTES = 32 * 1024 * 1024  # the vision guide's limit for one image
MAX_OCR_BYTES = 100 * 1024 * 1024
# layout tokens of recognized pages, as the API returns them: a block label and its box
# before the block's text, e.g. "<｜ref｜>text<｜/ref｜><｜box｜>[[42,305,415,394]]<｜/box｜> NaCl"
_LAYOUT = re.compile(r"<｜ref｜>.*?<｜/ref｜>|<｜box｜>.*?<｜/box｜>", re.S)
_TAG = re.compile(r"<｜/?[a-z_]+｜>")


def _api_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ToolError("this tool needs a DeepSeek API key: set DEEPSEEK_API_KEY")
    return key


def _url(path: str) -> str:
    root = (os.getenv("MATSIMPY_DEEPSEEK_TOOLS_URL") or DEFAULT_BASE_URL).rstrip("/")
    return f"{root}{path}"


def _post(path: str, *, timeout: float, **kwargs: Any) -> dict:
    response = post_with_retries(_url(path), headers={"Authorization": f"Bearer {_api_key()}"},
                                 timeout=timeout, **kwargs)
    data = response.json()
    if isinstance(data, dict) and "error" in data:  # OCR reports late failures with status 200
        error = data["error"]
        raise ToolError(error.get("message", str(error)) if isinstance(error, dict) else str(error))
    return data


def _clip(text: str, limit: int) -> tuple[str, bool]:
    return (text, False) if len(text) <= limit else (text[:limit], True)


@tool
def web_search(query: str, count: int = 5, full_content: bool = False) -> dict[str, Any]:
    """Search the web and return the best results with their URLs.

    Use it for facts no other tool provides, e.g. experimental lattice constants or
    recent papers, and cite the URLs you use.  Operators work in the query:
    site:materialsproject.org, -term, a phrase in double quotes, lang:en, after:2024.

    Args:
        query: Search query, at most 128 characters.
        count: Number of results (1 to 50).
        full_content: Also return each page's text (up to 3000 characters per result).
    """
    if not query.strip() or len(query) > 128:
        raise ToolError("query must have 1 to 128 characters")
    if not 1 <= count <= 50:
        raise ToolError("count must be between 1 and 50")
    data = _post("/v1/tools/search", timeout=60,
                 json={"query": query, "count": count, "need_content": full_content})
    results = []
    for item in data.get("results", []):
        result = {key: item.get(key) for key in ("title", "url", "date", "site_name")}
        result["summary"] = item.get("summary") or item.get("snippet") or ""
        if full_content and item.get("content"):
            result["content"], _ = _clip(item["content"], 3000)
        results.append(result)
    return {"query": query, "results": results}


@tool
def fetch_url(url: str, max_chars: int = 12000) -> dict[str, Any]:
    """Read a web page as Markdown, e.g. a result of web_search.

    Args:
        url: http or https URL.
        max_chars: Most characters of the page to return.
    """
    if not url.startswith(("http://", "https://")):
        raise ToolError("url must start with http:// or https://")
    data = _post("/v1/tools/fetch", timeout=120, json={"url": url})
    content, truncated = _clip(data.get("content") or "", max_chars)
    return {"url": url, "title": data.get("title"), "content": content, "truncated": truncated}


def clean_ocr_text(text: str) -> str:
    """OCR page text without layout tokens and their bounding boxes."""
    lines = _TAG.sub("", _LAYOUT.sub("", text)).splitlines()
    return "\n".join(line.strip() for line in lines).strip()


@tool(paths=("path", "output"))
def ocr_document(path: str, output: str | None = None, layout: bool = False,
                 max_chars: int = 15000) -> dict[str, Any]:
    """Recognize the text of a PDF, Word, PowerPoint or image file (OCR).

    Long documents: give ``output`` to save the full text as a file and get a preview.

    Args:
        path: Document in the workspace (PDF, DOC/DOCX, PPT/PPTX, PNG, JPEG, WebP, GIF,
            BMP or TIFF; at most 100 MiB and 1000 pages).
        output: Text file to write the recognized text to, page by page.
        layout: Keep layout tokens with bounding boxes ([[x1, y1, x2, y2]] on a 0-1000
            grid) for tables and figures; by default plain text is returned.
        max_chars: Most characters of text to return.
    """
    source = Path(path)
    if not source.is_file():
        raise ToolError(f"the file {path!r} does not exist")
    if source.stat().st_size > MAX_OCR_BYTES:
        raise ToolError(f"{source.name} is larger than 100 MiB")
    with source.open("rb") as handle:
        # recognition is billed even if the client disconnects: retry only refusals, not timeouts
        data = _post("/v1/tools/ocr", timeout=300, max_retries=1, retry_timeouts=False,
                     data={"purpose": OCR_PURPOSES[layout]}, files={"file": (source.name, handle)})
    pages = sorted(data.get("pages", []), key=lambda page: page.get("index", 0))
    texts = [page.get("text", "") if layout else clean_ocr_text(page.get("text", "")) for page in pages]
    incomplete = [page.get("index", i) + 1 for i, page in enumerate(pages) if page.get("finish_reason") == "length"]
    text = "\n\n".join(f"--- page {i} ---\n{body}" for i, body in enumerate(texts, start=1))
    result: dict[str, Any] = {"file": source.name, "page_count": data.get("page_count", len(pages))}
    if incomplete:
        result["incomplete_pages"] = incomplete
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
        result["output"] = Path(output).name
    result["text"], result["truncated"] = _clip(text, max_chars)
    return result


@tool
def describe_image(image: str, context: ToolContext,
                   question: str = "Describe this image in detail.") -> dict[str, Any]:
    """Ask the vision model about an image: a figure, a plot, a crystal-structure drawing.

    Args:
        image: Image file in the workspace (PNG, JPEG, GIF or WebP) or an http(s) URL.
        question: What to find out, e.g. "Read the lattice constants from this table."
    """
    if image.startswith(("http://", "https://")):
        url = image
    else:
        path = context.executor.path(image)
        if not path.is_file():
            raise ToolError(f"no image file {image!r}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ToolError(f"{path.name} is larger than 32 MiB")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"  # the API detects the real format
        url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
    data = _post("/chat/completions", timeout=180, json={"model": VISION_MODEL, "messages": [{
        "role": "user",
        "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": url}}],
    }]})
    message = data["choices"][0]["message"]
    return {"image": image, "model": data.get("model", VISION_MODEL), "answer": message.get("content") or ""}
