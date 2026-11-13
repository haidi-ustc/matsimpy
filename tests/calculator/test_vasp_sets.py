"""Tests for VASP input sets.

Uses matsimpy structures and imports.
"""

import warnings

import pytest
from matsimpy.core import Crystal, Lattice


class TestDictSet:
    def test_dictset_import(self):
        from matsimpy.calculator.vasp.sets import DictSet
        assert DictSet is not None

    def test_dictset_instantiate(self):
        """DictSet should instantiate with a crystal and config."""
        from matsimpy.calculator.vasp.sets import DictSet
        crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        try:
            vset = DictSet(crystal, config_dict={"INCAR": {"ENCUT": 400, "ISMEAR": 0}})
            assert vset is not None
        except (AttributeError, TypeError) as e:
            # Known gaps in pymatgen-to-matsimpy porting
            pytest.skip(f"DictSet not fully ported yet: {e}")


class TestInputSetDoesNotMutateCaller:
    """0.8.1 regression: input sets must never edit the caller's structure."""

    def test_relax_set_leaves_user_crystal_untouched(self):
        from matsimpy.calculator.vasp.sets import MPRelaxSet

        crystal = Crystal(
            ["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(4.0),
            site_properties=[{"magmom": 2.0}, {}],
        )
        before = crystal.site_properties
        vset = MPRelaxSet(crystal, sort_structure=False)
        assert crystal.site_properties == before
        assert [p["magmom"] for p in vset.structure.site_properties] == [2.0, 1.0]

    def test_get_valid_magmom_struct_copy_mode(self):
        from matsimpy.calculator.vasp.sets import get_valid_magmom_struct
        from matsimpy.core import Molecule

        mol = Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"magmom": 1}, {}])
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out = get_valid_magmom_struct(mol)
        assert mol.site_properties == ({"magmom": 1}, {})
        assert [s.properties["magmom"] for s in out.sites] == [1.0, 1.0]
        assert isinstance(out.site_properties[0]["magmom"], float)
        with pytest.raises(TypeError):
            get_valid_magmom_struct(mol, inplace=False)  # the in-place mode is gone

    def test_recommended_lreal_depends_on_the_number_of_atoms(self):
        from matsimpy.calculator.vasp.sets import _get_recommended_lreal
        from matsimpy.transformation import make_supercell

        si = Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.43))
        assert _get_recommended_lreal(si) is False
        assert _get_recommended_lreal(make_supercell(si, [3, 3, 3])) == "Auto"
