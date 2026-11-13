"""Regression tests for the November 2026 review of ``matsimpy.io``.

VASP and CIF data are unmodified pymatgen 2026.10.24 test files (see the
PROVENANCE.md files next to them).  Each test failed on the code before the fix.
"""

import json
import os

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.io import read
from matsimpy.io.ase import from_ase, read_ASE, to_ase, write_ASE
from matsimpy.io.cif import read_CIF, write_CIF
from matsimpy.io.json import from_json, to_json
from matsimpy.io.latex import crystals_to_latex_table
from matsimpy.io.mol import read_MOL, write_MOL
from matsimpy.io.pdb import read_PDB, write_PDB
from matsimpy.io.vasp import read_POSCAR, write_POSCAR
from matsimpy.io.xyz import read_XYZ, read_XYZ_multiframe, write_XYZ

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "calculator", "fixtures")
VASP = os.path.join(FIXTURES, "vasp")
CIF = os.path.join(FIXTURES, "cif")


def vasp(name):
    return os.path.join(VASP, name)


def cif(name):
    return os.path.join(CIF, name)


# --------------------------------------------------------------------------
# POSCAR
# --------------------------------------------------------------------------


def test_poscar_species_and_counts_over_several_lines():
    c = read_POSCAR(vasp("POSCAR_symbols_natoms_multilines"))
    assert len(c) == 53
    assert c.composition.as_counter() == {"Fe": 35, "Cr": 16, "Ni": 2}


@pytest.mark.parametrize("name", ["CONTCAR.MD", "CONTCAR.MD.npt"])
def test_contcar_velocities_are_kept(name):
    c = read_POSCAR(vasp(name))
    velocities = np.array([p["velocities"] for p in c.site_properties])
    assert velocities.shape == (len(c), 3)
    pmg = pytest.importorskip("pymatgen.io.vasp")
    ref = pmg.Poscar.from_file(vasp(name), check_for_potcar=False).structure
    np.testing.assert_allclose(velocities, ref.site_properties["velocities"])


def test_write_poscar_keeps_atom_order(tmp_path):
    c = read_POSCAR(vasp("POSCAR_Al12O18"))
    order = np.random.default_rng(0).permutation(len(c))
    shuffled = Crystal([c.species[i] for i in order], c.frac_positions[order], c.lattice)
    write_POSCAR(shuffled, tmp_path / "POSCAR")
    back = read_POSCAR(tmp_path / "POSCAR")
    assert back.species == shuffled.species
    np.testing.assert_allclose(back.cart_positions, shuffled.cart_positions, atol=1e-10)


def test_selective_dynamics_and_velocities_round_trip(tmp_path):
    c = read_POSCAR(vasp("POSCAR.AlN"))
    flags = [[True, False, True]] * len(c)
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


def test_poscar_title_must_be_one_line(tmp_path):
    c = read_POSCAR(vasp("POSCAR_fcc"))
    with pytest.raises(ValueError, match="single line"):
        write_POSCAR(c, tmp_path / "POSCAR", title="line1\nline2")


def test_gzipped_poscar_is_read():
    c = read(vasp("lobster_env/POSCAR.gz"))
    assert c.formula == "Fe16"


# --------------------------------------------------------------------------
# CIF
# --------------------------------------------------------------------------


def test_cif_with_comments_and_single_row_loop_matches_pymatgen():
    c = read_CIF(cif("FePO4.cif"))
    assert c.formula == "Fe4P4O16"
    pmg = pytest.importorskip("pymatgen.io.cif")
    ref = pmg.CifParser(cif("FePO4.cif")).parse_structures(primitive=False)[0]
    np.testing.assert_allclose(c.volume, ref.volume, rtol=1e-6)


def test_cif_type_symbols_with_charges():
    assert sorted(read_CIF(cif("CsCl-manual-oxi-ref.mcif")).species) == ["Cl", "Cs"]


@pytest.mark.parametrize(
    "name, match",
    [
        ("nosymm.cif", "not P1"),
        ("magnetic.example.NiO.mcif", "symmetry expansion"),
        ("C26H16BeN2O2S2.cif", "symmetry expansion"),  # used to fail in the tokenizer
        ("MultiStructure.cif", "2 structures"),
    ],
)
def test_cif_files_that_cannot_be_read_as_p1_raise(name, match):
    with pytest.raises(ValueError, match=match):
        read_CIF(cif(name))


