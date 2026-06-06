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
from matsimpy.storage import DataStorage

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
        storage = DataStorage(use_memory_store=True)
        self.assertEqual(storage.store_type, 'memory')
        self.assertIsNone(storage.store_path)
        storage.close()
    
    def test_init_json_store(self):
        """Test initialization with JSON store."""
        storage = DataStorage(store_path=str(self.store_path))
        self.assertEqual(storage.store_type, 'json')
        self.assertEqual(storage.store_path, self.store_path)
        self.assertTrue(self.store_path.exists())
        storage.close()
    
    def test_store_dict(self):
        """Test storing dictionary data."""
        storage = DataStorage(use_memory_store=True)
        data = {'energy': -10.5, 'forces': [[0, 0, 0]]}
        doc_id = storage.store_data(data)
        self.assertIsInstance(doc_id, str)
        self.assertEqual(len(doc_id), 32)  # MD5 hash length
        storage.close()
    
    def test_store_crystal(self):
        """Test storing Crystal structure."""
        storage = DataStorage(use_memory_store=True)
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        crystal = from_prototype('diamond', 'Si', 5.43)
        doc_id = storage.store_data(crystal)
        
        # Retrieve and verify
        retrieved = storage.retrieve_data(doc_id)
        self.assertIn('doc_id', retrieved)
        self.assertIn('stored_at', retrieved)
        self.assertIn('@module', retrieved)  # MSONable structure
        storage.close()
    
    def test_store_with_metadata(self):
        """Test storing data with metadata."""
        storage = DataStorage(use_memory_store=True)
        data = {'energy': -10.5}
        metadata = {'calculator': 'LJ', 'temperature': 300}
        doc_id = storage.store_data(data, metadata=metadata)
        
        retrieved = storage.retrieve_data(doc_id)
        self.assertEqual(retrieved['metadata'], metadata)
        storage.close()

    def test_metadata_changes_generated_doc_id(self):
        """Generated IDs include metadata so distinct records do not collide."""
        storage = DataStorage(use_memory_store=True)
        data = {'energy': -10.5}

        first_id = storage.store_data(data, metadata={'calculator': 'LJ'})
        second_id = storage.store_data(data, metadata={'calculator': 'DFT'})

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(
            storage.retrieve_data(first_id)['metadata']['calculator'],
            'LJ',
        )
        self.assertEqual(
            storage.retrieve_data(second_id)['metadata']['calculator'],
            'DFT',
        )
        storage.close()
    
    def test_store_with_custom_id(self):
        """Test storing data with custom document ID."""
        storage = DataStorage(use_memory_store=True)
        data = {'energy': -10.5}
        custom_id = 'my_custom_id'
        doc_id = storage.store_data(data, doc_id=custom_id)
        self.assertEqual(doc_id, custom_id)
        storage.close()
    
    def test_retrieve_by_id(self):
        """Test retrieving data by document ID."""
        storage = DataStorage(use_memory_store=True)
        data = {'energy': -10.5, 'forces': [[0, 0, 0]]}
        doc_id = storage.store_data(data)
        
        retrieved = storage.retrieve_data(doc_id)
        self.assertEqual(retrieved['energy'], -10.5)
        storage.close()
    
    def test_retrieve_nonexistent(self):
        """Test retrieving non-existent document."""
        storage = DataStorage(use_memory_store=True)
        retrieved = storage.retrieve_data('nonexistent_id')
        self.assertEqual(retrieved, {})
        storage.close()
    
    def test_retrieve_all(self):
        """Test retrieving all documents."""
        storage = DataStorage(use_memory_store=True)
        
        # Store multiple documents
        for i in range(5):
            storage.store_data({'index': i})
        
        all_docs = storage.retrieve_data()
        self.assertIsInstance(all_docs, list)
        self.assertEqual(len(all_docs), 5)
        storage.close()
    
    def test_retrieve_with_query(self):
        """Test retrieving documents with query."""
        storage = DataStorage(use_memory_store=True)
        
        # Store documents with different metadata
        storage.store_data(
            {'energy': -10.0},
            metadata={'calculator': 'LJ'}
        )
        storage.store_data(
            {'energy': -20.0},
            metadata={'calculator': 'DFT'}
        )
        storage.store_data(
            {'energy': -15.0},
            metadata={'calculator': 'LJ'}
        )
        
        # Query for LJ results
        lj_results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})
        self.assertEqual(len(lj_results), 2)
        
        # Verify all are LJ
        for result in lj_results:
            self.assertEqual(result['metadata']['calculator'], 'LJ')
        storage.close()
    
    def test_delete_data(self):
        """Test deleting data."""
        storage = DataStorage(use_memory_store=True)
        doc_id = storage.store_data({'energy': -10.5})
        
        # Delete
        success = storage.delete_data(doc_id)
        self.assertTrue(success)
        
        # Verify deleted
        retrieved = storage.retrieve_data(doc_id)
        self.assertEqual(retrieved, {})
        
        # Delete non-existent
        success = storage.delete_data('nonexistent')
        self.assertFalse(success)
        storage.close()
    
    def test_count_documents(self):
        """Test counting documents."""
        storage = DataStorage(use_memory_store=True)
        
        # Store multiple documents
        for i in range(5):
            storage.store_data({'index': i})
        
        count = storage.count_documents()
        self.assertEqual(count, 5)
        
        # Count with query
        storage.store_data({'type': 'test'}, metadata={'category': 'test'})
        test_count = storage.count_documents(query={'metadata.category': 'test'})
        self.assertEqual(test_count, 1)
        storage.close()
    
    def test_clear_store(self):
        """Test clearing all data from store."""
        storage = DataStorage(use_memory_store=True)
        
        # Store some data
        for i in range(5):
            storage.store_data({'index': i})
        
        self.assertEqual(storage.count_documents(), 5)
        
        # Clear
        storage.clear_store()
        self.assertEqual(storage.count_documents(), 0)
        storage.close()
    
    def test_context_manager(self):
        """Test using storage as context manager."""
        with DataStorage(use_memory_store=True) as storage:
            doc_id = storage.store_data({'test': 'data'})
            retrieved = storage.retrieve_data(doc_id)
            self.assertEqual(retrieved['test'], 'data')
        # Store should be closed automatically

    def test_close_is_idempotent(self):
        """Closing storage more than once should be a no-op."""
        storage = DataStorage(use_memory_store=True)
        storage.close()
        storage.close()
    
    def test_as_dict_from_dict(self):
        """Test serialization and deserialization."""
        storage = DataStorage(use_memory_store=True)
        storage_dict = storage.as_dict()
        
        self.assertIn('@module', storage_dict)
        self.assertIn('@class', storage_dict)
        self.assertEqual(storage_dict['store_type'], 'memory')
        
        # Recreate from dict
        storage2 = DataStorage.from_dict(storage_dict)
        self.assertEqual(storage2.store_type, 'memory')
        
        storage.close()
    
    def test_json_store_persistence(self):
        """Test that JSON store persists data across instances."""
        # Create storage and store data
        storage1 = DataStorage(store_path=str(self.store_path))
        doc_id = storage1.store_data({'test': 'data'})
        storage1.close()
        
        # Create new storage instance
        storage2 = DataStorage(store_path=str(self.store_path))
        retrieved = storage2.retrieve_data(doc_id)
        self.assertEqual(retrieved['test'], 'data')
        storage2.close()
    
    def test_crystal_roundtrip(self):
        """Test storing and retrieving Crystal structure."""
        storage = DataStorage(use_memory_store=True)
        
        # Store crystal
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        crystal = from_prototype('diamond', 'Si', 5.43)
        doc_id = storage.store_data(crystal)
        
        # Retrieve and restore
        crystal_dict = storage.retrieve_data(doc_id)
        crystal_restored = Crystal.from_dict(crystal_dict)
        
        # Verify
        self.assertEqual(crystal.formula, crystal_restored.formula)
        self.assertEqual(len(crystal), len(crystal_restored))
        storage.close()

