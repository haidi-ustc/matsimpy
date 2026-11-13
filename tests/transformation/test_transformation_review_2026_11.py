"""Regression tests for the November 2026 review of ``matsimpy.transformation``.

Each test failed on the code before the fix.
"""

import json

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation import make_supercell, translate
from matsimpy.transformation.atomic import merge_atoms, move_atoms, perturb_positions, swap_atoms
from matsimpy.transformation.chemical import substitute, substitute_all
from matsimpy.transformation.composite import ParameterSweep, TransformationPipeline
from matsimpy.transformation.geometric import translate_to_origin
from matsimpy.transformation.lattice import (
    apply_deformation,
    apply_strain,
    optimize_lattice,
    rotate_lattice,
    scale_lattice,
    standardize_cell,
    transform_lattice,
)
from matsimpy.transformation.registry import registry
from matsimpy.transformation.structural import align_molecules, fragment_molecule, merge_molecules


@pytest.fixture
def tric():
    lat = Lattice.from_parameters(3.0, 3.5, 4.0, 80, 100, 110)
    return Crystal(["Na", "Cl"], [[0.1, 0.2, 0.3], [0.6, 0.55, 0.8]], lat)


# --------------------------------------------------------------------------
# Lattice deformation conventions (row vectors: A' = A @ F.T)
# --------------------------------------------------------------------------


def test_apply_deformation_maps_cartesian_vectors_by_f(tric):
    F = np.array([[1.05, 0.1, 0.0], [0.0, 0.98, 0.03], [0.02, 0.0, 1.01]])
    out = apply_deformation(tric, F)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ F.T, atol=1e-12)
    np.testing.assert_allclose(out.cart_positions, tric.cart_positions @ F.T, atol=1e-12)
    np.testing.assert_allclose(out.frac_positions, tric.frac_positions, atol=1e-12)


def test_apply_deformation_without_positions_keeps_cartesian(tric):
    F = [[1.1, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    out = apply_deformation(tric, F, deform_positions=False)
    np.testing.assert_allclose(out.cart_positions, tric.cart_positions, atol=1e-12)


def test_apply_strain_matches_pymatgen(tric):
    pmg = pytest.importorskip("pymatgen.core")
    strain = [[0.01, 0.02, 0.0], [0.02, -0.01, 0.0], [0.0, 0.0, 0.03]]
    ours = apply_strain(tric, strain)
    ref = pmg.Lattice(tric.lattice.matrix).matrix @ (np.eye(3) + np.array(strain)).T
    np.testing.assert_allclose(ours.lattice.matrix, ref, atol=1e-12)


def test_apply_strain_vector_is_diagonal_and_bad_shapes_raise(tric):
    np.testing.assert_allclose(
        apply_strain(tric, [0.01, 0.0, 0.02]).lattice.matrix,
        apply_strain(tric, np.diag([0.01, 0.0, 0.02])).lattice.matrix,
    )
    for bad in (0.01, [0.01, 0.0], [[0.01, 0, 0], [0, 0, 0]], [[True, 0, 0], [0, 0, 0], [0, 0, 0]]):
        with pytest.raises((ValueError, TypeError)):
            apply_strain(tric, bad)
    with pytest.raises(ValueError, match="determinant"):
        apply_strain(tric, [-1.0, 0.0, 0.0])


def test_rotate_lattice_rotates_vectors_and_requires_proper_rotation(tric):
    R = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    out = rotate_lattice(tric, R)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ R.T, atol=1e-12)
    np.testing.assert_allclose(out.cart_positions, tric.cart_positions @ R.T, atol=1e-12)
    kept = rotate_lattice(tric, R, rotate_atoms=False)
    np.testing.assert_allclose(kept.cart_positions, tric.cart_positions, atol=1e-12)
    with pytest.raises(ValueError, match="orthogonal"):
        rotate_lattice(tric, np.diag([1.1, 1.0, 1.0]))
    with pytest.raises(ValueError, match="proper"):
        rotate_lattice(tric, np.diag([-1.0, 1.0, 1.0]))


def test_transform_lattice_default_moves_atoms_with_cell(tric):
    T = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.1]]
    out = transform_lattice(tric, T)
    np.testing.assert_allclose(out.frac_positions, tric.frac_positions, atol=1e-12)
    np.testing.assert_allclose(out.lattice.matrix, tric.lattice.matrix @ np.array(T).T, atol=1e-12)


