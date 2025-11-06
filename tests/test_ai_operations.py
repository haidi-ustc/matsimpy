"""Tests for AI operations (prediction, analysis, optimization)."""
import unittest
from unittest.mock import Mock, MagicMock
from matsimpy.core import Crystal, Lattice
from matsimpy.ai import (
    PropertyPrediction,
    AIAnalysis,
    AIOptimization,
    AIInterface
)


class TestPropertyPrediction(unittest.TestCase):
    """Tests for PropertyPrediction operation."""
    
    def setUp(self):
        """Set up mock AI interface and crystal."""
        self.mock_interface = Mock(spec=AIInterface)
        self.mock_interface.is_connected = True
        
        # Create test crystal
        self.crystal = Crystal(
            ['Ti', 'O', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            Lattice.cubic(4.0)
        )
    
    def test_predict_band_gap(self):
        """Test band gap prediction."""
        self.mock_interface.call.return_value = {"band_gap": 3.2}
        
        pred = PropertyPrediction(self.mock_interface)
        band_gap = pred.predict_band_gap(self.crystal)
        
        self.assertEqual(band_gap, 3.2)
        self.mock_interface.call.assert_called_once()
        call_args = self.mock_interface.call.call_args
        # call_args is (args, kwargs) tuple
        self.assertEqual(call_args[0][0] if call_args[0] else call_args[1].get('operation'), "predict_band_gap")
    
    def test_predict_formation_energy(self):
        """Test formation energy prediction."""
        self.mock_interface.call.return_value = {"formation_energy": -2.5}
        
        pred = PropertyPrediction(self.mock_interface)
        energy = pred.predict_formation_energy(self.crystal)
        
        self.assertEqual(energy, -2.5)
    
    def test_predict_bulk_modulus(self):
        """Test bulk modulus prediction."""
        self.mock_interface.call.return_value = {"bulk_modulus": 250.0}
        
        pred = PropertyPrediction(self.mock_interface)
        modulus = pred.predict_bulk_modulus(self.crystal)
        
        self.assertEqual(modulus, 250.0)
    
    def test_predict_properties(self):
        """Test multiple property prediction."""
        self.mock_interface.call.return_value = {
            "properties": {
                "band_gap": 3.2,
                "formation_energy": -2.5,
                "bulk_modulus": 250.0
            }
        }
        
        pred = PropertyPrediction(self.mock_interface)
        properties = pred.predict_properties(self.crystal, ['band_gap', 'formation_energy'])
        
        self.assertIn("band_gap", properties)
        self.assertIn("formation_energy", properties)
        self.assertEqual(properties["band_gap"], 3.2)
    
    def test_predict_properties_all(self):
        """Test predicting all available properties."""
        self.mock_interface.call.return_value = {
            "properties": {"band_gap": 3.2, "formation_energy": -2.5}
        }
        
        pred = PropertyPrediction(self.mock_interface)
        properties = pred.predict_properties(self.crystal)
        
        self.assertIsInstance(properties, dict)
    
    def test_execute(self):
        """Test execute method."""
        self.mock_interface.call.return_value = {
            "properties": {"band_gap": 3.2}
        }
        
        pred = PropertyPrediction(self.mock_interface)
        result = pred.execute(crystal=self.crystal, properties=['band_gap'])
        
        self.assertIn("band_gap", result)


class TestAIAnalysis(unittest.TestCase):
    """Tests for AIAnalysis operation."""
    
    def setUp(self):
        """Set up mock AI interface and crystal."""
        self.mock_interface = Mock(spec=AIInterface)
        self.mock_interface.is_connected = True
        
        self.crystal = Crystal(
            ['Si'],
            [[0, 0, 0]],
            Lattice.cubic(5.43)
        )
    
    def test_analyze_structure(self):
        """Test structure analysis."""
        self.mock_interface.call.return_value = {
            "analysis": {
                "stability": "stable",
                "symmetry": "cubic",
                "issues": []
            }
        }
        
        analysis = AIAnalysis(self.mock_interface)
        result = analysis.analyze_structure(self.crystal)
        
        self.assertIn("stability", result)
        self.mock_interface.call.assert_called_once()
    
    def test_analyze_structure_with_type(self):
        """Test analysis with specific type."""
        self.mock_interface.call.return_value = {
            "analysis": {"stability_score": 0.95}
        }
        
        analysis = AIAnalysis(self.mock_interface)
        result = analysis.analyze_structure(self.crystal, "stability")
        
        self.assertIsInstance(result, dict)
    
    def test_suggest_improvements(self):
        """Test improvement suggestions."""
        self.mock_interface.call.return_value = {
            "suggestions": [
                {"modification": "increase lattice parameter", "reason": "better stability"}
            ]
        }
        
        analysis = AIAnalysis(self.mock_interface)
        suggestions = analysis.suggest_improvements(self.crystal)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
    
    def test_suggest_improvements_with_target(self):
        """Test improvement suggestions with target property."""
        self.mock_interface.call.return_value = {
            "suggestions": [{"modification": "adjust band gap"}]
        }
        
        analysis = AIAnalysis(self.mock_interface)
        suggestions = analysis.suggest_improvements(self.crystal, "band_gap")
        
        self.assertIsInstance(suggestions, list)
    
    def test_compare_structures(self):
        """Test structure comparison."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = Crystal(['Ge'], [[0,0,0]], Lattice.cubic(5.65))
        
        self.mock_interface.call.return_value = {
            "comparison": {
                "similarity": 0.85,
                "differences": ["lattice parameter", "composition"]
            }
        }
        
        analysis = AIAnalysis(self.mock_interface)
        result = analysis.compare_structures([crystal1, crystal2])
        
        self.assertIn("similarity", result)
    
    def test_validate_structure(self):
        """Test structure validation."""
        self.mock_interface.call.return_value = {
            "validation": {
                "valid": True,
                "issues": [],
                "warnings": []
            }
        }
        
        analysis = AIAnalysis(self.mock_interface)
        result = analysis.validate_structure(self.crystal)
        
        self.assertIn("valid", result)
    
    def test_execute(self):
        """Test execute method."""
        self.mock_interface.call.return_value = {
            "analysis": {"stability": "stable"}
        }
        
        analysis = AIAnalysis(self.mock_interface)
        result = analysis.execute(structure=self.crystal, analysis_type="stability")
        
        self.assertIsInstance(result, dict)


class TestAIOptimization(unittest.TestCase):
    """Tests for AIOptimization operation."""
    
    def setUp(self):
        """Set up mock AI interface and crystal."""
        self.mock_interface = Mock(spec=AIInterface)
        self.mock_interface.is_connected = True
        
        self.crystal = Crystal(
            ['Ti', 'O', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            Lattice.cubic(4.0)
        )
    
    def test_optimize_for_property(self):
        """Test property optimization."""
        self.mock_interface.call.return_value = {
            "species": ['Ti', 'O', 'O'],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.1, 0, 0], [0, 4.1, 0], [0, 0, 4.1]]
        }
        
        opt = AIOptimization(self.mock_interface)
        optimized = opt.optimize_for_property(self.crystal, "band_gap", target_value=2.0)
        
        self.assertIsInstance(optimized, Crystal)
        self.assertNotEqual(optimized.lattice.a, self.crystal.lattice.a)
    
    def test_optimize_for_property_maximize(self):
        """Test property optimization with maximize."""
        self.mock_interface.call.return_value = {
            "species": ['Ti', 'O', 'O'],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.2, 0, 0], [0, 4.2, 0], [0, 0, 4.2]]
        }
        
        opt = AIOptimization(self.mock_interface)
        optimized = opt.optimize_for_property(
            self.crystal, "band_gap", maximize=True, max_iterations=5
        )
        
        self.assertIsInstance(optimized, Crystal)
    
    def test_optimize_stability(self):
        """Test stability optimization."""
        self.mock_interface.call.return_value = {
            "species": ['Ti', 'O', 'O'],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[3.9, 0, 0], [0, 3.9, 0], [0, 0, 3.9]]
        }
        
        opt = AIOptimization(self.mock_interface)
        optimized = opt.optimize_stability(self.crystal)
        
        self.assertIsInstance(optimized, Crystal)
    
    def test_optimize_lattice_parameters(self):
        """Test lattice parameter optimization."""
        self.mock_interface.call.return_value = {
            "species": ['Ti', 'O', 'O'],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.05, 0, 0], [0, 4.05, 0], [0, 0, 4.05]]
        }
        
        opt = AIOptimization(self.mock_interface)
        optimized = opt.optimize_lattice_parameters(self.crystal, target_density=4.5)
        
        self.assertIsInstance(optimized, Crystal)
    
    def test_optimize_lattice_with_constraints(self):
        """Test lattice optimization with constraints."""
        self.mock_interface.call.return_value = {
            "species": ['Ti', 'O', 'O'],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.0, 0, 0], [0, 4.0, 0], [0, 0, 4.0]]
        }
        
        opt = AIOptimization(self.mock_interface)
        constraints = {"space_group": 225}
        optimized = opt.optimize_lattice_parameters(self.crystal, constraints=constraints)
        
        self.assertIsInstance(optimized, Crystal)
    
    def test_execute(self):
        """Test execute method."""
        self.mock_interface.call.return_value = {
            "species": ['Ti', 'O', 'O'],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.1, 0, 0], [0, 4.1, 0], [0, 0, 4.1]]
        }
        
        opt = AIOptimization(self.mock_interface)
        optimized = opt.execute(
            crystal=self.crystal,
            property_name="band_gap",
            target_value=2.0
        )
        
        self.assertIsInstance(optimized, Crystal)


if __name__ == '__main__':
    unittest.main()