class TestCanonicalDocIDs(unittest.TestCase):
    """Tests for type-aware canonical document ID generation."""

    def test_distinct_ids_for_numpy_array_vs_string(self):
        import numpy as np
        from matsimpy.storage.maggma_store import _stable_doc_id

        id_array = _stable_doc_id({'x': np.array([1, 2])})
        id_string = _stable_doc_id({'x': '[1 2]'})
        self.assertNotEqual(id_array, id_string)

    def test_distinct_ids_for_numpy_scalar_vs_string(self):
        import numpy as np
        from matsimpy.storage.maggma_store import _stable_doc_id

        id_scalar = _stable_doc_id({'x': np.int64(5)})
        id_string = _stable_doc_id({'x': '5'})
        self.assertNotEqual(id_scalar, id_string)

    def test_distinct_ids_for_datetime_vs_iso_string(self):
        from datetime import datetime
        from matsimpy.storage.maggma_store import _stable_doc_id

        ts = datetime(2024, 1, 1, 12, 0, 0)
        id_dt = _stable_doc_id({'x': ts})
        id_str = _stable_doc_id({'x': '2024-01-01 12:00:00'})
        self.assertNotEqual(id_dt, id_str)

    def test_distinct_ids_for_path_vs_string(self):
        from pathlib import Path
        from matsimpy.storage.maggma_store import _stable_doc_id

        id_path = _stable_doc_id({'x': Path('/tmp/test')})
        id_str = _stable_doc_id({'x': '/tmp/test'})
        self.assertNotEqual(id_path, id_str)

    def test_stable_ids_for_identical_payloads(self):
        from matsimpy.storage.maggma_store import _stable_doc_id

        payload = {'energy': -10.5, 'forces': [[0.0, 0.0, 0.0]]}
        first = _stable_doc_id(payload)
        second = _stable_doc_id(payload)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)

    def test_different_payloads_produce_different_ids(self):
        from matsimpy.storage.maggma_store import _stable_doc_id

        id1 = _stable_doc_id({'a': 1})
        id2 = _stable_doc_id({'a': 2})
        self.assertNotEqual(id1, id2)

        id3 = _stable_doc_id({'a': 1, 'b': 2})
        id4 = _stable_doc_id({'a': 1})
        self.assertNotEqual(id3, id4)

