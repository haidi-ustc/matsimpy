"""Tests for AI utilities (prompts, formatting, cache)."""
import unittest
import time
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.ai.utils import prompts, formatting
from matsimpy.ai.models.cache import ResponseCache, cached

class TestPromptTemplates(unittest.TestCase):
    """Tests for prompt template utilities."""
    
    def test_get_generation_prompt(self):
        """Test generation prompt."""
        prompt = prompts.get_generation_prompt("TiO2")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("TiO2", prompt)
        self.assertIn("crystal structure", prompt.lower())
    
    def test_get_generation_prompt_with_constraints(self):
        """Test generation prompt with constraints."""
        constraints = {
            "space_group": 136,
            "lattice_params": [4.0, 4.0, 4.0],
            "density": 4.5
        }
        
        prompt = prompts.get_generation_prompt("TiO2", constraints)
        
        self.assertIn("Space group", prompt)
        self.assertIn("136", prompt)
        self.assertIn("density", prompt.lower())
    
    def test_get_prediction_prompt(self):
        """Test prediction prompt."""
        prompt = prompts.get_prediction_prompt("band_gap", "TiO2")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("band_gap", prompt)
        self.assertIn("TiO2", prompt)
    
    def test_get_analysis_prompt(self):
        """Test analysis prompt."""
        prompt = prompts.get_analysis_prompt("stability", "TiO2")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("stability", prompt.lower())
    
    def test_get_analysis_prompt_types(self):
        """Test different analysis types."""
        types = ["stability", "symmetry", "properties", "defects"]
        
        for analysis_type in types:
            prompt = prompts.get_analysis_prompt(analysis_type, "SiC")
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 0)
    
    def test_get_optimization_prompt(self):
        """Test optimization prompt."""
        prompt = prompts.get_optimization_prompt("band_gap", target_value=2.0, maximize=True)
        
        self.assertIsInstance(prompt, str)
        self.assertIn("band_gap", prompt)
        self.assertIn("2.0", prompt)
    
    def test_get_optimization_prompt_maximize(self):
        """Test optimization prompt with maximize."""
        prompt = prompts.get_optimization_prompt("formation_energy", maximize=False)
        
        self.assertIn("minimize", prompt.lower())
    
    def test_get_validation_prompt(self):
        """Test validation prompt."""
        prompt = prompts.get_validation_prompt("TiO2 structure")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("validate", prompt.lower())

