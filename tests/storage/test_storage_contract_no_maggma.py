"""Storage contract tests that do not require the real maggma package."""


import pytest

from matsimpy.storage.maggma_store import MaggmaBackend
from matsimpy.storage import DataStorage, MemoryBackend


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


