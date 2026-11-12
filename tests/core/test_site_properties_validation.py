"""Regression tests for site_properties validation and copy isolation."""

import pytest

from matsimpy.core import Crystal, Lattice, Molecule


def test_molecule_rejects_site_properties_length_mismatch():
    with pytest.raises(ValueError, match="site_properties.*must match"):
        Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]], site_properties=[{"charge": 0}])


def test_crystal_rejects_site_properties_length_mismatch():
    with pytest.raises(ValueError, match="site_properties.*must match"):
        Crystal(
            ["Si", "O"],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            Lattice.cubic(10),
            site_properties=[{"magmom": 1}],
        )


def test_added_site_properties_are_copied():
    molecule = Molecule(["C"], [[0, 0, 0]])
    props = {"tag": "added", "nested": {"value": 1}}

    result = molecule.add_atom("O", [2, 0, 0], site_properties=props)
    props["tag"] = "changed"
    props["nested"]["value"] = 2

    assert result.site_properties[1]["tag"] == "added"
    assert result.site_properties[1]["nested"]["value"] == 1


def test_molecule_sites_returns_safe_snapshots():
    molecule = Molecule(
        ["C", "O"],
        [[0, 0, 0], [1.2, 0, 0]],
        site_properties=[{"tag": "carbon"}, {"tag": "oxygen"}],
    )

    assert molecule.formula == "CO"
    leaked = molecule.sites
    for attr, value in (("specie", "N"), ("position", [9, 9, 9]), ("properties", {"tag": "x"})):
        with pytest.raises(AttributeError):
            setattr(leaked[0], attr, value)
    leaked[0].properties["tag"] = "changed"  # returned dict is a copy

    assert molecule.species == ("C", "O")
    assert molecule.formula == "CO"
    assert molecule.sites[0].specie == "C"
    assert molecule.sites[0].position.tolist() == [0, 0, 0]
    assert molecule.sites[0].properties["tag"] == "carbon"


def test_molecule_index_returns_single_safe_snapshot(monkeypatch):
    molecule = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])

    def fail_full_sites_rebuild():
        raise AssertionError("indexed access should not rebuild every site")

    monkeypatch.setattr(molecule, "_initialize_sites", fail_full_sites_rebuild)
    site = molecule[0]
    with pytest.raises(AttributeError):
        site.specie = "N"
    assert molecule[0].specie == "C"
    assert molecule.species == ("C", "O")


def test_crystal_sites_returns_safe_snapshots():
    crystal = Crystal(
        ["Si", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(10),
        site_properties=[{"tag": "silicon"}, {"tag": "oxygen"}],
    )

    original_formula = crystal.formula
    leaked = crystal.sites
    with pytest.raises(AttributeError):
        leaked[0].specie = "C"
    leaked[0].properties["tag"] = "changed"  # returned dict is a copy

    assert crystal.species == ("Si", "O")
    assert crystal.formula == original_formula
    assert crystal.sites[0].specie == "Si"
    assert crystal.sites[0].frac_position.tolist() == [0, 0, 0]
    assert crystal.sites[0].properties["tag"] == "silicon"


def test_crystal_index_returns_single_safe_snapshot(monkeypatch):
    crystal = Crystal(
        ["Si", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(10),
    )

    def fail_full_sites_rebuild():
        raise AssertionError("indexed access should not rebuild every site")

    monkeypatch.setattr(crystal, "_initialize_sites", fail_full_sites_rebuild)
    site = crystal[0]
    with pytest.raises(AttributeError):
        site.specie = "C"
    assert crystal[0].specie == "Si"
    assert crystal.species == ("Si", "O")
