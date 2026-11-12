"""Tests for bulk crystal builders."""
import unittest
import sys
import types
from unittest.mock import patch
import numpy as np
from matsimpy.core import Crystal
from matsimpy.builders.bulk import (
    from_prototype,
    list_prototypes,
    CRYSTAL_PROTOTYPES,
    random_crystal,
)


def _sorted_rows(values, decimals=8):
    rounded = np.round(np.asarray(values, dtype=float), decimals)
    return rounded[np.lexsort(rounded.T[::-1])]


class TestPrototypeBuilder(unittest.TestCase):
    """Tests for prototype-based bulk crystal generation."""
    
    
    
    
    
    
    def test_from_prototype_wurtzite(self):
        """Test wurtzite structure generation."""
        gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
        
        self.assertEqual(len(gan.species), 2)
        self.assertIn('Ga', gan.species)
        self.assertIn('N', gan.species)
        # Check hexagonal lattice
        self.assertAlmostEqual(gan.lattice.a, 3.19, places=2)
        self.assertAlmostEqual(gan.lattice.c, 5.19, places=2)
    
    
    
    def test_from_prototype_invalid(self):
        """Test invalid prototype name."""
        with self.assertRaises(ValueError):
            from_prototype('invalid_prototype', 'Cu', 3.61)
    
    def test_from_prototype_wrong_species_count(self):
        """Test with wrong number of species."""
        with self.assertRaises(ValueError):
            # Rocksalt needs 2 species, providing 1
            from_prototype('rocksalt', 'Na', 5.64)
    
    def test_list_prototypes(self):
        """Test listing available prototypes."""
        prototypes = list_prototypes()
        
        self.assertIsInstance(prototypes, dict)
        self.assertIn('fcc', prototypes)
        self.assertIn('bcc', prototypes)
        self.assertIn('diamond', prototypes)
        self.assertGreater(len(prototypes), 5)
    
    def test_crystal_prototypes_constant(self):
        """Test CRYSTAL_PROTOTYPES constant."""
        self.assertIsInstance(CRYSTAL_PROTOTYPES, dict)
        self.assertIn('fcc', CRYSTAL_PROTOTYPES)
        self.assertIn('description', CRYSTAL_PROTOTYPES['fcc'])
        self.assertIn('positions', CRYSTAL_PROTOTYPES['fcc'])

    def test_primitive_prototypes_match_ase_metric_invariants(self):
        """Primitive prototype metrics should match ASE reference conventions."""
        from ase.build import bulk

        references = [
            ('fcc', 'Cu', 3.61, 'fcc'),
            ('bcc', 'Fe', 2.87, 'bcc'),
            ('diamond', 'Si', 5.43, 'diamond'),
        ]
        for prototype, element, lattice_constant, ase_crystalstructure in references:
            with self.subTest(prototype=prototype):
                crystal = from_prototype(prototype, element, lattice_constant)
                atoms = bulk(
                    element,
                    ase_crystalstructure,
                    a=lattice_constant,
                    cubic=False,
                )
                self.assertEqual(len(crystal), len(atoms))
                np.testing.assert_allclose(
                    sorted([crystal.lattice.a, crystal.lattice.b, crystal.lattice.c]),
                    sorted(atoms.cell.lengths()),
                    rtol=1e-7,
                    atol=1e-7,
                )
                np.testing.assert_allclose(
                    sorted([crystal.lattice.alpha, crystal.lattice.beta, crystal.lattice.gamma]),
                    sorted(atoms.cell.angles()),
                    rtol=1e-7,
                    atol=1e-7,
                )
                np.testing.assert_allclose(
                    _sorted_rows(crystal.frac_positions % 1.0),
                    _sorted_rows(atoms.get_scaled_positions() % 1.0),
                    rtol=1e-7,
                    atol=1e-7,
                )

class TestPrototypeProperties(unittest.TestCase):
    """Test properties of generated prototypes."""
    
    
    
    
    
    def test_binary_compound_formula(self):
        """Test binary compound formula parsing (e.g., 'SiC')."""
        # Test diamond with SiC
        sic = from_prototype('diamond', 'SiC', 5.2)
        self.assertEqual(len(sic.species), 2)
        self.assertIn('Si', sic.species)
        self.assertIn('C', sic.species)
        
        # Test zincblende with GaN
        gan = from_prototype('zincblende', 'GaN', 4.5)
        self.assertEqual(len(gan.species), 2)
        self.assertIn('Ga', gan.species)
        self.assertIn('N', gan.species)
        
        # Test rocksalt with NaCl
        nacl = from_prototype('rocksalt', 'NaCl', 5.64)
        self.assertEqual(len(nacl.species), 2)
        self.assertIn('Na', nacl.species)
        self.assertIn('Cl', nacl.species)

    def test_single_site_prototype_multi_element_bcc_raises(self):
        with self.assertRaises(ValueError):
            from_prototype('bcc', 'FeCr', 3.0)


class TestRandomCrystal(unittest.TestCase):
    """Tests for PyXtal-backed random crystal generation boundaries."""

    def test_random_crystal_prefers_pymatgen_conversion_path(self):
        """PyXtal structures should convert through pymatgen when available."""
        from pymatgen.core import Lattice as PymatgenLattice
        from pymatgen.core import Structure as PymatgenStructure

        class FakePyXtal:
            valid = True

            def from_random(self, dim, group, species, num_ions, **kwargs):
                self.args = (dim, group, species, num_ions, kwargs)

            def to_pymatgen(self):
                return PymatgenStructure(
                    PymatgenLattice.cubic(3.0),
                    ['Si'],
                    [[0, 0, 0]],
                )

        fake_module = types.ModuleType("pyxtal")
        fake_module.pyxtal = FakePyXtal
        with patch.dict(sys.modules, {"pyxtal": fake_module}):
            crystal = random_crystal(3, 1, ['Si'], [1])

        self.assertIsInstance(crystal, Crystal)
        self.assertEqual(crystal.species, ('Si',))
        self.assertAlmostEqual(crystal.lattice.a, 3.0)

if __name__ == '__main__':
    unittest.main()
