"""Regression tests for site_properties validation and copy isolation."""

import pytest

from matsimpy.core import Crystal, Lattice, Molecule, Site


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


def test_site_properties_are_isolated_from_constructor_input():
    props = [{"charge": 0, "nested": {"spin": 1}}]
    molecule = Molecule(["C"], [[0, 0, 0]], site_properties=props)

    props[0]["charge"] = 9
    props[0]["nested"]["spin"] = 5

    assert molecule.site_properties[0]["charge"] == 0
    assert molecule.site_properties[0]["nested"]["spin"] == 1
    assert molecule.sites[0].properties["charge"] == 0
    assert molecule.sites[0].properties["nested"]["spin"] == 1


def test_structure_site_properties_getter_returns_copies():
    crystal = Crystal(
        ["Si"],
        [[0, 0, 0]],
        Lattice.cubic(10),
        site_properties=[{"tag": "original", "nested": {"value": 1}}],
    )

    leaked = crystal.site_properties
    leaked[0]["tag"] = "changed"
    leaked[0]["nested"]["value"] = 2

    assert crystal.site_properties[0]["tag"] == "original"
    assert crystal.site_properties[0]["nested"]["value"] == 1
    assert crystal.sites[0].properties["tag"] == "original"
    assert crystal.sites[0].properties["nested"]["value"] == 1


def test_site_properties_getter_returns_copies():
    site = Site([0, 0, 0], "C", properties={"tag": "original", "nested": {"value": 1}})

    leaked = site.properties
    leaked["tag"] = "changed"
    leaked["nested"]["value"] = 2

    assert site.properties["tag"] == "original"
    assert site.properties["nested"]["value"] == 1


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
    leaked[0].specie = "N"
    leaked[0].position = [9, 9, 9]
    leaked[0].properties = {"tag": "changed"}

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
    site.specie = "N"

    assert site.specie == "N"
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
    leaked[0].specie = "C"
    leaked[0].properties = {"tag": "changed"}

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
    site.specie = "C"

    assert site.specie == "C"
    assert crystal[0].specie == "Si"
    assert crystal.species == ("Si", "O")
