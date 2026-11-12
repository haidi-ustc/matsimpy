"""
Pytest configuration file.

This file is automatically loaded by pytest and sets up the test environment.
It ensures the matsimpy package is importable by adding the parent directory
to sys.path. This eliminates the need for sys.path.insert in individual test files.
"""
import sys
import os
import shutil
import tempfile
import atexit

import pytest

# ---------------------------------------------------------------------------
# Test isolation: never touch the developer's real ~/.matsimpy.
# Must run before any `matsimpy` import, because several modules compute
# Path.home()-based constants at import time (ai.session_store, ai.memory, ...).
# 0.8.1 and earlier let the suite write ~/.matsimpy/config.yaml, which then
# broke test_get_config_function on the next run and changed the user's defaults.
# ---------------------------------------------------------------------------
_ISOLATED_HOME = tempfile.mkdtemp(prefix="matsimpy-test-home-")
os.environ["HOME"] = _ISOLATED_HOME
os.environ["USERPROFILE"] = _ISOLATED_HOME  # Windows
for _key in [k for k in os.environ if k.startswith("MATSIMPY_")]:
    del os.environ[_key]
atexit.register(shutil.rmtree, _ISOLATED_HOME, ignore_errors=True)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the parent directory to the path so matsimpy can be imported
# This is only needed if the package is not installed in development mode
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def has_torch():
    """Check if torch is installed."""
    try:
        import torch
        return True
    except ImportError:
        return False


def has_torch_geometric():
    """Check if torch_geometric is installed."""
    try:
        import torch_geometric
        return True
    except ImportError:
        return False


def has_ase():
    """Check if ase is installed."""
    try:
        import ase
        return True
    except ImportError:
        return False


def has_pymatgen():
    """Check if pymatgen is installed."""
    try:
        import pymatgen
        return True
    except ImportError:
        return False


def make_cubic_lattice(a=10.0):
    """Return a simple cubic lattice for tests."""
    from matsimpy.core import Lattice

    return Lattice.cubic(a)


def make_simple_molecule():
    """Return a reusable two-atom molecule for tests."""
    from matsimpy.core import Molecule

    return Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])


def make_simple_crystal(lattice=None):
    """Return a reusable two-atom crystal for tests."""
    from matsimpy.core import Crystal

    if lattice is None:
        lattice = make_cubic_lattice(10.0)
    return Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)


@pytest.fixture
def cubic_lattice():
    return make_cubic_lattice()


@pytest.fixture
def simple_molecule():
    return make_simple_molecule()


@pytest.fixture
def simple_crystal():
    return make_simple_crystal()


def require_path(*parts):
    """Skip the calling test when a repo-only asset (fixture, docs) is absent.

    Source distributions built by <=0.8.1 did not ship these assets; keep the
    suite green there while still running the checks inside the repository.
    """
    path = os.path.join(REPO_ROOT, *parts)
    if not os.path.exists(path):
        pytest.skip(f"repository asset not available: {os.path.relpath(path, REPO_ROOT)}")
    return path


# Asset roots that live in the repository but were not shipped in <=0.8.1 sdists.
# A FileNotFoundError pointing inside one of these roots is reported as a skip
# *only if the root itself is missing*; a missing file inside a present root is
# still a real failure.
_ASSET_ROOTS = tuple(
    os.path.join(REPO_ROOT, *parts)
    for parts in (
        ("tests", "calculator", "fixtures"),
        ("docs", "api_reference"),
        ("docs", "user_guide"),
    )
)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not report.failed or call.excinfo is None:
        return
    if not call.excinfo.errisinstance(FileNotFoundError):
        return
    filename = os.path.abspath(str(getattr(call.excinfo.value, "filename", "") or ""))
    for root in _ASSET_ROOTS:
        if filename.startswith(root + os.sep) and not os.path.isdir(root):
            report.outcome = "skipped"
            report.longrepr = (
                str(item.fspath),
                item.location[1] or 0,
                f"Skipped: repository asset not available: {os.path.relpath(root, REPO_ROOT)}",
            )
            return
