"""
Tests for BatchProcessor class.
"""

import unittest
import warnings
from matsimpy.transformation.composite import BatchProcessor
from matsimpy.transformation import make_supercell
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Molecule
import pytest

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
    


class _SideEffectThenFail:
    def __init__(self, marker):
        self.marker = marker

    def __call__(self, structure):
        text = self.marker.read_text() if self.marker.exists() else ""
        self.marker.write_text(text + "x")
        raise ValueError("boom")


def test_process_stream_is_lazy_for_sequential_processors():
    molecule = Molecule(["He"], [[0, 0, 0]])

    def source():
        yield molecule
        raise AssertionError("stream was advanced beyond the first item")

    stream = BatchProcessor([lambda s: s.copy()], n_workers=1, progress=False).process_stream(source())
    assert next(stream).success
    with pytest.raises(AssertionError, match="advanced beyond"):
        next(stream)


def test_parallel_raise_mode_does_not_retry_a_failed_transform(tmp_path):
    marker = tmp_path / "calls.txt"
    processor = BatchProcessor([_SideEffectThenFail(marker)], n_workers=2, progress=False, error_handling="raise")
    with pytest.raises(RuntimeError, match="Transformation failed"):
        processor.process([Molecule(["He"], [[0, 0, 0]])])
    assert marker.read_text() == "x"


class _PoolThatDiesAfterOneResult:
    """Reads two items ahead like a real pool, returns one result, then fails."""

    def __init__(self, *args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def imap(self, func, items):
        first, _ = next(items), next(items)
        yield func(first)
        raise OSError("worker died")


def test_process_stream_fallback_resumes_after_the_last_result(monkeypatch):
    import multiprocessing

    class _Context:
        Pool = _PoolThatDiesAfterOneResult

    monkeypatch.setattr(multiprocessing, "get_context", lambda method: _Context())
    molecules = (Molecule(["He"], [[float(i), 0, 0]]) for i in range(4))  # one-shot iterator
    processor = BatchProcessor([lambda s: s], n_workers=2, progress=False)
    with pytest.warns(UserWarning, match="Falling back"):
        results = list(processor.process_stream(molecules))
    assert [r.index for r in results] == [0, 1, 2, 3]
    assert [r.structure.positions[0, 0] for r in results] == [0, 1, 2, 3]


if __name__ == '__main__':
    unittest.main()

