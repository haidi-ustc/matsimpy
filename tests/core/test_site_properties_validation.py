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
