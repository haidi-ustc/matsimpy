"""
Storage backend protocol.

All storage backends (MemoryBackend, MaggmaBackend, future backends)
must implement the StoreBackend protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StoreBackend(Protocol):
    """Protocol that all storage backends must implement.

    Methods:
        connect(): Initialize/open the backend connection.
        put(doc_id, document): Store a document dict keyed by doc_id.
        get(doc_id): Retrieve a document dict by doc_id, or None.
        query(criteria, limit, offset): Query documents, return list of dicts.
        delete(doc_id): Remove a document by doc_id, return True if existed.
        flush(): Force pending writes to durable storage.
        close(): Release resources and close the connection.
    """

    def connect(self) -> None:
        """Initialize or open the backend connection."""
        ...

    def put(self, doc_id: str, document: dict) -> None:
        """Store *document* dict keyed by *doc_id*."""
        ...

    def get(self, doc_id: str) -> dict | None:
        """Retrieve document dict by *doc_id*, or None if not found."""
        ...

    def query(
        self, criteria: dict, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """Return documents matching *criteria*."""
        ...

    def delete(self, doc_id: str) -> bool:
        """Remove document by *doc_id*. Return True if it existed."""
        ...

    def flush(self) -> None:
        """Force pending writes to durable storage."""
        ...

    def close(self) -> None:
        """Release resources and close the connection."""
        ...


__all__ = ["StoreBackend"]
