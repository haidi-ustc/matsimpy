"""
Tests for TransformationPipeline class.
"""

import unittest
import tempfile
import os
from matsimpy.transformation.composite import TransformationPipeline
from matsimpy.transformation import translate, rotate, make_supercell
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Molecule
import json
import numpy as np
import pytest
from matsimpy.transformation import chain, apply_transformations

class TestTransformationPipeline(unittest.TestCase):
    """Test cases for TransformationPipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    
    
    def test_add_step_chaining(self):
        """Test method chaining for add_step."""
        pipeline = (TransformationPipeline()
                   .add_step(translate, vector=[1, 1, 1])
                   .add_step(rotate, angle=90, axis=[0, 0, 1]))
        
        self.assertEqual(len(pipeline), 2)
    
    
    
    
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


def test_save_round_trips_numpy_kwargs(tmp_path):
    pipeline = TransformationPipeline("array_kwargs")
    pipeline.add_step(translate, vector=np.array([0.0, 0.0, 1.0]))
    pipeline.save(tmp_path / "p.json")
    kwargs = TransformationPipeline.load(tmp_path / "p.json").steps[0]["kwargs"]
    assert isinstance(kwargs["vector"], np.ndarray)
    np.testing.assert_allclose(kwargs["vector"], [0, 0, 1])


def test_save_rejects_opaque_kwargs(tmp_path):
    pipeline = TransformationPipeline("opaque")
    pipeline.add_step(translate, vector=[0, 0, 0], opaque=object())
    with pytest.raises(TypeError):
        pipeline.save(tmp_path / "p.json")


def test_save_rejects_functions_that_cannot_be_imported_by_name(tmp_path):
    pipeline = TransformationPipeline("p")
    pipeline.add_step(lambda s: s)
    with pytest.raises(ValueError, match="cannot be saved"):
        pipeline.save(tmp_path / "p.json")
    assert not (tmp_path / "p.json").exists()


def test_save_stores_the_function_name(tmp_path):
    pipeline = TransformationPipeline("ok").add_step(translate, vector=[1.0, 0.0, 0.0])
    pipeline.save(tmp_path / "ok.json")
    assert json.loads((tmp_path / "ok.json").read_text())["steps"][0]["func_name"] == "translate"


def test_chain_and_apply_transformations_apply_functions_in_order():
    molecule = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])
    shift = lambda s: translate(s, [1, 0, 0])  # noqa: E731
    turn = lambda s: rotate(s, 90, [0, 0, 1], center=[0, 0, 0])  # noqa: E731
    np.testing.assert_allclose(chain(molecule, [shift, turn]).positions, [[0, 1, 0], [0, 2.2, 0]], atol=1e-12)
    np.testing.assert_allclose(apply_transformations(molecule, shift).positions[0], [1, 0, 0])


if __name__ == '__main__':
    unittest.main()

