"""Comprehensive tests for Element and periodic_table module."""
import unittest

from matsimpy.core import Element

class TestElementComprehensive(unittest.TestCase):
    """Comprehensive tests for Element class."""
    
    def test_element_init(self):
        """Test element initialization."""
        h = Element('H')
        self.assertEqual(h.symbol, 'H')
    
    def test_element_init_invalid(self):
        """Test invalid element symbol."""
        with self.assertRaises(ValueError):
            Element('Xx')
    
    def test_element_from_Z(self):
        """Test creation from atomic number."""
        h = Element.from_Z(1)
        self.assertEqual(h.symbol, 'H')
        
        he = Element.from_Z(2)
        self.assertEqual(he.symbol, 'He')
    
    def test_element_from_Z_invalid_low(self):
        """Test invalid atomic number (too low)."""
        with self.assertRaises(ValueError):
            Element.from_Z(0)
    
    def test_element_from_Z_invalid_high(self):
        """Test invalid atomic number (too high)."""
        with self.assertRaises(ValueError):
            Element.from_Z(200)
    
    def test_element_get_element_caching(self):
        """Test Element.get_element with caching."""
        h1 = Element.get_element('H')
        h2 = Element.get_element('H')
        # Should be same object (cached)
        self.assertIs(h1, h2)
    
    def test_element_get_element_case_insensitive(self):
        """Test get_element is case insensitive."""
        h1 = Element.get_element('H')
        h2 = Element.get_element('h')
        self.assertEqual(h1.symbol, h2.symbol)
    
    def test_element_str(self):
        """Test string representation."""
        h = Element('H')
        self.assertEqual(str(h), 'H')
    
    def test_element_repr(self):
        """Test representation."""
        h = Element('H')
        self.assertIn('Element', repr(h))
        self.assertIn('H', repr(h))
    
    def test_element_properties(self):
        """Test various element properties."""
        h = Element('H')
        
        # Test atomic properties
        self.assertEqual(h.atomic_no, 1)
        self.assertIsInstance(h.atomic_mass, (int, float))
        self.assertGreater(h.atomic_mass, 0)
        
        # Test name
        self.assertIsInstance(h.name, str)
    
    def test_element_electronegativity(self):
        """Test electronegativity property."""
        h = Element('H')
        # X and x should be same (alias)
        self.assertEqual(h.X, h.x)
    
    def test_element_radius_properties(self):
        """Test radius-related properties."""
        fe = Element('Fe')
        
        # These may be None, but should not raise errors
        _ = fe.radius
        _ = fe.calculated_radius
        _ = fe.atomic_radius
        _ = fe.atomic_radius_calculated
        _ = fe.metallic_radius
        _ = fe.van_der_waals_radius
        _ = fe.ionic_radii
        _ = fe.shannon_radii
    
    def test_element_physical_properties(self):
        """Test physical property access."""
        fe = Element('Fe')
        
        # These may be None, but should not raise errors
        _ = fe.melting_point
        _ = fe.boiling_point
        _ = fe.density_of_solid
        _ = fe.thermal_conductivity
        _ = fe.electrical_resistivity
    
    def test_element_mechanical_properties(self):
        """Test mechanical property access."""
        fe = Element('Fe')
        
        # These may be None, but should not raise errors
        _ = fe.youngs_modulus
        _ = fe.bulk_modulus
        _ = fe.rigidity_modulus  # Use rigidity_modulus instead of shear_modulus
        _ = fe.poissons_ratio
        _ = fe.vickers_hardness
        _ = fe.brinell_hardness
        _ = fe.mineral_hardness
    
    def test_element_electronic_properties(self):
        """Test electronic property access."""
        h = Element('H')
        
        # These may be None, but should not raise errors
        _ = h.electronic_structure
        _ = h.atomic_orbitals
        _ = h.oxidation_states
        _ = h.common_oxidation_states
    
    def test_element_iupac_ordering(self):
        """Test IUPAC ordering property."""
        h = Element('H')
        # Should handle both key formats
        _ = h.iupac_ordering
    
    def test_element_chemical_properties(self):
        """Test chemical property access."""
        o = Element('O')
        
        # These may be None, but should not raise errors
        _ = o.oxidation_states
        _ = o.common_oxidation_states
        _ = o.mendeleev_no
    
    def test_element_thermodynamic_properties(self):
        """Test thermodynamic property access."""
        h = Element('H')
        
        # These may be None, but should not raise errors
        _ = h.critical_temperature
        _ = h.superconduction_temperature
        _ = h.liquid_range
    
    def test_element_optical_properties(self):
        """Test optical property access."""
        fe = Element('Fe')
        
        # These may be None, but should not raise errors
        _ = fe.reflectivity
        _ = fe.refractive_index
    
    def test_element_other_properties(self):
        """Test other miscellaneous properties."""
        h = Element('H')
        
        # These may be None, but should not raise errors
        _ = h.molar_volume
        _ = h.velocity_of_sound
        _ = h.coefficient_of_linear_thermal_expansion
        _ = h.rigidity_modulus
    
    def test_element_all_elements(self):
        """Test that all elements can be created."""
        from matsimpy.core.periodic_table import ELEMENTS
        
        for symbol in ELEMENTS[:10]:  # Test first 10
            elem = Element(symbol)
            self.assertEqual(elem.symbol, symbol)
    
    def test_element_caching_consistency(self):
        """Test that caching works consistently."""
        h1 = Element('H')
        h2 = Element.get_element('H')
        h3 = Element.from_Z(1)
        
        # All should have same symbol
        self.assertEqual(h1.symbol, h2.symbol)
        self.assertEqual(h1.symbol, h3.symbol)

if __name__ == '__main__':
    unittest.main()

