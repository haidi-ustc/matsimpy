"""
Tests for BatchProcessor class.
"""

import unittest
import warnings
from matsimpy.transformation.composite import BatchProcessor
from matsimpy.transformation import make_supercell
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Molecule

class TestBatchProcessor(unittest.TestCase):
    """Test cases for BatchProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    
    def test_empty_transformations(self):
        """Test that empty transformations raise error."""
        with self.assertRaises(ValueError):
            BatchProcessor(transformations=[])
    
    def test_invalid_error_handling(self):
        """Test that invalid error_handling raises error."""
        transformations = [lambda s: make_supercell(s, [2, 2, 2])]
        with self.assertRaises(ValueError):
            BatchProcessor(
                transformations=transformations,
                error_handling='invalid'
            )
    
    
    
    def test_process_multiple_structures_parallel(self):
        """Test processing multiple structures in parallel."""
        transformations = [lambda s: make_supercell(s, [2, 2, 2])]
        processor = BatchProcessor(
            transformations=transformations,
            n_workers=2,
            progress=False
        )
        
        crystals = [self.crystal, self.crystal, self.crystal]
        with warnings.catch_warnings():
            # Suppress parallel processing fallback warning if it occurs
            warnings.filterwarnings("ignore", category=UserWarning, message="Parallel processing failed")
            results = processor.process(crystals)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(len(result.structure), len(self.crystal) * 8)
    
    def test_process_empty_list(self):
        """Test processing empty list."""
        transformations = [lambda s: make_supercell(s, [2, 2, 2])]
        processor = BatchProcessor(transformations=transformations)
        
        results = processor.process([])
        self.assertEqual(len(results), 0)
    
    
    
    
    def test_error_handling_log(self):
        """Test error handling with 'log' strategy."""
        def failing_transform(s):
            raise ValueError("Test error")
        
        transformations = [failing_transform]
        processor = BatchProcessor(
            transformations=transformations,
            n_workers=1,
            progress=False,
            error_handling='log'
        )
        
        # Should not raise, but log errors
        results = processor.process([self.crystal])
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
    
    
    
    def test_repr(self):
        """Test string representation."""
        transformations = [lambda s: make_supercell(s, [2, 2, 2])]
        processor = BatchProcessor(
            transformations=transformations,
            n_workers=4,
            error_handling='skip'
        )
        
        repr_str = repr(processor)
        self.assertIn("BatchProcessor", repr_str)
        self.assertIn("4", repr_str)  # n_workers
        self.assertIn("skip", repr_str)  # error_handling
    

if __name__ == '__main__':
    unittest.main()