# --------------------------------------------------------------------------
# Scaling
# --------------------------------------------------------------------------


def test_scale_lattice_and_optimize_lattice_validation(tric):
    with pytest.raises(TypeError):
        scale_lattice(tric, True)
    with pytest.raises(TypeError):
        scale_lattice(tric, [True, 1.0, 1.0])
    with pytest.raises(ValueError, match="only one"):
        optimize_lattice(tric, target_density=2.0, target_volume=50.0)
    with pytest.raises(ValueError, match="preserve_angles"):
        optimize_lattice(tric, target_volume=50.0, preserve_angles=False)


# --------------------------------------------------------------------------
# Supercell, standardize_cell
# --------------------------------------------------------------------------


def test_make_supercell_leaves_non_periodic_axis_alone():
    slab = Crystal(["C"], [[0.25, 0.25, 1.3]], Lattice.cubic(5.0), pbc=[True, True, False])
    sc = make_supercell(slab, [2, 2, 1])
    np.testing.assert_allclose(sorted(set(np.round(sc.frac_positions[:, 2], 12))), [1.3])
    with pytest.raises(ValueError, match="non-periodic"):
        make_supercell(slab, [1, 1, 2])
    with pytest.raises(ValueError, match="non-periodic"):
        make_supercell(slab, [[1, 0, 1], [0, 1, 0], [0, 0, 1]])
    with pytest.raises(TypeError):
        make_supercell(slab, [True, True, True])


def test_standardize_cell_fails_loudly():
    pytest.importorskip("spglib")
    slab = Crystal(["Cu"], [[0, 0, 0]], Lattice.cubic(3.0), pbc=[True, True, False])
    with pytest.raises(ValueError, match="periodic"):
        standardize_cell(slab)
    fcc_prim = Crystal(
        ["Cu"], [[0, 0, 0]], Lattice([[0, 1.8, 1.8], [1.8, 0, 1.8], [1.8, 1.8, 0]]),
        site_properties=[{"magmom": 1.0}],
    )
    with pytest.raises(ValueError, match="site properties"):
        standardize_cell(fcc_prim)  # 1 atom -> 4 atoms


# --------------------------------------------------------------------------
# Atomic operations
# --------------------------------------------------------------------------


def test_merge_atoms_uses_minimum_image_midpoint():
    c = Crystal(["H", "H"], [[0.05, 0.5, 0.5], [0.95, 0.5, 0.5]], Lattice.cubic(5.0))
    merged = merge_atoms(c, 0, 1)
    assert len(merged) == 1
    assert merged.frac_positions[0, 0] % 1.0 == pytest.approx(0.0, abs=1e-12) or \
        merged.frac_positions[0, 0] % 1.0 == pytest.approx(1.0, abs=1e-12)
    with pytest.raises(ValueError, match="duplicates"):
        merge_atoms(c, 0, 0)


