"""Maggma-based storage backend for MatSimPy.

Provides persistent storage using maggma's MemoryStore and JSONStore.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

from .schema import _stable_doc_id_legacy

logger = logging.getLogger(__name__)

try:
    from maggma.stores import MemoryStore, JSONStore
    MAGGMA_AVAILABLE = True
except ImportError:
    MAGGMA_AVAILABLE = False
    MemoryStore = None
    JSONStore = None


class MaggmaBackend:
    """Storage backend backed by maggma.

    Supports two store types:
    - ``"memory"``: In-memory (via maggma MemoryStore)
    - ``"json"``: File-based JSON (via maggma JSONStore)
    """

    def __init__(
        self,
        store_path: Optional[Union[str, Path]] = None,
        use_memory_store: bool = False,
        auto_flush: bool = True,
        **kwargs,
    ):
        if not MAGGMA_AVAILABLE:
            raise ImportError(
                "maggma is required for MaggmaBackend. "
                "Install with: pip install maggma"
            )

        self._closed = True
        self.auto_flush = auto_flush

        if use_memory_store:
            self._store = MemoryStore(key="doc_id", **kwargs)
            self.store_type = "memory"
            self.store_path = None
        else:
            if store_path is None:
                store_path = Path("./materials_simulation_data.json")
            else:
                store_path = Path(store_path)

            store_path.parent.mkdir(parents=True, exist_ok=True)

            if not store_path.exists():
                with open(store_path, "w") as f:
                    json.dump([], f)

            self._store = JSONStore(str(store_path), key="doc_id", **kwargs)
            self.store_type = "json"
            self.store_path = store_path

    def connect(self) -> None:
        self._store.connect()
        self._closed = False
        logger.info("MaggmaBackend connected (%s)", self.store_type)

    def put(self, doc_id: str, document: dict) -> None:
        self._store.update(document)
        if self.auto_flush:
            self._flush_store()

    def get(self, doc_id: str) -> dict | None:
        return self._store.query_one(criteria={"doc_id": doc_id})

    def query(
        self, criteria: dict, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        results = list(self._store.query(criteria=criteria))
        return results[offset : offset + limit]

    def delete(self, doc_id: str) -> bool:
        doc = self._store.query_one(criteria={"doc_id": doc_id})
        if doc is None:
            return False
        self._store.remove_docs(criteria={"doc_id": doc_id})
        if self.auto_flush:
            self._flush_store()
        return True

    def flush(self) -> None:
        self._flush_store()

    def _flush_store(self) -> None:
        if self.store_type == "json" and hasattr(self._store, "update_json_file"):
            self._store.update_json_file()

    def close(self) -> None:
        if self._closed:
            return
        self._flush_store()
        self._store.close()
        self._closed = True
        logger.info("MaggmaBackend closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


__all__ = ["MaggmaBackend"]
