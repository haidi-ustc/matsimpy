"""
Tests for data storage module.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import pytest
pytest.importorskip("maggma", reason="maggma not installed")

from matsimpy import Crystal, Lattice
from matsimpy.storage import DataStorage, MemoryBackend, MaggmaBackend


class TestDataStorage(unittest.TestCase):
    """Tests for DataStorage class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / 'test_storage.json'

    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_init_memory_store(self):
        """Test initialization with memory store."""
        storage = DataStorage(backend=MemoryBackend())
        self.assertIsNotNone(storage)
        storage.close()

    def test_init_json_store(self):
        """Test initialization with JSON store."""
        storage = DataStorage(backend=MaggmaBackend(store_path=self.store_path))
        self.assertIsNotNone(storage)
        storage.close()

    def test_default_backend_is_memory(self):
        """Test default backend is MemoryBackend."""
        storage = DataStorage()
        self.assertIsInstance(storage.backend, MemoryBackend)
        storage.close()

    def test_store_and_retrieve_dict(self):
        """Test storing and retrieving a dictionary."""
        storage = DataStorage(backend=MemoryBackend())
        data = {'energy': -10.5}
        doc_id = storage.store_data(data)
        retrieved = storage.retrieve_data(doc_id)
        self.assertIsNotNone(retrieved)
        storage.close()

    def test_store_and_retrieve_crystal(self):
        """Test storing and retrieving a Crystal."""
        storage = DataStorage(backend=MemoryBackend())
        crystal = Crystal(
            ['Si'], [[0, 0, 0]],
            Lattice.cubic(5.43),
        )
        doc_id = storage.store_data(crystal)
        retrieved = storage.retrieve_data(doc_id)
        self.assertEqual(retrieved.formula, crystal.formula)
        self.assertEqual(len(retrieved), len(crystal))
        storage.close()

    def test_delete_data(self):
        """Test deleting data."""
        storage = DataStorage(backend=MemoryBackend())
        doc_id = storage.store_data({'test': 'data'})
        self.assertTrue(storage.delete(doc_id))
        self.assertFalse(storage.delete(doc_id))
        storage.close()

    def test_retrieve_nonexistent(self):
        """Test retrieving non-existent doc raises KeyError."""
        storage = DataStorage(backend=MemoryBackend())
        with self.assertRaises(KeyError):
            storage.retrieve_data('nonexistent')
        storage.close()

    def test_idempotent_id(self):
        """Test that same data gets same ID."""
        storage = DataStorage(backend=MemoryBackend())
        id1 = storage.store_data({'a': 1})
        id2 = storage.store_data({'a': 1})
        self.assertEqual(id1, id2)
        storage.close()

    def test_query(self):
        """Test querying documents."""
        storage = DataStorage(backend=MemoryBackend())
        storage.store_data({'val': 1}, metadata={'tag': 'A'})
        storage.store_data({'val': 2}, metadata={'tag': 'B'})
        storage.store_data({'val': 3}, metadata={'tag': 'A'})
        results = storage.query({'metadata.tag': 'A'}, limit=10)
        self.assertEqual(len(results), 2)
        storage.close()


if __name__ == '__main__':
    unittest.main()
