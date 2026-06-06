"""Storage contract tests that do not require the real maggma package."""

from pathlib import Path

from matsimpy.storage import maggma_store


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
        criteria = criteria or {}
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


def _patch_stores(monkeypatch):
    monkeypatch.setattr(maggma_store, "MAGGMA_AVAILABLE", True)
    monkeypatch.setattr(maggma_store, "MemoryStore", FakeStore)
    monkeypatch.setattr(maggma_store, "JSONStore", FakeJSONStore)


def test_memory_store_contract_without_real_maggma(monkeypatch):
    _patch_stores(monkeypatch)
    storage = maggma_store.DataStorage(use_memory_store=True)

    first_id = storage.store_data(
        {"energy": -1.0},
        metadata={"calculator": "mock"},
    )
    second_id = storage.store_data(
        {"energy": -1.0},
        metadata={"calculator": "mock"},
    )
    other_id = storage.store_data({"energy": -2.0})

    assert first_id == second_id
    assert len(first_id) == 32
    assert storage.retrieve_data(first_id)["metadata"]["calculator"] == "mock"
    assert len(storage.retrieve_data(query={"metadata.calculator": "mock"})) == 1
    assert storage.count_documents() == 2

    assert storage.delete_data(other_id) is True
    assert storage.delete_data("missing") is False
    assert storage.count_documents() == 1

    storage.clear_store()
    assert storage.count_documents() == 0
    storage.close()
    assert storage.store.closed is True


def test_json_store_close_flushes_without_real_maggma(monkeypatch, tmp_path):
    _patch_stores(monkeypatch)
    store_path = tmp_path / "storage.json"

    storage = maggma_store.DataStorage(store_path=store_path)

    assert storage.store_type == "json"
    assert storage.store_path == Path(store_path)
    assert store_path.exists()

    storage.close()
    assert storage.store.updated_json is True
    assert storage.store.closed is True
