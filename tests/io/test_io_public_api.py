"""Public API contract tests for matsimpy.io."""

import importlib.util
from pathlib import Path
import sys


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
    removed_imports = (
        "matsimpy.adapters",
        "..adapters",
        "...adapters",
        "matsimpy.export",
        "..export",
        "...export",
    )
    offenders = []
    for path in Path("matsimpy").glob("**/*.py"):
        if any("adapters" in part or "export" in part for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for reference in removed_imports:
            if reference in text:
                offenders.append(f"{path}: {reference}")

    assert offenders == []
