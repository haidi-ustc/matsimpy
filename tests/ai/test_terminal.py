"""Terminal frontends for the data-returning REPL controller."""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

from matsimpy.ai.repl import CommandResult


class FakeTurn:
    final_response = "built copper"


class FakeSession:
    conversation_id = 17

    def __init__(self):
        self.requests = []

    def run(self, text):
        self.requests.append(text)
        return FakeTurn()


class FakeSkills:
    def discover(self):
        return [{"name": "crystals"}, {"name": "molecules"}]


class FakeController:
    def __init__(self):
        self.session = FakeSession()
        self.skill_library = FakeSkills()
        self.commands = []

    def execute(self, text):
        self.commands.append(text)
        return CommandResult(
            "quit" if text == "/quit" else "command",
            display_hint="Goodbye." if text == "/quit" else "command done",
            exit_requested=text == "/quit",
        )

    def command_names(self):
        return ("/quit", "/skills", "/resume")


def test_importing_terminal_does_not_import_optional_ui_packages(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"prompt_toolkit", "rich"}:
            raise AssertionError(f"eager optional import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("matsimpy.ai.terminal", None)

    import matsimpy.ai.terminal  # noqa: F401


def test_terminal_frontends_are_public_ai_interfaces():
    from matsimpy.ai import PlainTerminal, TerminalFrontend, create_terminal

    assert issubclass(PlainTerminal, TerminalFrontend)
    assert callable(create_terminal)


def test_plain_terminal_accepts_text_and_slash_commands():
    from matsimpy.ai.terminal import PlainTerminal

    inputs = iter(["build copper", "/skills", "/quit"])
    output = []
    controller = FakeController()

    terminal = PlainTerminal(
        controller,
        input_reader=lambda _prompt: next(inputs),
        output_writer=output.append,
    )
    terminal.run()

    assert controller.session.requests == ["build copper"]
    assert controller.commands == ["/skills", "/quit"]
    assert "built copper" in output
    assert "command done" in output


def test_plain_terminal_ctrl_c_cancels_turn_and_continues():
    from matsimpy.ai.terminal import PlainTerminal

    controller = FakeController()
    calls = iter([KeyboardInterrupt(), "/quit"])

    def reader(_prompt):
        value = next(calls)
        if isinstance(value, BaseException):
            raise value
        return value

    output = []
    PlainTerminal(controller, input_reader=reader, output_writer=output.append).run()

    assert any("cancel" in line.lower() for line in output)
    assert controller.commands == ["/quit"]


def test_create_terminal_falls_back_when_prompt_toolkit_is_unavailable(monkeypatch):
    from matsimpy.ai import terminal

    monkeypatch.setattr(terminal, "_prompt_toolkit_available", lambda: False)

    assert isinstance(terminal.create_terminal(FakeController()), terminal.PlainTerminal)


def test_cli_interactive_mode_uses_terminal_frontend(monkeypatch):
    from typer.testing import CliRunner
    from matsimpy.ai import cli

    calls = []

    class SkillManager:
        def load(self, _name):
            pass

    class Engine:
        def __init__(self, **kwargs):
            self.skill_manager = SkillManager()
            self.repl_controller = FakeController()
            self.verbose = False

    class Terminal:
        def run(self):
            calls.append("run")

    monkeypatch.setattr(cli, "AIEngine", Engine)
    monkeypatch.setattr(cli, "_register_all_skills", lambda _manager: None)
    monkeypatch.setattr(cli, "create_terminal", lambda controller: Terminal(), raising=False)

    result = CliRunner().invoke(cli.app, [])

    assert result.exit_code == 0
    assert calls == ["run"]


def test_cli_command_mode_does_not_construct_interactive_terminal(monkeypatch):
    from typer.testing import CliRunner
    from matsimpy.ai import cli

    class SkillManager:
        def load(self, _name):
            pass

    class Engine:
        def __init__(self, **kwargs):
            self.skill_manager = SkillManager()
            self.verbose = False

        def chat(self, text):
            return f"answer: {text}"

    monkeypatch.setattr(cli, "AIEngine", Engine)
    monkeypatch.setattr(cli, "_register_all_skills", lambda _manager: None)
    monkeypatch.setattr(
        cli,
        "create_terminal",
        lambda _controller: pytest.fail("interactive frontend constructed"),
    )

    result = CliRunner().invoke(cli.app, ["-c", "build copper"])

    assert result.exit_code == 0
    assert "answer: build copper" in result.output


def test_cli_command_uses_default_workspace_when_workspace_is_omitted(
    monkeypatch, tmp_path
):
    from typer.testing import CliRunner

    from matsimpy.ai import cli
    from matsimpy.ai.conversation import ChatMessage, ChatResponse

    default_workspace = tmp_path / ".matsimpy" / "ai" / "workspace"
    monkeypatch.setattr(
        "matsimpy.ai.workspace.DEFAULT_WORKSPACE", default_workspace
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "offline-test-key")
    monkeypatch.setattr(
        "matsimpy.ai.provider.DeepSeekProvider.chat",
        lambda self, messages, tools=None, tool_choice="auto": ChatResponse(
            ChatMessage.assistant("OK"), [], "stop"
        ),
    )

    result = CliRunner().invoke(cli.app, ["-c", "Reply with exactly OK"])

    assert result.exit_code == 0
    assert result.output.rstrip().endswith("OK")
    assert (default_workspace / "ai-state.db").is_file()


@pytest.mark.requires_repl
@pytest.mark.pty
def test_prompt_toolkit_terminal_configures_history_multiline_and_completion(tmp_path):
    pytest.importorskip("prompt_toolkit")
    from matsimpy.ai.terminal import PromptToolkitTerminal

    controller = FakeController()
    history = tmp_path / "history"
    terminal = PromptToolkitTerminal(controller, history_path=history)

    assert terminal.prompt_session.multiline is True
    assert Path(terminal.prompt_session.history.filename) == history
    words = terminal.completion_candidates("/s")
    assert "/skills" in words
    assert "crystals" in terminal.completion_candidates("cr")
    assert "session 17" in terminal.bottom_toolbar()


@pytest.mark.requires_repl
@pytest.mark.pty
def test_prompt_toolkit_history_is_reused(tmp_path):
    pytest.importorskip("prompt_toolkit")
    from matsimpy.ai.terminal import PromptToolkitTerminal

    history = tmp_path / "history"
    first = PromptToolkitTerminal(FakeController(), history_path=history)
    first.prompt_session.history.append_string("build silicon")
    first.prompt_session.history.store_string("build silicon")

    second = PromptToolkitTerminal(FakeController(), history_path=history)
    assert "build silicon" in list(second.prompt_session.history.load_history_strings())


@pytest.mark.requires_repl
@pytest.mark.pty
def test_prompt_toolkit_pipe_input_submits_multiline_and_handles_interrupt(tmp_path):
    pytest.importorskip("prompt_toolkit")
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
    from matsimpy.ai.terminal import PromptToolkitTerminal

    controller = FakeController()
    rendered = []
    with create_pipe_input() as pipe:
        terminal = PromptToolkitTerminal(
            controller,
            history_path=tmp_path / "history",
            input=pipe,
            output=DummyOutput(),
            output_writer=rendered.append,
        )
        pipe.send_text("first line\x1b\rsecond line\r\x03/quit\r")
        terminal.run()

    assert controller.session.requests == ["first line\nsecond line"]
    assert controller.commands == ["/quit"]
    assert any("cancel" in item.lower() for item in rendered)