class TestStorageEdgeCases(unittest.TestCase):

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / 'test_storage.json'

    def tearDown(self):
        import shutil
        from pathlib import Path
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_retrieve_data_empty_doc_id_raises(self):
        """Empty doc_id must raise ValueError, not fall through to all-documents."""
        storage = DataStorage(use_memory_store=True)
        storage.store_data({'test': 'data'}, doc_id='custom')
        with self.assertRaises(ValueError):
            storage.retrieve_data(doc_id='')
        storage.close()

    def test_retrieve_data_none_doc_id_returns_all(self):
        """None doc_id should still return all documents."""
        storage = DataStorage(use_memory_store=True)
        for i in range(3):
            storage.store_data({'index': i})
        result = storage.retrieve_data(doc_id=None)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        storage.close()

    def test_query_empty_dict_is_explicit(self):
        """query={} should be treated as explicit query, not no-query."""
        storage = DataStorage(use_memory_store=True)
        storage.store_data({'type': 'a'})
        storage.store_data({'type': 'b'})
        result = storage.retrieve_data(query={})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        storage.close()

    def test_json_store_auto_flush_makes_writes_durable(self):
        """After store_data with JSON store, data visible to new reader."""
        storage1 = DataStorage(store_path=str(self.store_path))
        doc_id = storage1.store_data({'test': 'auto_flush'})
        storage1.close()

        storage2 = DataStorage(store_path=str(self.store_path))
        retrieved = storage2.retrieve_data(doc_id)
        self.assertEqual(retrieved['test'], 'auto_flush')
        storage2.close()

    def test_store_rejects_invalid_custom_doc_id(self):
        """Custom doc_id must be a non-empty string."""
        storage = DataStorage(use_memory_store=True)
        with self.assertRaises(ValueError):
            storage.store_data({'test': 'data'}, doc_id='')
        with self.assertRaises(ValueError):
            storage.store_data({'test': 'data'}, doc_id=0)
        storage.close()

    def test_store_rejects_metadata_overwrite(self):
        """Payload with 'metadata' key must not be overwritten by explicit arg."""
        storage = DataStorage(use_memory_store=True)
        with self.assertRaises(ValueError):
            storage.store_data(
                {'result': 'ok', 'metadata': {'user': 'data'}},
                metadata={'calculator': 'LJ'},
            )
        storage.close()

    def test_store_allows_payload_metadata_without_explicit_arg(self):
        """Payload 'metadata' is fine when no explicit metadata arg given."""
        storage = DataStorage(use_memory_store=True)
        doc_id = storage.store_data({'result': 'ok', 'metadata': {'user': 'data'}})
        retrieved = storage.retrieve_data(doc_id)
        self.assertEqual(retrieved['metadata'], {'user': 'data'})
        storage.close()

class TestStreaming(unittest.TestCase):

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / 'test_storage.json'

    def tearDown(self):
        import shutil
        from pathlib import Path
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_iter_data_yields_without_materializing_all(self):
        storage = DataStorage(use_memory_store=True)
        for i in range(20):
            storage.store_data({'index': i})
        results = list(storage.iter_data())
        self.assertEqual(len(results), 20)
        storage.close()

    def test_iter_data_with_limit(self):
        storage = DataStorage(use_memory_store=True)
        for i in range(10):
            storage.store_data({'index': i})
        results = list(storage.iter_data(limit=3))
        self.assertEqual(len(results), 3)
        storage.close()

    def test_iter_data_with_skip(self):
        storage = DataStorage(use_memory_store=True)
        for i in range(5):
            storage.store_data({'index': i})
        results = list(storage.iter_data(skip=2))
        self.assertEqual(len(results), 3)
        storage.close()

    def test_iter_data_with_query(self):
        storage = DataStorage(use_memory_store=True)
        storage.store_data({'type': 'a'}, metadata={'cat': 'x'})
        storage.store_data({'type': 'b'}, metadata={'cat': 'y'})
        storage.store_data({'type': 'c'}, metadata={'cat': 'x'})
        results = list(storage.iter_data(query={'metadata.cat': 'x'}))
        self.assertEqual(len(results), 2)
        storage.close()

if __name__ == '__main__':
    unittest.main()
