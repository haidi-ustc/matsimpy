"""The sdist must carry the assets the test-suite needs.

The 0.8.5-0.9.0 sdists were built from a tree without tests/calculator/fixtures,
so 25 real-file VASP/Gaussian tests were skipped in every later checkout.
"""

import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "CHANGELOG.md",
    "MIGRATION_0.9.md",
    "tests/calculator/fixtures/vasp/vasprun.xml",
    "tests/calculator/fixtures/vasp/OUTCAR",
    "tests/calculator/fixtures/gaussian/methane.log",
    "matsimpy/calculator/vasp/MPRelaxSet.yaml",
    "matsimpy/calculator/vasp/vasp_potcar_stats.json",
    "matsimpy/calculator/vasp/vdW_parameters.yaml",
]


@pytest.mark.skipif(not (ROOT / "pyproject.toml").is_file(), reason="not a source checkout")
def test_sdist_contains_test_fixtures_and_package_data(tmp_path):
    for rel in REQUIRED:
        assert (ROOT / rel).is_file(), f"missing from the source tree: {rel}"

    build = (
        "import sys; from setuptools import build_meta; "
        "print(build_meta.build_sdist(sys.argv[1]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", build, str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    archive = tmp_path / result.stdout.strip().splitlines()[-1]

    with tarfile.open(archive) as tar:
        members = {name.split("/", 1)[1] for name in tar.getnames() if "/" in name}
    missing = [rel for rel in REQUIRED if rel not in members]
    assert not missing, f"sdist is missing: {missing}"