def test_atom_index_validation():
    m = Molecule(["H", "O", "H"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
    with pytest.raises(ValueError, match="duplicates"):
        move_atoms(m, [0, 0], [1.0, 0, 0])
    with pytest.raises(TypeError):
        move_atoms(m, True, [1.0, 0, 0])
    with pytest.raises(ValueError):
        move_atoms(m, 0, 1.0)  # used to broadcast to [1, 1, 1]
    np.testing.assert_allclose(move_atoms(m, np.int64(0), [1.0, 0, 0]).positions[0], [1, 0, 0])
    with pytest.raises(ValueError, match="duplicates"):
        swap_atoms(m, 1, 1)
    with pytest.raises(ValueError, match="duplicates"):
        perturb_positions(m, 0.1, indices=[0, 0], seed=1)


def test_substitute_validation():
    m = Molecule(["H", "O", "H"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
    with pytest.raises(ValueError):
        substitute(m, 0, ["F", "Cl"])  # used to take the first species silently
    with pytest.raises(TypeError):
        substitute(m, True, "F")
    assert substitute(m, np.int64(1), "S").species == ("H", "S", "H")
    with pytest.raises(ValueError, match="not found"):
        substitute_all(m, "C", "Si")


def test_translate_to_origin_uses_mass_weighted_center_for_crystals():
    c = Crystal(["H", "O"], [[0, 0, 0], [0.5, 0, 0]], Lattice.cubic(4.0))
    out = translate_to_origin(c)
    masses = np.array([1.00794, 15.9994])
    com = np.average(out.cart_positions, weights=masses, axis=0)
    np.testing.assert_allclose(com, [0, 0, 0], atol=1e-3)


# --------------------------------------------------------------------------
# Molecular operations
# --------------------------------------------------------------------------


def test_align_molecules_recovers_rotation():
    rng = np.random.default_rng(1)
    p = rng.normal(size=(5, 3)) * 2
    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    ref = Molecule(["C"] * 5, p)
    moved = Molecule(["C"] * 5, p @ R.T + [1, 2, 3])
    aligned = align_molecules(ref, moved, range(5), range(5))
    np.testing.assert_allclose(aligned.positions, p, atol=1e-10)


def test_merge_molecules_does_not_leave_overlapping_atoms():
    c = Molecule(["C"], [[0, 0, 0]])
    o = Molecule(["O"], [[5, 5, 5]])
    with pytest.raises(ValueError, match="apart"):
        merge_molecules(c, o, 0, 0)
    np.testing.assert_allclose(merge_molecules(c, o, 0, 0, bond_length=1.2).positions[1], [1.2, 0, 0])


def test_fragment_molecule_rejects_breaking_a_non_bond():
    m = Molecule(["C", "C", "C"], [[0, 0, 0], [1.5, 0, 0], [3.0, 0, 0]])
    with pytest.raises(ValueError, match="not bonded"):
        fragment_molecule(m, [[0, 2]])
    assert len(fragment_molecule(m, [[0, 1]])) == 2


# --------------------------------------------------------------------------
# Registry schemas
# --------------------------------------------------------------------------


def test_registry_schemas_cover_signatures_and_accept_numpy():
    import inspect

    for spec in registry.list_all():
        params = list(inspect.signature(spec.callable).parameters)[1:]
        props = set((spec.parameter_schema or {}).get("properties", {}))
        assert set(params) == props, spec.name

    m = Molecule(["H", "O", "H"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
    out = registry.apply("substitute", m, indices=np.array([0, 2]), new_species=["F", "F"])
    assert out.species == ("F", "O", "F")
    assert registry.apply("translate", m, vector=np.array([1.0, 0, 0])).positions[0, 0] == 1.0
    assert registry.get("merge_atoms").preserves_composition is False
    assert registry.get("split_atom").preserves_composition is False
    assert registry.get("standardize_cell").preserves_site_properties is False


# --------------------------------------------------------------------------
# Composite
# --------------------------------------------------------------------------


def test_parameter_sweep_custom_applies_in_declared_order():
    c = Crystal(["Cu"], [[0, 0, 0]], Lattice.cubic(3.0))
    sweep = ParameterSweep(
        c,
        {
            "supercell": {"func": make_supercell, "params": {"scaling_matrix": [[2, 1, 1]]}},
            "move": {"func": move_atoms, "params": {"indices": [1], "displacement": [[0.1, 0, 0]]}},
        },
        mode="custom",
        # listed in the other order: atom 1 only exists after the supercell step
        custom_combinations=[{"move": {"indices": 1, "displacement": [0.1, 0, 0]},
                              "supercell": {"scaling_matrix": [2, 1, 1]}}],
    )
    (structure, _), = list(sweep)
    np.testing.assert_allclose(structure.cart_positions[1], [3.1, 0, 0], atol=1e-12)


def test_pipeline_save_rejects_lambdas(tmp_path):
    pipe = TransformationPipeline("p")
    pipe.add_step(lambda s: s)
    with pytest.raises(ValueError, match="cannot be saved"):
        pipe.save(tmp_path / "p.json")
    assert not (tmp_path / "p.json").exists()

    ok = TransformationPipeline("ok")
    ok.add_step(translate, vector=[1.0, 0.0, 0.0])
    ok.save(tmp_path / "ok.json")
    assert json.loads((tmp_path / "ok.json").read_text())["steps"][0]["func_name"] == "translate"
