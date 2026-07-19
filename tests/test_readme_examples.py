"""Executable contracts for Python examples published in README.md."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PYTHON_BLOCK = re.compile(
    r"^```python\s*\n(?P<code>.*?)^```$",
    flags=re.MULTILINE | re.DOTALL,
)
PYTHON_NOTEST_BLOCK = re.compile(
    r"^```python notest\s*\n(?P<code>.*?)^```$",
    flags=re.MULTILINE | re.DOTALL,
)
BASH_BLOCK = re.compile(
    r"^```bash\s*\n(?P<code>.*?)^```$",
    flags=re.MULTILINE | re.DOTALL,
)


def _python_examples():
    text = README.read_text()
    return [match.group("code") for match in PYTHON_BLOCK.finditer(text)]


def _blocks(pattern):
    return [match.group("code") for match in pattern.finditer(README.read_text())]


@pytest.mark.parametrize("code", _python_examples())
def test_readme_python_example_executes(code, tmp_path):
    """Each ordinary Python fence is a complete, offline example."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_readme_has_executable_python_examples():
    assert _python_examples(), "README must contain executable Python examples"


@pytest.mark.parametrize("code", _blocks(PYTHON_NOTEST_BLOCK))
def test_file_dependent_python_example_compiles(code):
    compile(code, str(README), "exec")


@pytest.mark.parametrize("code", _blocks(BASH_BLOCK))
def test_readme_shell_example_has_valid_syntax(code):
    result = subprocess.run(
        ["bash", "-n"],
        input=code,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
