"""Public API contract tests for matsimpy.io."""

import importlib.util
import importlib
import os
from pathlib import Path
import sys
import textwrap
import subprocess


def test_io_exports_unified_public_api():
    import matsimpy.io as io

    expected = {
        "read",
        "write",
        "read_file",
        "write_file",
        "to_ase",
        "from_ase",
        "to_pymatgen",
        "from_pymatgen",
        "crystals_to_latex_table",
        "molecules_to_latex_table",
        "structures_to_latex_table",
        "save_latex_table",
    }
    assert expected <= set(io.__all__)
    for name in expected:
        assert hasattr(io, name)


def test_removed_public_packages_are_not_importable():
    for module_name in ("matsimpy.adapters", "matsimpy.export"):
        for cached in list(sys.modules):
            if cached == module_name or cached.startswith(f"{module_name}."):
                sys.modules.pop(cached)
        assert importlib.util.find_spec(module_name) is None


def test_no_runtime_imports_from_removed_adapter_or_export_packages():
    repo_root = Path(__file__).resolve().parents[2]
    root = repo_root / "matsimpy"
    removed_imports = (
        "matsimpy.adapters",
        "..adapters",
        "...adapters",
        "matsimpy.export",
        "..export",
        "...export",
    )
    scanned = []
    offenders = []
    for path in root.rglob("*.py"):
        if "adapters" in path.parts or "export" in path.parts:
            continue
        scanned.append(path)
        text = path.read_text(encoding="utf-8")
        for reference in removed_imports:
            if reference in text:
                offenders.append(f"{path}: {reference}")

    assert scanned
    assert offenders == []


def test_io_reimport_after_module_cache_clear_is_idempotent():
    import matsimpy.io

    original_modules = {
        cached: module
        for cached, module in sys.modules.items()
        if cached == "matsimpy.io" or cached.startswith("matsimpy.io.")
    }
    try:
        for cached in original_modules:
            if cached != "matsimpy.io.registry":
                sys.modules.pop(cached, None)

        reimported = importlib.import_module("matsimpy.io")
        assert "to_ase" in reimported.__all__
    finally:
        for cached in list(sys.modules):
            if cached == "matsimpy.io" or cached.startswith("matsimpy.io."):
                sys.modules.pop(cached)
        sys.modules.update(original_modules)


def test_io_errors_import_keeps_pymatgen_converters_callable_when_dependency_is_blocked(tmp_path):
    blocker = tmp_path / "sitecustomize.py"
    blocker.write_text(textwrap.dedent("""
        import builtins
        real_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name == "pymatgen" or name.startswith("pymatgen."):
                raise ImportError("blocked optional pymatgen")
            return real_import(name, *args, **kwargs)
        builtins.__import__ = guarded
    """))
    code = textwrap.dedent("""
        from matsimpy.io.errors import ParseError
        from matsimpy.io import from_pymatgen, to_pymatgen
        assert issubclass(ParseError, ValueError)
        assert callable(to_pymatgen)
        assert callable(from_pymatgen)
        try:
            from_pymatgen(object())
        except ImportError as exc:
            assert "pymatgen is required for conversion" in str(exc)
        else:
            raise AssertionError("missing pymatgen did not raise ImportError")
    """)
    repo_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": f"{tmp_path}{os.pathsep}{repo_root}"}
    result = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
