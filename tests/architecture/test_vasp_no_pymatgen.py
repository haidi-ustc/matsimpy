import ast
from pathlib import Path

import pytest


VASP_DIR = Path(__file__).parents[2] / "matsimpy" / "calculator" / "vasp"


@pytest.mark.xfail(strict=True, reason="migration characterization: remove in Task 9")
def test_vasp_production_modules_do_not_import_pymatgen():
    violations = []
    for path in VASP_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name == "pymatgen" or name.startswith("pymatgen.") for name in names):
                violations.append(f"{path.name}:{node.lineno}")
    assert violations == []


def test_vasp_imports_when_pymatgen_is_blocked(tmp_path):
    import os
    import subprocess
    import sys

    blocker = tmp_path / "sitecustomize.py"
    blocker.write_text(
        "import builtins\n"
        "_real = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name == 'pymatgen' or name.startswith('pymatgen.'):\n"
        "        raise ImportError('blocked by architecture test')\n"
        "    return _real(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n"
    )
    code = (
        "import matsimpy.calculator.vasp.inputs; "
        "import matsimpy.calculator.vasp.outputs; "
        "import matsimpy.calculator.vasp.sets"
    )
    env = {**os.environ, "PYTHONPATH": f"{tmp_path}{os.pathsep}{os.getcwd()}"}
    result = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
