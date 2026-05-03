"""Regression tests for transformation correctness edge cases."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation import translate
from matsimpy.transformation.atomic import merge_atoms, perturb_positions, sort_atoms, split_atom, swap_atoms
from matsimpy.transformation.composite import BatchProcessor, TransformationPipeline
from matsimpy.transformation.lattice import get_niggli_reduced, perturb_lattice, standardize_cell
from matsimpy.transformation.structural import fragment_molecule, generate_conformers, make_supercell


def test_swap_atoms_reindexes_site_properties():
    molecule = Molecule(
        ["Na", "Cl"],
        [[0, 0, 0], [1, 0, 0]],
        site_properties=[{"label": "Na-site"}, {"label": "Cl-site"}],
    )

    swapped = swap_atoms(molecule, 0, 1)

    assert swapped.species == ("Cl", "Na")
    assert swapped.site_properties == ({"label": "Cl-site"}, {"label": "Na-site"})


def test_sort_atoms_reindexes_site_properties():
    crystal = Crystal(
        ["Na", "Cl"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
        site_properties=[{"label": "Na-site"}, {"label": "Cl-site"}],
    )

    sorted_crystal = sort_atoms(crystal, key="species")

    assert sorted_crystal.species == ("Cl", "Na")
    assert sorted_crystal.site_properties == (
        {"label": "Cl-site"},
        {"label": "Na-site"},
    )


def test_merge_atoms_collapses_site_properties_to_merged_site():
    molecule = Molecule(
        ["H", "O", "H"],
        [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
        site_properties=[{"id": 0}, {"id": 1}, {"id": 2}],
    )

    merged = merge_atoms(molecule, 0, 1)

    assert merged.species == ("H", "H")
    assert merged.site_properties == ({"id": 0}, {"id": 2})


def test_split_atom_copies_source_site_properties_to_new_sites():
    molecule = Molecule(
        ["O", "He"],
        [[0, 0, 0], [3, 0, 0]],
        site_properties=[{"role": "split"}, {"role": "kept"}],
    )

    split = split_atom(molecule, 0, ["H", "H"], [[-0.5, 0, 0], [0.5, 0, 0]])

    assert split.species == ("He", "H", "H")
    assert split.site_properties == (
        {"role": "kept"},
        {"role": "split"},
        {"role": "split"},
    )


def test_split_atom_rejects_mismatched_species_and_positions():
    molecule = Molecule(["O"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="same length"):
        split_atom(molecule, 0, ["H", "H"], [[0, 0, 0]])


def test_make_supercell_preserves_pbc_and_repeats_site_properties():
    crystal = Crystal(
        ["Na", "Cl"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
        pbc=[True, False, True],
        site_properties=[{"id": "Na"}, {"id": "Cl"}],
    )

    supercell = make_supercell(crystal, [2, 1, 1])

    assert supercell.pbc == (True, False, True)
    assert len(supercell) == 4
    assert supercell.site_properties == (
        {"id": "Na"},
        {"id": "Cl"},
        {"id": "Na"},
        {"id": "Cl"},
    )


def test_make_supercell_general_unimodular_preserves_cartesian_positions():
    crystal = Crystal(["He"], [[0.25, 0, 0]], Lattice.cubic(1.0))

    transformed = make_supercell(crystal, [[1, 1, 0], [0, 1, 0], [0, 0, 1]])

    delta = transformed.cart_positions[0] - crystal.cart_positions[0]
    delta_frac = delta @ np.linalg.inv(transformed.lattice.lattice_vectors)
    np.testing.assert_allclose(delta_frac, np.rint(delta_frac), atol=1e-12)


def test_perturb_positions_preserves_pbc_and_does_not_reset_global_rng():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(1.0), pbc=[True, False, True])

    np.random.seed(123)
    expected_next = np.random.random(3)
    np.random.seed(123)
    perturbed = perturb_positions(crystal, 0.1, seed=999)
    actual_next = np.random.random(3)

    assert perturbed.pbc == (True, False, True)
    np.testing.assert_allclose(actual_next, expected_next)


def test_perturb_lattice_does_not_reset_global_rng():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(1.0))

    np.random.seed(456)
    expected_next = np.random.random(3)
    np.random.seed(456)
    perturb_lattice(crystal, 0.1, seed=999)
    actual_next = np.random.random(3)

    np.testing.assert_allclose(actual_next, expected_next)


def test_placeholder_apis_raise_not_implemented():
    molecule = Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]])
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(1.0))

    with pytest.raises(NotImplementedError):
        fragment_molecule(molecule, [(0, 1)])
    with pytest.raises(NotImplementedError):
        generate_conformers(molecule)
    with pytest.raises(NotImplementedError):
        get_niggli_reduced(crystal)


def test_standardize_cell_does_not_pass_stale_site_properties_when_cell_changes():
    spglib = pytest.importorskip("spglib")
    del spglib
    crystal = Crystal(
        ["Na", "Cl"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
        site_properties=[{"id": "Na"}, {"id": "Cl"}],
    )

    standardized = standardize_cell(crystal)

    assert len(standardized.site_properties) in (0, len(standardized))


def test_pipeline_round_trips_numpy_kwargs(tmp_path):
    pipeline = TransformationPipeline("array_kwargs")
    pipeline.add_step(translate, displacement=np.array([0.0, 0.0, 0.0]))
    path = tmp_path / "pipeline.json"

    pipeline.save(path)
    loaded = TransformationPipeline.load(path)

    assert isinstance(loaded.steps[0]["kwargs"]["displacement"], np.ndarray)
    np.testing.assert_allclose(loaded.steps[0]["kwargs"]["displacement"], [0, 0, 0])


def test_pipeline_rejects_opaque_kwargs(tmp_path):
    pipeline = TransformationPipeline("opaque")
    pipeline.add_step(translate, displacement=[0, 0, 0], opaque=object())

    with pytest.raises(TypeError):
        pipeline.save(tmp_path / "pipeline.json")


def test_process_stream_is_lazy_for_sequential_processors():
    molecule = Molecule(["He"], [[0, 0, 0]])

    def source():
        yield molecule
        raise AssertionError("stream was advanced beyond the first item")

    processor = BatchProcessor([lambda structure: structure.copy()], n_workers=1, progress=False)
    stream = processor.process_stream(source())

    first = next(stream)
    assert first.success
    with pytest.raises(AssertionError, match="advanced beyond"):
        next(stream)
