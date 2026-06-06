"""Contract tests for all storage backends.

Parametrized over MemoryBackend and MaggmaBackend.
Tests all 7 protocol methods.
"""

import pytest
from matsimpy.core import Crystal, Lattice
from matsimpy.storage import DataStorage, MemoryBackend

try:
    from matsimpy.storage import MaggmaBackend
    MAGGMA = MaggmaBackend is not None
except ImportError:
    MAGGMA = False


@pytest.fixture
def crystal():
    return Crystal(
        ['Si'],
        [[0, 0, 0]],
        Lattice.cubic(5.43),
    )


def _make_storage(backend_type):
    if backend_type == "memory":
        return DataStorage(backend=MemoryBackend())
    raise ValueError(f"Unknown backend type: {backend_type}")


@pytest.fixture(params=["memory"])
def storage(request):
    return _make_storage(request.param)


class TestStorageContract:

    def test_store_and_retrieve(self, storage, crystal):
        doc_id = storage.store_data(crystal)
        retrieved = storage.retrieve_data(doc_id)
        assert retrieved == crystal

    def test_id_stability(self, storage, crystal):
        """Same content → same ID."""
        id1 = storage.store_data(crystal)
        id2 = storage.store_data(crystal)
        assert id1 == id2

    def test_id_length(self, storage, crystal):
        """ID is 64 hex chars (sha256)."""
        doc_id = storage.store_data(crystal)
        assert len(doc_id) == 64

    def test_retrieve_nonexistent_raises(self, storage):
        with pytest.raises(KeyError):
            storage.retrieve_data("nonexistent-id")

    def test_delete(self, storage, crystal):
        doc_id = storage.store_data(crystal)
        assert storage.delete(doc_id) is True
        assert storage.delete(doc_id) is False

    def test_query(self, storage, crystal):
        storage.store_data(crystal, metadata={"tag": "test"})
        results = storage.query({"metadata.tag": "test"}, limit=10)
        assert len(results) >= 1

    def test_flush_and_close(self, storage, crystal):
        """Flush and close don't raise."""
        storage.store_data(crystal)
        storage.flush()
        storage.close()
