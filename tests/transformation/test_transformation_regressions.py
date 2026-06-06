"""Regression tests for transformation correctness edge cases."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation import translate
from matsimpy.transformation.atomic import merge_atoms, perturb_positions, sort_atoms, split_atom, swap_atoms
from matsimpy.transformation.composite import BatchProcessor, TransformationPipeline
from matsimpy.transformation.lattice import (
    get_niggli_reduced,
    perturb_lattice,
    scale_lattice,
    set_volume,
    standardize_cell,
)
from matsimpy.transformation.structural import (
    align_molecules,
    fragment_molecule,
    generate_conformers,
    make_supercell,
)


class _SideEffectThenFail:
    def __init__(self, marker):
        self.marker = marker

    def __call__(self, structure):
        marker_text = self.marker.read_text() if self.marker.exists() else ""
        self.marker.write_text(marker_text + "x")
        raise ValueError("boom")


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


def test_fragment_molecule_breaks_inferred_bond_and_preserves_properties():
    molecule = Molecule(
        ["H", "H"],
        [[0, 0, 0], [0.74, 0, 0]],
        site_properties=[{"id": "left"}, {"id": "right"}],
    )

    fragments = fragment_molecule(molecule, [(0, 1)])

    assert len(fragments) == 2
    assert [fragment.species for fragment in fragments] == [("H",), ("H",)]
    assert fragments[0].site_properties == ({"id": "left"},)
    assert fragments[1].site_properties == ({"id": "right"},)


def test_optional_conformer_generation_requires_rdkit_or_returns_molecules():
    molecule = Molecule(["H", "H"], [[0, 0, 0], [0.74, 0, 0]])
    try:
        conformers = generate_conformers(molecule, n_conformers=1)
    except ImportError as e:
        assert "RDKit is required" in str(e)
    else:
        assert len(conformers) == 1
        assert isinstance(conformers[0], Molecule)


def test_get_niggli_reduced_returns_new_crystal_and_preserves_metadata():
    pytest.importorskip("spglib")
    crystal = Crystal(
        ["He"],
        [[0.25, 0.25, 0.25]],
        Lattice([[2.0, 0.1, 0.0], [0.0, 1.9, 0.2], [0.1, 0.0, 2.1]]),
        site_properties=[{"tag": "kept"}],
    )

    reduced = get_niggli_reduced(crystal)

    assert reduced is not crystal
    assert isinstance(reduced, Crystal)
    assert reduced.species == crystal.species
    assert reduced.pbc == crystal.pbc
    assert reduced.site_properties == crystal.site_properties
    np.testing.assert_allclose(reduced.cart_positions, crystal.cart_positions, atol=1e-10)


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


def test_standardize_cell_preserves_site_properties_when_sites_reorder(monkeypatch):
    spglib = pytest.importorskip("spglib")
    crystal = Crystal(
        ["Na", "Cl"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
        site_properties=[{"id": "Na"}, {"id": "Cl"}],
    )

    def fake_standardize_cell(cell):
        lattice, positions, numbers = cell
        return lattice, positions[[1, 0]], np.array(numbers)[[1, 0]]

    monkeypatch.setattr(spglib, "standardize_cell", fake_standardize_cell)

    standardized = standardize_cell(crystal)

    assert standardized.species == ("Cl", "Na")
    assert standardized.site_properties == ({"id": "Cl"}, {"id": "Na"})


def test_scale_lattice_rejects_invalid_scale_factors():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(1.0))

    invalid_values = [0, -1, float("nan"), [1, 1], [1, -1, 1], [1, float("inf"), 1]]
    for value in invalid_values:
        with pytest.raises(ValueError):
            scale_lattice(crystal, value)


def test_set_volume_rejects_non_positive_target_volume():
    crystal = Crystal(["He"], [[0, 0, 0]], Lattice.cubic(1.0))

    with pytest.raises(ValueError, match="target_volume"):
        set_volume(crystal, -100)


def test_align_molecules_rejects_empty_selections_early():
    molecule = Molecule(["H"], [[0, 0, 0]])

    with pytest.raises(ValueError, match="at least one"):
        align_molecules(molecule, molecule, [], [])


def test_align_molecules_rejects_out_of_range_indices():
    molecule = Molecule(["H"], [[0, 0, 0]])

    with pytest.raises(IndexError, match="outside molecule"):
        align_molecules(molecule, molecule, [0], [1])


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


def test_parallel_raise_mode_does_not_retry_failed_transform(tmp_path):
    marker = tmp_path / "calls.txt"

    processor = BatchProcessor(
        [_SideEffectThenFail(marker)],
        n_workers=2,
        progress=False,
        error_handling="raise",
    )

    with pytest.raises(RuntimeError, match="Transformation failed"):
        processor.process([Molecule(["He"], [[0, 0, 0]])])

    assert marker.read_text() == "x"
