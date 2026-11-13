"""Tests for matsimpy.io POSCAR/CONTCAR reading and writing.

Every input is an unmodified pymatgen test file from tests/calculator/fixtures/vasp
(see PROVENANCE.md). pymatgen, when installed, is the reference for what each file
contains.
"""

import os

import numpy as np
import pytest

from matsimpy.core import Crystal
from matsimpy.io import read, read_POSCAR, write, write_POSCAR
from matsimpy.io.registry import registry

VASP_DIR = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures", "vasp")


def _path(*parts):
    return os.path.join(VASP_DIR, *parts)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "handler"), [
    ("POSCAR", "vasp-poscar"),
    ("POSCAR.AlN", "vasp-poscar"),
    ("POSCAR_fcc", "vasp-poscar"),
    ("CONTCAR_Li2O", "vasp-contcar"),
    ("FePO4.vasp", "vasp-poscar"),  # extension
])
def test_format_is_detected_from_vasp_file_names(name, handler):
    assert registry.detect(_path(name)).name == handler


@pytest.mark.parametrize(("relpath", "formula", "natoms"), [
    (("POSCAR_fcc",), "H8", 8),
    (("POSCAR.AlN",), "Al2N2", 4),
    (("CONTCAR_Li2O",), "Li64O32", 96),
    # empty comment (first) line: blank lines were dropped, shifting every line
    (("nmr", "cs", "basic", "hydromagnesite", "POSCAR"), "H20C8O36Mg10", 74),
    (("lobster_env", "POSCAR.gz"), "Fe16", 16),  # compressed
])
def test_read_real_files(relpath, formula, natoms):
    crystal = read(_path(*relpath))
    assert crystal.formula == formula
    assert len(crystal) == natoms


def test_species_and_counts_over_several_lines():
    c = read_POSCAR(_path("POSCAR_symbols_natoms_multilines"))
    assert c.composition.as_counter() == {"Fe": 35, "Cr": 16, "Ni": 2}


def test_empty_comment_line_matches_pymatgen():
    structure = pytest.importorskip("pymatgen.core").Structure
    path = _path("nmr", "cs", "basic", "hydromagnesite", "POSCAR")
    crystal, reference = read(path), structure.from_file(path)
    np.testing.assert_allclose(crystal.lattice.matrix, reference.lattice.matrix)
    np.testing.assert_allclose(crystal.frac_positions, reference.frac_coords)
    assert list(crystal.species) == [site.specie.symbol for site in reference]


@pytest.mark.parametrize("name", ["CONTCAR.MD", "CONTCAR.MD.npt"])  # .npt has lattice velocities first
def test_contcar_velocities_match_pymatgen(name):
    velocities = np.array([p["velocities"] for p in read_POSCAR(_path(name)).site_properties])
    pmg = pytest.importorskip("pymatgen.io.vasp")
    ref = pmg.Poscar.from_file(_path(name), check_for_potcar=False).structure
    np.testing.assert_allclose(velocities, ref.site_properties["velocities"])


@pytest.mark.parametrize("name", ["FePO4.vasp", "POSCAR"])
def test_vasp4_poscar_is_rejected_with_a_clear_message(name):
    with pytest.raises(ValueError, match="VASP 4 format POSCAR"):
        read(_path(name))


def test_read_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_POSCAR(tmp_path / "missing.vasp")
    (tmp_path / "bad.vasp").write_text("Invalid\n")
    with pytest.raises(ValueError):
        read_POSCAR(tmp_path / "bad.vasp")


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------


def test_write_round_trip_by_file_name(tmp_path):
    crystal = read(_path("POSCAR.AlN"))
    write(crystal, str(tmp_path / "POSCAR"))  # format detected from the name
    again = read(str(tmp_path / "POSCAR"))
    assert again.species == crystal.species
    np.testing.assert_allclose(again.lattice.matrix, crystal.lattice.matrix)
    np.testing.assert_allclose(again.frac_positions, crystal.frac_positions, atol=1e-8)
    assert "Al" in (tmp_path / "POSCAR").read_text().splitlines()[0]  # default title is the formula


def test_write_keeps_atom_order(tmp_path):
    c = read_POSCAR(_path("POSCAR_Al12O18"))
    order = np.random.default_rng(0).permutation(len(c))
    shuffled = Crystal([c.species[i] for i in order], c.frac_positions[order], c.lattice)
    write_POSCAR(shuffled, tmp_path / "POSCAR")
    back = read_POSCAR(tmp_path / "POSCAR")
    assert back.species == shuffled.species
    np.testing.assert_allclose(back.cart_positions, shuffled.cart_positions, atol=1e-10)


def test_selective_dynamics_and_velocities_round_trip(tmp_path):
    c = read_POSCAR(_path("POSCAR.AlN"))
    flags = [[True, True, True], [False, False, False], [True, False, True], [False, True, False]]
    c = c.with_site_properties(
        [{"selective_dynamics": f, "velocities": [0.1 * i, 0.0, -0.1]} for i, f in enumerate(flags)]
    )
    write_POSCAR(c, tmp_path / "POSCAR")
    back = read_POSCAR(tmp_path / "POSCAR")
    assert [p["selective_dynamics"] for p in back.site_properties] == flags
    np.testing.assert_allclose([p["velocities"] for p in back.site_properties],
                               [p["velocities"] for p in c.site_properties])
    pmg = pytest.importorskip("pymatgen.io.vasp")
    ref = pmg.Poscar.from_file(str(tmp_path / "POSCAR"), check_for_potcar=False).structure
    assert np.array(ref.site_properties["selective_dynamics"]).tolist() == flags


def test_write_errors(tmp_path):
    with pytest.raises(ValueError):
        write_POSCAR("not a crystal", tmp_path / "POSCAR")
    with pytest.raises(ValueError, match="single line"):
        write_POSCAR(read_POSCAR(_path("POSCAR_fcc")), tmp_path / "POSCAR", title="line1\nline2")