def test_cif_quoting_rules(tmp_path):
    path = tmp_path / "q.cif"
    path.write_text(
        "data_q\n"
        "_publ_author_name 'Strel'tsov, V.A.'\n"
        "_cell_length_a 4\n_cell_length_b 4\n_cell_length_c 4\n"
        "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n"
        "_symmetry_space_group_name_H-M 'P 1'\n"
        "loop_\n_atom_site_label\n_atom_site_type_symbol\n"
        "_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n"
        "C1' C 0 0 0  # a comment with an apostrophe: it's\n"
        "O1' O 0.5 0.5 0.5\n"
        "_journal_coden_ASTM\n;\nsome text\n;\n"
    )
    c = read_CIF(path)
    assert c.species == ("C", "O")


def test_write_cif_title_is_one_word(tmp_path):
    c = read_POSCAR(vasp("POSCAR_fcc"))
    write_CIF(c, tmp_path / "x.cif", title="two\nlines")
    assert read_CIF(tmp_path / "x.cif").formula == c.formula


# --------------------------------------------------------------------------
# PDB
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["POSCAR_fcc", "POSCAR_Al12O18"])
def test_write_pdb_uses_standard_orientation(tmp_path, name):
    c = read_POSCAR(vasp(name))
    write_PDB(c, tmp_path / "x.pdb")
    back = read_PDB(tmp_path / "x.pdb", as_crystal=True)
    d = back.frac_positions - c.frac_positions
    d -= np.round(d)
    assert np.abs(d).max() < 1e-3
    assert back.species == c.species


def test_pdb_element_from_atom_name(tmp_path):
    path = tmp_path / "n.pdb"
    path.write_text(
        "ATOM      1 FE   UNK A   1       0.000   0.000   0.000  1.00  0.00\n"
        "ATOM      2 CL   UNK A   1       2.000   0.000   0.000  1.00  0.00\n"
        "ATOM      3  CA  UNK A   1       0.000   2.000   0.000  1.00  0.00\n"
        "ATOM      4  C1  UNK A   1       0.000   0.000   2.000  1.00  0.00            \n"
        "END\n"
    )
    assert read_PDB(path).species == ("Fe", "Cl", "C", "C")


def test_pdb_with_several_models_raises(tmp_path):
    atom = "ATOM      1  C   UNK A   1       0.000   0.000   0.000  1.00  0.00           C\n"
    (tmp_path / "m.pdb").write_text("MODEL 1\n" + atom + "ENDMDL\nMODEL 2\n" + atom + "ENDMDL\nEND\n")
    with pytest.raises(ValueError, match="MODEL"):
        read_PDB(tmp_path / "m.pdb")


# --------------------------------------------------------------------------
# XYZ / ASE / MOL / XSF
# --------------------------------------------------------------------------


def test_extended_xyz_with_cell_is_not_read_as_molecule(tmp_path):
    c = read_POSCAR(vasp("POSCAR_MnO"))
    write_ASE(c, tmp_path / "x.xyz")
    with pytest.raises(ValueError, match="format='ase'"):
        read_XYZ(tmp_path / "x.xyz")
    assert read(tmp_path / "x.xyz", format="ase").formula == c.formula


