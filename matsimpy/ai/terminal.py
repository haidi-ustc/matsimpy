"""Terminal front ends of the agent: plain ``input()``, or prompt_toolkit with history and completion."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .repl import ReplController

__all__ = ["PlainTerminal", "PromptToolkitTerminal", "create_terminal", "format_event"]

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


class PlainTerminal:
    """Read requests and commands with ``input()``; needs only the standard library."""

    def __init__(
        self,
        controller: ReplController,
        *,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], Any] = print,
    ) -> None:
        self.controller = controller
        self.read = input_reader
        self.write = output_writer

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
        self.write(text)


class PromptToolkitTerminal(PlainTerminal):
    """History, completion of commands, and Markdown output (with rich, if installed)."""

    def __init__(self, controller: ReplController, *, history_path: str | Path | None = None, **session_options):
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
        super().__init__(controller, input_reader=self.prompt_session.prompt)
        try:
            from rich.console import Console
            from rich.markdown import Markdown

            console = Console()
            self._markdown = lambda text: console.print(Markdown(text))
        except ImportError:
            self._markdown = print

    def render(self, text: str) -> None:
        self._markdown(text)


def create_terminal(controller: ReplController) -> PlainTerminal:
    """prompt_toolkit if it is installed, else the plain terminal."""
    try:
        return PromptToolkitTerminal(controller)
    except ImportError:
        return PlainTerminal(controller)
