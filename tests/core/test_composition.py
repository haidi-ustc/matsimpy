"""Tests for Composition: parsing, formulas, fractions, output and serialization."""

import pytest

from matsimpy.core import Composition


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_nested_groups_are_expanded():
    comp = Composition("Ca(OH)2(CO3)")
    assert (comp["Ca"], comp["O"], comp["H"], comp["C"]) == (1, 5, 2, 1)


@pytest.mark.parametrize("formula", ["", "Ca(OH]2", "Ca(OH2", "2H", "Ca(OH)0", "H02", "Fe()"])
def test_malformed_formulas_raise(formula):
    with pytest.raises(ValueError):
        Composition(formula)


def test_invalid_sort_by_raises():
    with pytest.raises(ValueError):
        Composition("H2O", sort_by="invalid")


@pytest.mark.parametrize("amount", [True, "2"])
def test_from_mapping_rejects_non_numeric_amounts(amount):
    with pytest.raises(TypeError):
        Composition.from_mapping({"Fe": amount})


# --------------------------------------------------------------------------
# Formulas and access
# --------------------------------------------------------------------------


@pytest.mark.parametrize("comp, reduced", [
    (Composition("Fe2O3"), "Fe2O3"),
    (Composition("Ca2Mg2Si4O12"), "CaMgSi2O6"),
    (Composition("O6Fe4", sort_by="alphabet"), "Fe2O3"),
])
def test_reduced_formula(comp, reduced):
    assert comp.reduced_formula == reduced


@pytest.mark.parametrize("formula, anonymous", [("Fe2O3", "A3B2"), ("NaCl", "AB")])
def test_anonymous_formula(formula, anonymous):
    assert Composition(formula).anonymous_formula == anonymous


def test_adding_fractional_compositions():
    total = Composition.from_mapping({"Fe": 0.5, "O": 1.0}) + Composition.from_mapping({"O": 1.5})
    assert total.formula == "Fe0.5O2.5"


def test_formula_is_read_only():
    with pytest.raises(AttributeError):
        Composition("H2O").formula = "CO2"


def test_getitem_returns_zero_for_absent_elements_and_rejects_non_symbols():
    c = Composition("H2O")
    assert c["C"] == 0
    with pytest.raises(KeyError):
        c["h"]


def test_equality_and_repr():
    assert Composition("H2O") == Composition("H2O")
    assert Composition("H2O") != Composition("H2O2")
    assert Composition("H2O") != "H2O"
    assert "H2O" in repr(Composition("H2O"))


# --------------------------------------------------------------------------
# Fractions and mass
# --------------------------------------------------------------------------


def test_mole_and_mass_fractions():
    comp = Composition("Fe2O3")
    assert comp.mole_fractions() == pytest.approx({"Fe": 0.4, "O": 0.6})
    assert sum(comp.mass_fractions().values()) == pytest.approx(1.0)
    assert comp.mass_fractions()["Fe"] > comp.mass_fractions()["O"]


def test_mass_is_cached():
    comp = Composition("Fe2O3")
    mass = comp.mass
    assert comp._cached_mass == mass


# --------------------------------------------------------------------------
# HTML and LaTeX
# --------------------------------------------------------------------------


@pytest.mark.parametrize("comp, html", [
    (Composition("H2O"), "H<sub>2</sub>O"),
    (Composition.from_mapping({"Fe": 0.5, "O": 1.5}), "Fe<sub>0.5</sub>O<sub>1.5</sub>"),
])
def test_to_html(comp, html):
    assert comp.to_html() == html


def test_to_latex_with_fractional_amounts():
    assert Composition.from_mapping({"Fe": 0.5, "O": 1}).to_latex() == "Fe$_{0.5}$O"


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------


def test_as_dict_stores_the_processed_formula_and_round_trips():
    d = Composition("OH2", sort_by="element").as_dict()
    assert d["formula"] == "H2O"
    assert str(Composition.from_dict(d)) == "H2O"
    assert Composition.from_dict({"formula": "H2O"}).formula == "H2O"


def test_json_round_trip():
    comp = Composition("H2O")
    assert Composition.from_json(comp.to_json()) == comp