def test_ase_format_keeps_pbc_and_blank_title(tmp_path):
    c = read_POSCAR(vasp("POSCAR_MnO")).set_pbc([True, True, False])
    write_ASE(c, tmp_path / "s.ase")
    assert read_ASE(tmp_path / "s.ase").pbc == (True, True, False)
    m = Molecule(["O", "H", "H"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
    write_ASE(m, tmp_path / "m.ase", title="")
    assert len(read_ASE(tmp_path / "m.ase")) == 3


def test_ase_converters_keep_magmoms():
    pytest.importorskip("ase")
    c = read_POSCAR(vasp("POSCAR_MnO"))
    c = c.with_site_property("magmom", [5.0 if s == "Mn" else 0.0 for s in c.species])
    atoms = to_ase(c)
    np.testing.assert_allclose(atoms.get_initial_magnetic_moments(), [p["magmom"] for p in c.site_properties])
    assert [p["magmom"] for p in from_ase(atoms).site_properties] == [p["magmom"] for p in c.site_properties]


def test_pymatgen_converters_keep_pbc_site_properties_and_oxidation_states():
    pmg = pytest.importorskip("pymatgen.io.vasp")
    from matsimpy.io.pymatgen import from_pymatgen, to_pymatgen

    s = pmg.Poscar.from_file(vasp("CONTCAR.MD")).structure
    c = from_pymatgen(s)
    assert "velocities" in c.site_properties[0]
    slab = read_POSCAR(vasp("POSCAR_MnO")).set_pbc([True, True, False])
    assert to_pymatgen(slab).lattice.pbc == (True, True, False)
    assert from_pymatgen(to_pymatgen(slab)).pbc == (True, True, False)
    ps = to_pymatgen(read_POSCAR(vasp("POSCAR_MnO")))
    ps.add_oxidation_state_by_element({"Mn": 2, "O": -2})
    back = from_pymatgen(ps)
    assert {p["oxidation_state"] for p in back.site_properties} == {2, -2}
    assert {str(sp) for sp in to_pymatgen(back).species} == {"Mn2+", "O2-"}


def test_mol_counts_line_with_many_bonds_and_size_limit(tmp_path):
    lines = ["title", "", "", "  2150  0  0  0  0  0  0  0  0999 V2000"]
    lines += ["    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0",
              "    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0", "M  END"]
    (tmp_path / "x.mol").write_text("\n".join(lines) + "\n")
    assert len(read_MOL(tmp_path / "x.mol")) == 2  # 2 atoms, 150 bonds (block absent)
    big = Molecule(["H"] * 1000, [[i * 1.0, 0, 0] for i in range(1000)])
    with pytest.raises(ValueError, match="999"):
        write_MOL(big, tmp_path / "big.mol")


def test_xsf_with_atomic_numbers(tmp_path):
    ase = pytest.importorskip("ase.io")
    from matsimpy.io.ase import to_ase as _to_ase
    from matsimpy.io.xsf import read_XSF

    c = read_POSCAR(vasp("POSCAR_MnO"))
    ase.write(tmp_path / "x.xsf", _to_ase(c))  # ASE writes atomic numbers
    assert read_XSF(tmp_path / "x.xsf").species == c.species


def test_xyz_multiframe_strict_rejects_garbage(tmp_path):
    m = Molecule(["O", "H", "H"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
    write_XYZ(m, tmp_path / "a.xyz")
    text = (tmp_path / "a.xyz").read_text()
    (tmp_path / "multi.xyz").write_text(text + "this is not xyz\n" + text)
    with pytest.raises(ValueError, match="atom count"):
        read_XYZ_multiframe(tmp_path / "multi.xyz")
    assert len(read_XYZ_multiframe(tmp_path / "multi.xyz", strict=False)) == 2
    with pytest.raises(ValueError, match="single line"):
        write_XYZ(m, tmp_path / "b.xyz", title="a\nb")


# --------------------------------------------------------------------------
# JSON, LaTeX, volumetric
# --------------------------------------------------------------------------


def test_json_keeps_numpy_site_properties():
    c = read_POSCAR(vasp("POSCAR_MnO"))
    c = c.with_site_property("magmom", [np.array([0, 0, 1.0])] * len(c))
    back = from_json(to_json(c))
    assert isinstance(back.site_properties[0]["magmom"], np.ndarray)


def test_json_pymatgen_structure_gives_clear_error():
    pmg = pytest.importorskip("pymatgen.io.vasp")
    s = pmg.Poscar.from_file(vasp("POSCAR_MnO")).structure
    with pytest.raises(ValueError, match="from_pymatgen"):
        from_json(json.dumps(s.as_dict()))


def test_latex_unknown_column_raises_and_no_placeholder_space_group():
    c = read_POSCAR(vasp("POSCAR_MnO"))
    assert "N/A" not in crystals_to_latex_table([c])
    with pytest.raises(ValueError, match="Unknown crystal table column"):
        crystals_to_latex_table([c], include_columns=["ID", "Space Group"])
    table = crystals_to_latex_table(
        [c], include_columns=["ID", "Space Group"],
        custom_formatters={"Space Group": lambda crystal, i: "Fm-3m"},
    )
    assert "Fm-3m" in table


def test_integrated_diff_is_zero_without_spin():
    from matsimpy.calculator.vasp.outputs import Chgcar

    chg = Chgcar.from_file(vasp("CHGCAR.nospin.gz"))
    np.testing.assert_allclose(chg.get_integrated_diff(0, 1.0, nbins=2), [[0.5, 0.0], [1.0, 0.0]])
