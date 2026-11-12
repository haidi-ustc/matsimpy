"""Every script in examples/ runs cleanly.

The examples catch exceptions to keep going, so a zero exit code is not enough: a
printed error, a failed check mark or a warning also fails the test. Missing optional
packages (reported with "Install with" or "not installed") are allowed.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted(p.name for p in (ROOT / "examples").glob("*.py") if p.name != "__init__.py")
PROBLEM = re.compile(r"Traceback|Warning:|✗|\bError\b|\bFailed\b")
OPTIONAL = re.compile(r"Install with|not installed|required for", re.IGNORECASE)


def _run(args, tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT), "HOME": str(tmp_path), "TMPDIR": str(tmp_path)}
    env.pop("DEEPSEEK_API_KEY", None)
    done = subprocess.run([sys.executable, *args], cwd=tmp_path, env=env, capture_output=True,
                          text=True, timeout=300)
    problems = [line for line in (done.stdout + done.stderr).splitlines()
                if PROBLEM.search(line) and not OPTIONAL.search(line)]
    assert done.returncode == 0 and not problems, problems or done.stderr[-2000:]
    return done.stdout


@pytest.mark.skipif(not EXAMPLES, reason="repository asset not available: examples/")
@pytest.mark.parametrize("name", EXAMPLES)
def test_example_runs(name, tmp_path):
    _run([str(ROOT / "examples" / name)], tmp_path)


def test_ai_extending_example_runs_offline(tmp_path):
    if not (ROOT / "examples" / "ai" / "extending.py").exists():
        pytest.skip("repository asset not available: examples/ai")
    pytest.importorskip("typer")
    pytest.importorskip("requests")
    output = _run(["-m", "examples.ai.extending"], tmp_path)
    assert "cubic_supercell_matrix -> [4, 4, 4]" in output
    assert "from_prototype over MCP -> Fe" in output
    assert "success: Built NaCl." in output
