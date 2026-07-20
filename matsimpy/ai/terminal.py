"""Interactive and dependency-free terminal frontends for the agent REPL."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

from .repl import CommandResult, ReplController


class TerminalFrontend(ABC):
    """Terminal interface over a :class:`ReplController`."""

    def __init__(self, controller: ReplController) -> None:
        self.controller = controller

    @abstractmethod
    def run(self) -> None:
        """Read and execute input until the user exits."""


class PlainTerminal(TerminalFrontend):
    """Portable terminal requiring only the Python standard library."""

    def __init__(
        self,
        controller: ReplController,
        *,
        input_reader: Callable[[str], str] | None = None,
        output_writer: Callable[[str], Any] | None = None,
    ) -> None:
        super().__init__(controller)
        self._input = input_reader or input
        self._output = output_writer or print

    def run(self) -> None:
        self._output("MatSimPy AI — /skills lists skills, /quit exits")
        while True:
            try:
                text = self._input("\n👤 › ").strip()
            except EOFError:
                self._output("Goodbye.")
                return
            except KeyboardInterrupt:
                self._output("Cancelled. Enter another request or /quit.")
                continue
            if not text:
                continue
            try:
                if self._execute(text):
                    return
            except KeyboardInterrupt:
                self._output("Cancelled current turn.")
            except Exception as exc:
                self._output(f"Error: {exc}")

    def _execute(self, text: str) -> bool:
        if text.startswith("/"):
            result = self.controller.execute(text)
            self.render_command(result)
            return result.exit_requested
        turn = self.controller.session.run(text)
        self.render_response(turn.final_response)
        return False

    def render_response(self, response: str) -> None:
        """Render an LLM response as safe plain text."""
        self._output(response)

    def render_command(self, result: CommandResult) -> None:
        """Render the controller's concise display text."""
        if result.display_hint:
            self._output(result.display_hint)


class PromptToolkitTerminal(PlainTerminal):
    """Enhanced terminal with history, multiline editing, and completion."""

    def __init__(
        self,
        controller: ReplController,
        *,
        history_path: str | Path | None = None,
        output_writer: Callable[[str], Any] | None = None,
        input: Any | None = None,
        output: Any | None = None,
    ) -> None:
        # All optional imports deliberately remain inside construction.
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.key_binding import KeyBindings

        markdown_output = output_writer
        if output_writer is None:
            try:
                from rich.console import Console
                from rich.markdown import Markdown

                console = Console(markup=False)
                output_writer = console.print

                def markdown_output(text: str) -> None:
                    console.print(Markdown(text))
            except ImportError:
                output_writer = print
                markdown_output = output_writer

        terminal = self

        class AgentCompleter(Completer):
            def get_completions(self, document, complete_event):
                word = document.get_word_before_cursor()
                for candidate in terminal.completion_candidates(word):
                    yield Completion(candidate, start_position=-len(word))

        path = Path(history_path or Path.home() / ".matsimpy" / "ai_history")
        path.parent.mkdir(parents=True, exist_ok=True)
        bindings = KeyBindings()

        @bindings.add("c-m", eager=True)
        def _submit(event) -> None:
            event.current_buffer.validate_and_handle()

        @bindings.add("escape", "c-m", eager=True)
        def _insert_newline(event) -> None:
            event.current_buffer.insert_text("\n")

        session_options = {
            "history": FileHistory(str(path)),
            "completer": AgentCompleter(),
            "multiline": True,
            "key_bindings": bindings,
            "bottom_toolbar": self.bottom_toolbar,
        }
        if input is not None:
            session_options["input"] = input
        if output is not None:
            session_options["output"] = output
        self.prompt_session = PromptSession(**session_options)
        super().__init__(
            controller,
            input_reader=lambda prompt: self.prompt_session.prompt(prompt),
            output_writer=output_writer,
        )
        self._markdown_output = markdown_output or self._output

    def render_response(self, response: str) -> None:
        """Render an LLM response as Markdown when Rich is available."""
        self._markdown_output(response)

    def completion_candidates(self, prefix: str) -> tuple[str, ...]:
        """Return slash-command and skill-name completion candidates."""
        candidates: set[str] = set(self.controller.command_names())
        library = getattr(self.controller, "skill_library", None)
        if library is not None:
            for skill in library.discover():
                name = (
                    skill.get("name")
                    if isinstance(skill, dict)
                    else getattr(skill, "name", None)
                )
                if name:
                    candidates.add(str(name))
        folded = prefix.casefold()
        return tuple(
            sorted(item for item in candidates if item.casefold().startswith(folded))
        )

    def bottom_toolbar(self) -> str:
        """Show the active durable session without performing I/O."""
        session_id = getattr(self.controller.session, "conversation_id", None)
        return f" session {session_id or 'new'} | Enter submit | Esc+Enter newline | Ctrl+C cancel "


def _prompt_toolkit_available() -> bool:
    try:
        import prompt_toolkit  # noqa: F401
    except ImportError:
        return False
    return True


def create_terminal(controller: ReplController) -> TerminalFrontend:
    """Create the best installed frontend, falling back without error."""
    if _prompt_toolkit_available():
        try:
            return PromptToolkitTerminal(controller)
        except ImportError:
            pass
    return PlainTerminal(controller)


__all__ = [
    "PlainTerminal",
    "PromptToolkitTerminal",
    "TerminalFrontend",
    "create_terminal",
]
