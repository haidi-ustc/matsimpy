"""Packaging and runtime contract tests that unit tests do not otherwise cover."""

import builtins
import subprocess
import sys
import textwrap
from pathlib import Path


def test_config_import_is_base_dependency_safe():
    from matsimpy.config import ConfigManager

    assert ConfigManager is not None


def test_cli_entrypoint_missing_prompt_toolkit_is_actionable(monkeypatch, capsys):
    from matsimpy.ui.cli import __main__ as cli_main

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("prompt_toolkit"):
            raise ModuleNotFoundError("No module named 'prompt_toolkit'", name="prompt_toolkit")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    menu_path = Path(cli_main.__file__).parent / "matsimpy_menu.json"
    monkeypatch.setattr(sys, "argv", ["matsimpy", str(menu_path)])

    try:
        cli_main.main()
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("expected SystemExit")

    captured = capsys.readouterr()
    assert "MatSimPy[cli]" in captured.err


def test_workflow_files_do_not_reference_removed_entrypoints():
    workflow_text = "\n".join(
        path.read_text()
        for path in Path(".workflow").glob("*.yml")
    )

    assert "requirements.txt" not in workflow_text
    assert "python3 ./main.py" not in workflow_text


def test_storage_import_without_maggma_is_quiet_and_actionable():
    script = textwrap.dedent(
        """
        import builtins
        import warnings

        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "maggma" or name.startswith("maggma."):
                raise ImportError("blocked maggma")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = guarded_import

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from matsimpy.storage import DataStorage
            assert not caught, [str(w.message) for w in caught]

        try:
            DataStorage(use_memory_store=True)
        except ImportError as exc:
            assert "maggma is required" in str(exc)
            assert "MatSimPy[storage]" in str(exc)
        else:
            raise AssertionError("DataStorage should require maggma when invoked")
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert result.returncode == 0, result.stdout + result.stderr
