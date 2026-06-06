"""Storage contract tests that do not require the real maggma package."""

from pathlib import Path

import pytest

from matsimpy.storage.maggma_store import MaggmaBackend
from matsimpy.storage import DataStorage, MemoryBackend


class FakeStore:
    def __init__(self, *args, **kwargs):
        self.docs = {}
        self.connected = False
        self.closed = False
        self.updated_json = False

    def connect(self):
        self.connected = True

    def update(self, doc):
        self.docs[doc["doc_id"]] = dict(doc)

    def query_one(self, criteria):
        for doc in self.docs.values():
            if _matches(doc, criteria):
                return dict(doc)
        return None

    def query(self, criteria=None, limit=100):
        if criteria is None:
            criteria = {}
        count = 0
        for doc in self.docs.values():
            if _matches(doc, criteria):
                yield dict(doc)
                count += 1
                if count >= limit:
                    return

    def remove_docs(self, criteria):
        to_remove = [
            doc_id
            for doc_id, doc in self.docs.items()
            if _matches(doc, criteria)
        ]
        for doc_id in to_remove:
            del self.docs[doc_id]

    def count(self, criteria=None):
        return sum(1 for _ in self.query(criteria=criteria or {}))

    def update_json_file(self):
        self.updated_json = True

    def close(self):
        self.closed = True


class FakeJSONStore(FakeStore):
    pass


def _matches(doc, criteria):
    for key, expected in (criteria or {}).items():
        current = doc
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        if current != expected:
            return False
    return True


def test_memory_store_contract(monkeypatch):
    """Test DataStorage with MemoryBackend (no maggma needed)."""
    storage = DataStorage(backend=MemoryBackend())
    first_id = storage.store_data(
        {"energy": -1.0},
        metadata={"calculator": "mock"},
    )
    second_id = storage.store_data(
        {"energy": -1.0},
        metadata={"calculator": "mock"},
    )
    other_id = storage.store_data({"energy": -2.0})
    different_metadata_id = storage.store_data(
        {"energy": -1.0},
        metadata={"calculator": "other"},
    )

    assert first_id == second_id
    assert first_id != different_metadata_id
    assert len(first_id) == 64  # sha256 = 64 hex chars
    assert storage.retrieve_data(first_id) is not None

    assert storage.delete(other_id) is True
    assert storage.delete("missing") is False

    # Query by metadata
    storage2 = DataStorage(backend=MemoryBackend())
    storage2.store_data({"val": 1}, metadata={"tag": "A"})
    storage2.store_data({"val": 2}, metadata={"tag": "B"})
    results = storage2.query({"metadata.tag": "A"}, limit=10)
    assert len(results) == 1

    storage.close()
    storage2.close()


def test_maggma_backend_constructor_reports_missing_maggma(monkeypatch):
    """Constructing MaggmaBackend without maggma should raise clear hint."""
    from matsimpy.storage import maggma_store
    monkeypatch.setattr(maggma_store, "MAGGMA_AVAILABLE", False)
    with pytest.raises(ImportError, match="pip install maggma"):
        MaggmaBackend(use_memory_store=True)


def test_default_storage_is_memory():
    """DataStorage() defaults to MemoryBackend - no maggma needed."""
    storage = DataStorage()
    assert isinstance(storage.backend, MemoryBackend)
    doc_id = storage.store_data({"test": 1})
    assert storage.retrieve_data(doc_id) is not None
    storage.close()
