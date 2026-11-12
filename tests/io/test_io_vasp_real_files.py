"""matsimpy.io POSCAR reading on real pymatgen test files.

Files: tests/calculator/fixtures/vasp (see PROVENANCE.md). pymatgen, when
installed, is the reference for what each file contains.
"""

import os
import shutil

import numpy as np
import pytest

from matsimpy.io import read
from matsimpy.io.registry import registry

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


def _path(*parts):
    return os.path.join(VASP_DIR, *parts)


@pytest.mark.parametrize(
    ("name", "handler"),
    [
        ("POSCAR", "vasp-poscar"),
        ("POSCAR.AlN", "vasp-poscar"),
        ("POSCAR_fcc", "vasp-poscar"),
        ("CONTCAR_Li2O", "vasp-contcar"),
        ("FePO4.vasp", "vasp-poscar"),  # extension
    ],
)
def test_format_detected_from_vasp_file_names(name, handler):
    """Only extensions were used, so read("POSCAR") raised "Could not detect"."""
    assert registry.detect(_path(name)).name == handler


@pytest.mark.parametrize(
    ("relpath", "formula", "natoms"),
    [
        (("POSCAR_fcc",), "H8", 8),
        (("POSCAR.AlN",), "Al2N2", 4),
        (("CONTCAR_Li2O",), "Li64O32", 96),
        # empty comment (first) line: blank lines were dropped, shifting every line
        (("nmr", "cs", "basic", "hydromagnesite", "POSCAR"), "H20C8O36Mg10", 74),
    ],
)
def test_read_real_poscars_without_format(relpath, formula, natoms):
    crystal = read(_path(*relpath))
    assert crystal.formula == formula
    assert len(crystal) == natoms


def test_read_poscar_with_empty_comment_line_matches_pymatgen():
    pytest.importorskip("pymatgen")
    from pymatgen.core import Structure

    path = _path("nmr", "cs", "basic", "hydromagnesite", "POSCAR")
    crystal = read(path)
    reference = Structure.from_file(path)
    np.testing.assert_allclose(crystal.lattice.matrix, reference.lattice.matrix)
    np.testing.assert_allclose(crystal.frac_positions, reference.frac_coords)
    assert list(crystal.species) == [site.specie.symbol for site in reference]


@pytest.mark.parametrize("name", ["FePO4.vasp", "POSCAR"])
def test_vasp4_poscar_is_rejected_with_a_clear_message(name):
    """VASP 4 files (no symbol line; species named after the coordinates) are not
    supported. Both real files are VASP 4; they failed with "Invalid species counts"."""
    with pytest.raises(ValueError, match="VASP 4 format POSCAR"):
        read(_path(name))


def test_write_detects_poscar_file_name(tmp_path):
    from matsimpy.io import write

    crystal = read(_path("POSCAR.AlN"))
    write(crystal, str(tmp_path / "POSCAR"))
    again = read(str(tmp_path / "POSCAR"))
    assert again.formula == crystal.formula
    np.testing.assert_allclose(again.lattice.matrix, crystal.lattice.matrix)