class TestFormatting(unittest.TestCase):
    """Tests for formatting utilities."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Ti', 'O', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            Lattice.cubic(4.0)
        )
        
        self.molecule = Molecule(
            ['O', 'H', 'H'],
            [[0, 0, 0], [0.96, 0, 0], [-0.96, 0, 0]]
        )
    
    def test_format_structure_for_ai_crystal(self):
        """Test formatting crystal for AI."""
        data = formatting.format_structure_for_ai(self.crystal)
        
        self.assertIn("species", data)
        self.assertIn("positions", data)
        self.assertIn("lattice", data)
        self.assertIn("formula", data)
        self.assertEqual(len(data["species"]), 3)
        self.assertEqual(len(data["positions"]), 3)
    
    def test_format_structure_for_ai_molecule(self):
        """Test formatting molecule for AI."""
        data = formatting.format_structure_for_ai(self.molecule)
        
        self.assertIn("species", data)
        self.assertIn("positions", data)
        self.assertNotIn("lattice", data)  # Molecules don't have lattice
    
    def test_format_structure_lattice_params(self):
        """Test lattice parameters in formatted data."""
        data = formatting.format_structure_for_ai(self.crystal)
        
        self.assertIn("lattice_params", data)
        self.assertIn("a", data["lattice_params"])
        self.assertIn("volume", data)
    
    def test_parse_structure_from_ai_crystal(self):
        """Test parsing crystal from AI result."""
        result = {
            "species": ["Ti", "O", "O"],
            "positions": [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0.5]],
            "lattice": [[4.0, 0, 0], [0, 4.0, 0], [0, 0, 4.0]]
        }
        
        structure = formatting.parse_structure_from_ai(result)
        
        self.assertIsInstance(structure, Crystal)
        self.assertEqual(len(structure.species), 3)
    
    def test_parse_structure_from_ai_molecule(self):
        """Test parsing molecule from AI result."""
        result = {
            "species": ["O", "H", "H"],
            "positions": [[0, 0, 0], [0.96, 0, 0], [-0.96, 0, 0]]
        }
        
        structure = formatting.parse_structure_from_ai(result)
        
        self.assertIsInstance(structure, Molecule)
        self.assertEqual(len(structure.species), 3)
    
    def test_parse_structure_invalid(self):
        """Test parsing invalid structure."""
        result = {"species": ["Ti"]}  # Missing positions
        
        with self.assertRaises(ValueError):
            formatting.parse_structure_from_ai(result)
    
    def test_format_properties_for_ai(self):
        """Test formatting properties."""
        properties = {
            "band_gap": 3.2,
            "formation_energy": -2.5,
            "bulk_modulus": 250.0
        }
        
        formatted = formatting.format_properties_for_ai(properties)
        
        self.assertIsInstance(formatted, str)
        self.assertIn("band_gap", formatted)
        self.assertIn("3.2", formatted)
    
    def test_format_constraints_for_ai(self):
        """Test formatting constraints."""
        constraints = {
            "space_group": 136,
            "density": 4.5
        }
        
        formatted = formatting.format_constraints_for_ai(constraints)
        
        self.assertIsInstance(formatted, str)
        self.assertIn("space_group", formatted)

class TestResponseCache(unittest.TestCase):
    """Tests for response caching."""
    
    def setUp(self):
        """Set up cache."""
        self.cache = ResponseCache(max_size=10, ttl=1)  # 1 second TTL
    
    def test_cache_set_get(self):
        """Test basic cache set and get."""
        self.cache.set("operation1", {"input": "data"}, {"result": "value"})
        
        result = self.cache.get("operation1", {"input": "data"})
        
        self.assertIsNotNone(result)
        self.assertEqual(result["result"], "value")
    
    def test_cache_miss(self):
        """Test cache miss."""
        result = self.cache.get("operation1", {"input": "different"})
        
        self.assertIsNone(result)
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        self.cache.set("operation1", {"input": "data"}, {"result": "value"})
        
        # Wait for expiration
        time.sleep(1.1)
        
        result = self.cache.get("operation1", {"input": "data"})
        
        self.assertIsNone(result)
    
    def test_cache_size_limit(self):
        """Test cache size limit."""
        # Fill cache beyond limit
        for i in range(15):
            self.cache.set(f"op{i}", {"i": i}, {"result": i})
        
        # Should not exceed max_size
        self.assertLessEqual(self.cache.size(), 10)
    
    def test_cache_clear(self):
        """Test cache clearing."""
        self.cache.set("operation1", {"input": "data"}, {"result": "value"})
        self.assertEqual(self.cache.size(), 1)
        
        self.cache.clear()
        
        self.assertEqual(self.cache.size(), 0)
        result = self.cache.get("operation1", {"input": "data"})
        self.assertIsNone(result)
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        # Same operation and inputs should generate same key
        key1 = self.cache._generate_key("op", {"a": 1, "b": 2})
        key2 = self.cache._generate_key("op", {"b": 2, "a": 1})  # Different order
        
        self.assertEqual(key1, key2)  # Should be same
    
    def test_cache_no_ttl(self):
        """Test cache without TTL."""
        cache = ResponseCache(max_size=10, ttl=None)
        cache.set("operation1", {"input": "data"}, {"result": "value"})
        
        # Wait and check it's still there
        time.sleep(0.5)
        result = cache.get("operation1", {"input": "data"})
        
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()

