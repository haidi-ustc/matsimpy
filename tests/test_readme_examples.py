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


# All README blocks run in ONE child interpreter (each block with fresh globals,
# a fresh working directory and a fresh config singleton).  0.8.2 started one
# interpreter per block, which made this file ~1/3 of the whole suite's runtime.
_RUNNER = r"""
import json, os, sys, tempfile, traceback
blocks = json.load(sys.stdin)
results = []
for code in blocks:
    cwd = tempfile.mkdtemp(prefix="readme-block-")
    os.chdir(cwd)
    try:
        import matsimpy.config.manager as _m
        _m._global_config = None
    except Exception:
        pass
    try:
        exec(compile(code, "<README block>", "exec"), {"__name__": "__main__"})
        results.append(None)
    except BaseException:
        results.append(traceback.format_exc())
print("@@RESULTS@@" + json.dumps(results))
"""


@pytest.fixture(scope="module")
def readme_results(tmp_path_factory):
    blocks = _python_examples()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-c", _RUNNER],
        input=__import__("json").dumps(blocks),
        cwd=tmp_path_factory.mktemp("readme"),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    marker = proc.stdout.rfind("@@RESULTS@@")
    assert marker >= 0, proc.stderr
    return dict(zip(blocks, __import__("json").loads(proc.stdout[marker + len("@@RESULTS@@"):])))


@pytest.mark.parametrize("code", _python_examples())
def test_readme_python_example_executes(code, readme_results):
    """Each ordinary Python fence is a complete, offline example."""
    assert readme_results[code] is None, readme_results[code]


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
