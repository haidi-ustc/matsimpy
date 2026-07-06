"""Path safety tests for AI IO skill file writes."""

import pytest

from matsimpy import Molecule
from matsimpy.ai.skills.io import _save_latex_table, _write_structure


def test_write_structure_rejects_absolute_path(tmp_path):
    target = tmp_path / "outside.xyz"
    molecule = Molecule(["He"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="workspace-relative"):
        _write_structure(str(target), molecule, format="xyz")

    assert not target.exists()


def test_write_structure_rejects_parent_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "escape.xyz"
    if outside.exists():
        outside.unlink()

    molecule = Molecule(["Ne"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="workspace-relative"):
        _write_structure("../escape.xyz", molecule, format="xyz")

    assert not outside.exists()


def test_save_latex_table_rejects_parent_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    molecule = Molecule(["He"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="workspace-relative"):
        _save_latex_table("../table.tex", [molecule])


def test_write_structure_accepts_relative_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    molecule = Molecule(["He"], [[0, 0, 0]])

    result = _write_structure("helium.xyz", molecule, format="xyz")

    assert result["saved_to"] == "helium.xyz"
    assert (tmp_path / "helium.xyz").exists()
