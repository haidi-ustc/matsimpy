"""
Tests for TransformationPipeline class.
"""

import unittest
import tempfile
import os
from pathlib import Path
from matsimpy.transformation.composite import TransformationPipeline
from matsimpy.transformation import translate, rotate, make_supercell
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Molecule


class TestTransformationPipeline(unittest.TestCase):
    """Test cases for TransformationPipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_pipeline_creation(self):
        """Test creating a pipeline."""
        pipeline = TransformationPipeline("test_pipeline")
        self.assertEqual(pipeline.name, "test_pipeline")
        self.assertEqual(len(pipeline), 0)
        self.assertEqual(len(pipeline.steps), 0)
    
    def test_add_step(self):
        """Test adding steps to pipeline."""
        pipeline = TransformationPipeline()
        pipeline.add_step(translate, vector=[1, 1, 1])
        pipeline.add_step(rotate, angle=90, axis=[0, 0, 1])
        
        self.assertEqual(len(pipeline), 2)
        self.assertEqual(pipeline.steps[0]['name'], 'translate')
        self.assertEqual(pipeline.steps[1]['name'], 'rotate')
    
    def test_add_step_chaining(self):
        """Test method chaining for add_step."""
        pipeline = (TransformationPipeline()
                   .add_step(translate, vector=[1, 1, 1])
                   .add_step(rotate, angle=90, axis=[0, 0, 1]))
        
        self.assertEqual(len(pipeline), 2)
    
    def test_apply_single_step(self):
        """Test applying pipeline with single step."""
        pipeline = TransformationPipeline()
        pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
        
        result = pipeline.apply(self.crystal)
        
        self.assertEqual(len(result), len(self.crystal) * 8)  # 2^3 = 8
        self.assertIsNot(result, self.crystal)  # Should be new object
    
    def test_apply_multiple_steps(self):
        """Test applying pipeline with multiple steps."""
        pipeline = TransformationPipeline()
        pipeline.add_step(translate, vector=[0, 0, 0])
        pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
        
        result = pipeline.apply(self.crystal)
        
        self.assertEqual(len(result), len(self.crystal) * 8)
    
    def test_apply_inplace(self):
        """Test applying pipeline in-place."""
        pipeline = TransformationPipeline()
        pipeline.add_step(translate, vector=[1, 1, 1])
        
        original_id = id(self.molecule)
        result = pipeline.apply(self.molecule, inplace=True)
        
        # First step can be inplace, but subsequent steps create new objects
        # So result might be different object
        self.assertIsInstance(result, Molecule)
    
    def test_apply_empty_pipeline(self):
        """Test applying empty pipeline."""
        pipeline = TransformationPipeline()
        
        result = pipeline.apply(self.crystal)
        self.assertEqual(len(result), len(self.crystal))
        self.assertIsNot(result, self.crystal)  # Should be copy
    
    def test_apply_batch_sequential(self):
        """Test applying pipeline to multiple structures sequentially."""
        pipeline = TransformationPipeline()
        pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
        
        crystals = [self.crystal, self.crystal, self.crystal]
        results = pipeline.apply_batch(crystals, parallel=False)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(len(result), len(self.crystal) * 8)
    
    def test_apply_batch_parallel(self):
        """Test applying pipeline to multiple structures in parallel."""
        pipeline = TransformationPipeline()
        pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
        
        crystals = [self.crystal, self.crystal, self.crystal]
        results = pipeline.apply_batch(crystals, parallel=True, n_workers=2)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(len(result), len(self.crystal) * 8)
    
    def test_apply_batch_empty(self):
        """Test applying pipeline to empty list."""
        pipeline = TransformationPipeline()
        results = pipeline.apply_batch([])
        self.assertEqual(len(results), 0)
    
    def test_repr(self):
        """Test string representation."""
        pipeline = TransformationPipeline("my_pipeline")
        pipeline.add_step(translate, vector=[1, 1, 1])
        
        repr_str = repr(pipeline)
        self.assertIn("TransformationPipeline", repr_str)
        self.assertIn("my_pipeline", repr_str)
        self.assertIn("1", repr_str)  # Number of steps
    
    def test_save_and_load(self):
        """Test saving and loading pipeline."""
        # Create pipeline
        pipeline = TransformationPipeline("test_pipeline")
        pipeline.add_step(translate, vector=[1, 1, 1])
        pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
        pipeline.metadata = {'description': 'Test pipeline'}
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            pipeline.save(temp_path)
            
            # Load pipeline
            loaded = TransformationPipeline.load(temp_path)
            
            self.assertEqual(loaded.name, "test_pipeline")
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded.metadata, {'description': 'Test pipeline'})
            
            # Test that loaded pipeline works
            result = loaded.apply(self.crystal)
            self.assertEqual(len(result), len(self.crystal) * 8)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        with self.assertRaises(FileNotFoundError):
            TransformationPipeline.load("nonexistent_pipeline.json")
    
    def test_invalid_func_type(self):
        """Test that non-callable functions raise error."""
        pipeline = TransformationPipeline()
        with self.assertRaises(TypeError):
            pipeline.add_step("not_a_function", arg1=1)


if __name__ == '__main__':
    unittest.main()

