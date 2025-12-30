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
    
    def test_element_lt_comparison(self):
        """Test __lt__ method for sorting by atomic number."""
        h = Element('H')
        o = Element('O')
        fe = Element('Fe')
        
        # Test direct comparison
        self.assertTrue(h < o)
        self.assertTrue(o < fe)
        self.assertFalse(fe < h)
        
        # Test sorting
        elements = [fe, h, o]
        elements.sort()
        self.assertEqual([e.symbol for e in elements], ['H', 'O', 'Fe'])
        
        # Test sorted() function
        sorted_elements = sorted([fe, h, o])
        self.assertEqual([e.symbol for e in sorted_elements], ['H', 'O', 'Fe'])
    
    def test_element_lt_type_error(self):
        """Test __lt__ raises TypeError for non-Element comparison."""
        h = Element('H')
        with self.assertRaises(TypeError):
            _ = h < 1
    
    def test_get_elements_by_period(self):
        """Test get_elements_by_period class method."""
        # Test period 1
        period1 = Element.get_elements_by_period(1)
        self.assertEqual(len(period1), 2)
        self.assertEqual([e.symbol for e in period1], ['H', 'He'])
        
        # Test period 2
        period2 = Element.get_elements_by_period(2)
        self.assertEqual(len(period2), 8)
        self.assertEqual(period2[0].symbol, 'Li')
        self.assertEqual(period2[-1].symbol, 'Ne')
        
        # Verify all elements are in correct period
        for elem in period1:
            self.assertEqual(elem.period, 1)
        for elem in period2:
            self.assertEqual(elem.period, 2)
    
    def test_get_elements_by_period_exclude_strings(self):
        """Test get_elements_by_period with exclude parameter (strings)."""
        # Exclude carbon from period 2
        period2_no_c = Element.get_elements_by_period(2, exclude=['C'])
        symbols = [e.symbol for e in period2_no_c]
        self.assertNotIn('C', symbols)
        self.assertEqual(len(period2_no_c), 7)
        
        # Exclude multiple elements
        period2_excluded = Element.get_elements_by_period(2, exclude=['C', 'N', 'O'])
        symbols = [e.symbol for e in period2_excluded]
        self.assertNotIn('C', symbols)
        self.assertNotIn('N', symbols)
        self.assertNotIn('O', symbols)
        self.assertEqual(len(period2_excluded), 5)
    
    def test_get_elements_by_period_exclude_elements(self):
        """Test get_elements_by_period with exclude parameter (Element instances)."""
        c = Element('C')
        o = Element('O')
        
        # Exclude using Element instances
        period2_excluded = Element.get_elements_by_period(2, exclude=[c, o])
        symbols = [e.symbol for e in period2_excluded]
        self.assertNotIn('C', symbols)
        self.assertNotIn('O', symbols)
        self.assertEqual(len(period2_excluded), 6)
    
    def test_get_elements_by_period_exclude_mixed(self):
        """Test get_elements_by_period with mixed exclude types."""
        c = Element('C')
        # Mix of strings and Element instances
        period2_excluded = Element.get_elements_by_period(2, exclude=[c, 'N', 'O'])
        symbols = [e.symbol for e in period2_excluded]
        self.assertNotIn('C', symbols)
        self.assertNotIn('N', symbols)
        self.assertNotIn('O', symbols)
    
    def test_get_elements_by_period_invalid_period(self):
        """Test get_elements_by_period with invalid period."""
        with self.assertRaises(ValueError):
            Element.get_elements_by_period(0)
        with self.assertRaises(ValueError):
            Element.get_elements_by_period(8)
        with self.assertRaises(ValueError):
            Element.get_elements_by_period(-1)
    
    def test_get_elements_by_period_exclude_invalid_type(self):
        """Test get_elements_by_period with invalid exclude type."""
        with self.assertRaises(TypeError):
            Element.get_elements_by_period(1, exclude=[1, 2, 3])  # Numbers not allowed
    
    def test_get_elements_by_group(self):
        """Test get_elements_by_group class method."""
        # Test group 1 (alkali metals + H)
        group1 = Element.get_elements_by_group(1)
        self.assertGreater(len(group1), 0)
        self.assertIn('H', [e.symbol for e in group1])
        self.assertIn('Li', [e.symbol for e in group1])
        self.assertIn('Na', [e.symbol for e in group1])
        
        # Verify all elements are in correct group
        for elem in group1:
            self.assertEqual(elem.group, 1)
        
        # Test group 18 (noble gases)
        group18 = Element.get_elements_by_group(18)
        self.assertGreater(len(group18), 0)
        self.assertIn('He', [e.symbol for e in group18])
        self.assertIn('Ne', [e.symbol for e in group18])
        
        # Verify all elements are in correct group
        for elem in group18:
            self.assertEqual(elem.group, 18)
    
    def test_get_elements_by_group_exclude_strings(self):
        """Test get_elements_by_group with exclude parameter (strings)."""
        # Exclude helium from group 18
        group18_no_he = Element.get_elements_by_group(18, exclude=['He'])
        symbols = [e.symbol for e in group18_no_he]
        self.assertNotIn('He', symbols)
        
        # Exclude multiple elements
        group1_excluded = Element.get_elements_by_group(1, exclude=['H', 'Li'])
        symbols = [e.symbol for e in group1_excluded]
        self.assertNotIn('H', symbols)
        self.assertNotIn('Li', symbols)
    
    def test_get_elements_by_group_exclude_elements(self):
        """Test get_elements_by_group with exclude parameter (Element instances)."""
        he = Element('He')
        na = Element('Na')
        
        # Exclude using Element instances
        group18_excluded = Element.get_elements_by_group(18, exclude=[he])
        symbols = [e.symbol for e in group18_excluded]
        self.assertNotIn('He', symbols)
        
        group1_excluded = Element.get_elements_by_group(1, exclude=[na])
        symbols = [e.symbol for e in group1_excluded]
        self.assertNotIn('Na', symbols)
    
    def test_get_elements_by_group_exclude_mixed(self):
        """Test get_elements_by_group with mixed exclude types."""
        he = Element('He')
        # Mix of strings and Element instances
        group18_excluded = Element.get_elements_by_group(18, exclude=[he, 'Ne'])
        symbols = [e.symbol for e in group18_excluded]
        self.assertNotIn('He', symbols)
        self.assertNotIn('Ne', symbols)
    
    def test_get_elements_by_group_invalid_group(self):
        """Test get_elements_by_group with invalid group."""
        with self.assertRaises(ValueError):
            Element.get_elements_by_group(0)
        with self.assertRaises(ValueError):
            Element.get_elements_by_group(19)
        with self.assertRaises(ValueError):
            Element.get_elements_by_group(-1)
    
    def test_get_elements_by_group_exclude_invalid_type(self):
        """Test get_elements_by_group with invalid exclude type."""
        with self.assertRaises(TypeError):
            Element.get_elements_by_group(1, exclude=[1, 2, 3])  # Numbers not allowed
    
    def test_get_elements_by_group_sorted(self):
        """Test that get_elements_by_group returns sorted elements."""
        group1 = Element.get_elements_by_group(1)
        atomic_numbers = [e.atomic_no for e in group1]
        # Verify sorted by atomic number
        self.assertEqual(atomic_numbers, sorted(atomic_numbers))
    
    def test_get_elements_by_period_sorted(self):
        """Test that get_elements_by_period returns sorted elements."""
        period2 = Element.get_elements_by_period(2)
        atomic_numbers = [e.atomic_no for e in period2]
        # Verify sorted by atomic number
        self.assertEqual(atomic_numbers, sorted(atomic_numbers))

if __name__ == '__main__':
    unittest.main()

