"""Tests for per-site properties: validation, column API, copies and propagation."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule


def _fe2():
    return Crystal(["Fe", "Fe"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2.87))


def _water():
    return Molecule(["O", "H", "H"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])


def _with_props():
    c = Crystal(["Fe", "O", "O"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.2, 0.3, 0.1]],
                Lattice.cubic(4.0), site_properties=[{"m": 1}, {"m": 2}, {"m": 3}])
    m = Molecule(["O", "H", "C"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
                 site_properties=[{"m": 1}, {"m": 2}, {"m": 3}])
    return [c, m]


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


# --------------------------------------------------------------------------
# Column API
# --------------------------------------------------------------------------


@pytest.mark.parametrize("make", [_fe2, _water])
def test_site_property_column_api(make):
    s = make()
    n = len(s)
    a = s.with_site_property("magmom", np.arange(n, dtype=float))
    assert a.site_property("magmom") == list(range(n))
    assert type(a.site_property("magmom")[0]) is float  # ndarray input -> tolist()
    b = a.with_site_property("tag", ["x"] * n)
    assert b.site_properties[0] == {"magmom": 0.0, "tag": "x"}
    assert b.without_site_property("magmom").site_property("tag") == ["x"] * n
    assert b.without_site_property("magmom", "tag").site_properties == ()
    with pytest.raises(KeyError):
        s.site_property("magmom")
    assert s.site_property("magmom", default=0.0) == [0.0] * n
    with pytest.raises(ValueError):
        s.with_site_property("magmom", [1.0])


def test_with_site_properties_replaces_or_clears_all_rows():
    s = _with_props()[1]
    assert s.with_site_properties([{"m": 5}, {"m": 6}, {"m": 7}]).site_property("m") == [5, 6, 7]
    assert s.with_site_properties(None).site_properties == ()


def test_site_property_values_are_copies():
    s = _fe2().with_site_property("v", [[1, 2, 3], [4, 5, 6]])
    s.site_property("v")[0].append(99)
    assert s.site_property("v")[0] == [1, 2, 3]


def test_site_property_with_partial_rows_needs_a_default():
    s = _fe2().with_site_properties([{"magmom": 2.0}, {}])
    with pytest.raises(KeyError):
        s.site_property("magmom")
    assert s.site_property("magmom", default=None) == [2.0, None]


# --------------------------------------------------------------------------
# Propagation through structure operations
# --------------------------------------------------------------------------


@pytest.mark.parametrize("idx", [0, 1], ids=["crystal", "molecule"])
def test_remove_atom_filters_site_properties(idx):
    r = _with_props()[idx].remove_atom([1])
    assert r.site_property("m") == [1, 3]


@pytest.mark.parametrize("idx", [0, 1], ids=["crystal", "molecule"])
def test_sort_atoms_reorders_site_properties(idx):
    s = _with_props()[idx]
    r = s.sort_atoms("element")
    for sp, m in zip(r.species, r.site_property("m")):
        if s.species.count(sp) == 1:
            assert s.site_property("m")[s.species.index(sp)] == m
    assert sorted(r.site_property("m")) == [1, 2, 3]
