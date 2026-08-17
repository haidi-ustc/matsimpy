"""Packaging and runtime contract tests that unit tests do not otherwise cover."""

import subprocess
import sys
import textwrap
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]


def _read_pyproject():
    if tomllib is None:
        raise RuntimeError("tomllib is required for packaging contract tests")
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


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


def test_package_version_is_single_sourced_in_readme_and_import():
    pyproject = _read_pyproject()
    expected_version = pyproject["project"]["version"]
    readme = (ROOT / "README.md").read_text()

    import matsimpy

    assert matsimpy.__version__ == expected_version
    assert f"**Version**: v{expected_version}" in readme
    assert "v0.5.0" not in readme
    assert "v0.6.0" not in readme


def test_license_metadata_and_readme_use_mit():
    pyproject = _read_pyproject()
    readme = (ROOT / "README.md").read_text()
    license_text = (ROOT / "LICENSE").read_text()

    assert "License :: OSI Approved :: MIT License" in pyproject["project"]["classifiers"]
    assert "MIT License" in license_text
    assert "Permission is hereby granted, free of charge" in license_text
    assert "Redistribution and use in source and binary forms" not in license_text
    assert "licensed under the MIT License" in readme


def test_readme_and_config_do_not_advertise_quantum_espresso():
    readme = (ROOT / "README.md").read_text()
    defaults = (ROOT / "matsimpy" / "config" / "defaults.py").read_text()

    assert "Quantum Espresso" not in readme
    assert "QE" not in readme
    assert "quantum_espresso" not in defaults


def test_console_scripts_keep_ai_repl_optional():
    pyproject = _read_pyproject()
    scripts = pyproject["project"]["scripts"]
    optional = pyproject["project"]["optional-dependencies"]

    assert scripts == {"matsimpy-ai": "matsimpy.ai.cli:app"}
    assert "ai" in optional
    assert "typer" in optional["ai"]
    assert "requests" in optional["ai"]
    assert "cli" not in optional


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
        check=False,
        cwd=ROOT,
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
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_vasp_runtime_imports_without_undeclared_dependencies(tmp_path):
    target = tmp_path / "site"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    install = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--quiet",
            "--target",
            str(target),
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=run_dir,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    script = textwrap.dedent("""
        import builtins
        import importlib.resources
        import pathlib
        import sys

        target = pathlib.Path(sys.argv[1]).resolve()
        blocked = {"ase", "orjson", "pymatgen", "tqdm"}
        real_import = builtins.__import__
        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and (name in blocked or any(name.startswith(pkg + ".") for pkg in blocked)):
                raise ModuleNotFoundError(f"blocked optional dependency: {name}", name=name)
            return real_import(name, globals, locals, fromlist, level)
        builtins.__import__ = guarded_import

        import matsimpy.calculator.vasp as vasp
        import matsimpy.calculator.vasp.inputs
        import matsimpy.calculator.vasp.outputs
        import matsimpy.calculator.vasp.sets
        assert pathlib.Path(vasp.__file__).resolve().is_relative_to(target)
        assert vasp.Incar is not None
        assert matsimpy.calculator.vasp.inputs.Poscar is not None
        assert matsimpy.calculator.vasp.outputs.Vasprun is not None
        assert matsimpy.calculator.vasp.sets.DictSet is not None

        resources = importlib.resources.files("matsimpy.calculator.vasp")
        required = {
            "incar_parameters.json",
            "vasp_potcar_file_hashes.json",
            "vasp_potcar_pymatgen_hashes.json",
            "vasp_potcar_stats.json",
            "VASPIncarBase.yaml",
            "MPRelaxSet.yaml",
            "PBE54Base.yaml",
            "PBE64Base.yaml",
            "vdW_parameters.yaml",
        }
        missing = sorted(name for name in required if not (resources / name).is_file())
        assert missing == []
    """)
    result = subprocess.run(
        [sys.executable, "-c", script, str(target)],
        capture_output=True, text=True,
        check=False,
        cwd=run_dir,
        env={"PYTHONPATH": str(target)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
