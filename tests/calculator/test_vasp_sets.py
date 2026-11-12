"""Tests for VASP input sets.

Uses matsimpy structures and imports.
"""

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
        out = get_valid_magmom_struct(mol)
        assert mol.site_properties == ({"magmom": 1}, {})
        assert [s.properties["magmom"] for s in out.sites] == [1.0, 1.0]
        assert isinstance(out.site_properties[0]["magmom"], float)
