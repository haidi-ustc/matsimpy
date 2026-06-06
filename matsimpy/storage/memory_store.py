"""
In-memory storage backend for MatSimPy.

Implements the StoreBackend protocol using a plain Python dict.
Primary use: testing and fast prototyping (no persistence).
"""

from __future__ import annotations


class MemoryBackend:
    """In-memory storage backed by a Python dict.

    Implements the StoreBackend protocol. Data is lost on process exit.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def put(self, doc_id: str, document: dict) -> None:
        self._store[doc_id] = document

    def get(self, doc_id: str) -> dict | None:
        return self._store.get(doc_id)

    def query(
        self, criteria: dict, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        results = []
        for doc in self._store.values():
            if self._matches(doc, criteria):
                results.append(doc)
        return results[offset : offset + limit]

    @staticmethod
    def _matches(doc: dict, criteria: dict) -> bool:
        for key, value in criteria.items():
            parts = key.split(".")
            current = doc
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return False
            if current != value:
                return False
        return True

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._store:
            del self._store[doc_id]
            return True
        return False

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self._store.clear()
        self._connected = False


__all__ = ["MemoryBackend"]
