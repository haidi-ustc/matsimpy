"""Packaging and runtime contract tests that unit tests do not otherwise cover."""

import builtins
import subprocess
import sys
import textwrap
from pathlib import Path


def test_config_import_is_base_dependency_safe():
    from matsimpy.config import ConfigManager
    assert ConfigManager is not None


def test_workflow_files_do_not_reference_removed_entrypoints():
    workflow_text = "\n".join(
        path.read_text()
        for path in Path(".workflow").glob("*.yml")
    )
    assert "requirements.txt" not in workflow_text
    assert "python3 ./main.py" not in workflow_text


def test_storage_import_without_maggma_is_quiet_and_actionable():
    script = textwrap.dedent("""
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
        storage = DataStorage(backend=MemoryBackend())
        assert storage.store_data({"test": 1})
        storage.close()
        storage2 = DataStorage()
        assert storage2.store_data({"test": 2})
        storage2.close()
        from matsimpy.storage.maggma_store import MaggmaBackend
        try:
            MaggmaBackend(use_memory_store=True)
        except ImportError as exc:
            assert "maggma is required" in str(exc)
        else:
            raise AssertionError("MaggmaBackend should require maggma")
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_core_runtime_imports_without_ase_or_pymatgen():
    script = textwrap.dedent("""
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
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stdout + result.stderr
