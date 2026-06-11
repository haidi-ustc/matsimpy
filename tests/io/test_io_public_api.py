"""Public API contract tests for matsimpy.io."""

import importlib.util
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
