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
            warnings.filterwarnings("ignore", message="A NumPy version.*")
            from matsimpy.storage import DataStorage, MemoryBackend
            assert not caught, [str(w.message) for w in caught]

        # MemoryBackend works without maggma
        storage = DataStorage(backend=MemoryBackend())
        assert storage.store_data({"test": 1})
        storage.close()

        # Default DataStorage() works without maggma
        storage2 = DataStorage()
        assert storage2.store_data({"test": 2})
        storage2.close()

        # MaggmaBackend requires maggma
        from matsimpy.storage.maggma_store import MaggmaBackend
        try:
            MaggmaBackend(use_memory_store=True)
        except ImportError as exc:
            assert "maggma is required" in str(exc)
        else:
            raise AssertionError("MaggmaBackend should require maggma")
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_core_runtime_imports_without_ase_or_pymatgen():
    script = textwrap.dedent(
        """
        import builtins

        blocked = {"ase", "pymatgen"}
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and (name in blocked or any(name.startswith(pkg + ".") for pkg in blocked)):
                raise ModuleNotFoundError(f"blocked optional dependency: {name}", name=name)
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import

        import matsimpy
        import matsimpy.core
        import matsimpy.builders
        import matsimpy.calculator

        assert matsimpy.Crystal is not None
        assert matsimpy.calculator.LennardJones is not None
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_calculator_import_without_ml_optional_dependencies():
    script = textwrap.dedent(
        """
        import builtins

        blocked = {"torch", "torch_geometric", "mattersim"}
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and (name in blocked or any(name.startswith(pkg + ".") for pkg in blocked)):
                raise ModuleNotFoundError(f"blocked optional dependency: {name}", name=name)
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import

        from matsimpy.calculator import LennardJones, Mattersim
        from matsimpy.calculator.ml import Mattersim as MLMattersim

        assert LennardJones is not None
        assert Mattersim is MLMattersim
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert result.returncode == 0, result.stdout + result.stderr
