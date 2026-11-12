"""Terminal front ends of the agent: plain ``input()``, or prompt_toolkit with history and completion."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .repl import ReplController

__all__ = ["PlainTerminal", "PromptToolkitTerminal", "create_terminal", "format_event", "markdown_printer"]

BANNER = "MatSimPy AI. Type a request, /help for commands, /quit to exit."


def format_event(event: str, data: dict) -> str | None:
    """One progress line for an agent event (``on_event``)."""
    if event == "tool_call":
        arguments = json.dumps(data["arguments"], ensure_ascii=False)
        return f"  → {data['name']} {arguments if len(arguments) < 160 else arguments[:157] + '...'}"
    if event == "tool_result" and not data["ok"]:
        return f"  ✗ {data['name']}: {data['result'].get('error', '')[:200]}"
    if event == "warning":
        return f"  ! {data['message']}"
    return None


def markdown_printer(stream=None, *, markdown: bool | None = None) -> Callable[[str], None]:
    """A function that prints the model's Markdown answers to ``stream`` (default stdout).

    The Markdown is rendered with rich when ``markdown`` is true, or by default when the
    stream is a terminal and rich is installed. Otherwise the Markdown source is printed,
    so piped output stays plain text.
    """
    stream = stream or sys.stdout
    if markdown is None:
        markdown = hasattr(stream, "isatty") and stream.isatty()
    if markdown:
        try:
            from rich.console import Console
            from rich.markdown import Markdown
        except ImportError:
            pass
        else:
            console = Console(file=stream)
            return lambda text: console.print(Markdown(text))
    return lambda text: print(text, file=stream)


class PlainTerminal:
    """Read requests and commands with ``input()``; needs only the standard library."""

    def __init__(
        self,
        controller: ReplController,
        *,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], Any] | None = None,
        markdown: bool | None = None,
    ) -> None:
        """``markdown``: render answers as Markdown (default: when stdout is a terminal).
        A custom ``output_writer`` receives every line, answers included, as plain text."""
        self.controller = controller
        self.read = input_reader
        self.write = output_writer or print
        self._render = markdown_printer(markdown=markdown) if output_writer is None else self.write

    def run(self) -> None:
        self.write(BANNER)
        while True:
            try:
                line = self.read("\n› ").strip()
            except EOFError:
                self.write("Goodbye.")
                return
            except KeyboardInterrupt:
                self.write("(Ctrl+D or /quit exits)")
                continue
            if not line:
                continue
            try:
                if self.handle(line):
                    return
            except KeyboardInterrupt:
                self.write("Cancelled; the turn was discarded.")

    def handle(self, line: str) -> bool:
        """Run one line; returns True when the user asked to exit."""
        if line.startswith("/"):
            result = self.controller.execute(line)
            self.write(result.text if result.ok else f"! {result.text}")
            return result.exit
        result = self.controller.agent.run(line)
        if result.status == "error":
            self.write(f"! {result.response}")
        else:
            self.render(result.response)
        return False

    def render(self, text: str) -> None:
        self._render(text)


class PromptToolkitTerminal(PlainTerminal):
    """History, completion of commands, and Markdown output (with rich, if installed)."""

    def __init__(self, controller: ReplController, *, history_path: str | Path | None = None,
                 markdown: bool | None = None, **session_options):
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.history import FileHistory

        path = Path(history_path or Path.home() / ".matsimpy" / "ai_history")
        path.parent.mkdir(parents=True, exist_ok=True)
        words = list(controller.command_names()) + [s.name for s in controller.agent.skills.discover()]
        self.prompt_session = PromptSession(
            history=FileHistory(str(path)),
            completer=WordCompleter(words, sentence=True),
            bottom_toolbar=lambda: f" session {controller.agent.session.id} | {controller.agent.provider.model} ",
            **session_options,
        )
        super().__init__(controller, input_reader=self.prompt_session.prompt, markdown=markdown)


def create_terminal(controller: ReplController, *, markdown: bool | None = None) -> PlainTerminal:
    """prompt_toolkit if it is installed, else the plain terminal."""
    try:
        return PromptToolkitTerminal(controller, markdown=markdown)
    except ImportError:
        return PlainTerminal(controller, markdown=markdown)
