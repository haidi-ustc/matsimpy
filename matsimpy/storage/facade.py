"""
DataStorage facade — high-level API composing codec + backend.

This is the user-facing API. It composes:
- DocumentCodec: encodes/decodes MatSimPy objects ↔ DocumentEnvelope
- StoreBackend: persists/retrieves document dicts
"""

from __future__ import annotations

import logging
from typing import Optional, Union

from monty.json import MSONable

from ..core import Structure
from .codec import DocumentCodec
from .memory_store import MemoryBackend
from .backend import StoreBackend
from .schema import DocumentEnvelope

logger = logging.getLogger(__name__)


class DataStorage:
    """High-level storage API composing codec + backend.

    Default backend is MemoryBackend (in-memory, for testing).
    Use MaggmaBackend for persistent JSON storage.
    """

    def __init__(self, backend: Optional[StoreBackend] = None):
        self.codec = DocumentCodec()
        self.backend = backend if backend is not None else MemoryBackend()
        self.backend.connect()

    def store_data(
        self,
        data: Union[dict, MSONable],
        doc_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Store data and return the document ID."""
        if isinstance(data, MSONable):
            envelope = self.codec.encode(data, metadata=metadata)
            if doc_id is not None:
                envelope = DocumentEnvelope(
                    doc_id=doc_id,
                    payload=envelope.payload,
                    schema_version=envelope.schema_version,
                    metadata=envelope.metadata,
                )
        elif isinstance(data, dict):
            metadata = metadata or {}
            DocumentEnvelope.validate_metadata(metadata)
            if doc_id is None:
                doc_id = DocumentEnvelope.generate_id(data, metadata)
            envelope = DocumentEnvelope(
                doc_id=doc_id,
                payload=data,
                metadata=metadata,
            )
        else:
            raise TypeError(
                f"Expected MSONable or dict, got {type(data).__name__}"
            )

        self.backend.put(envelope.doc_id, envelope.to_dict())
        logger.info("Stored data with ID: %s", envelope.doc_id)
        return envelope.doc_id

    def retrieve_data(self, doc_id: str):
        """Retrieve a stored document by its document ID.

        Returns a MatSimPy Structure if the payload contains MSON metadata,
        otherwise the raw payload dict.

        Raises:
            KeyError: If doc_id is not found.
        """
        doc = self.backend.get(doc_id)
        if doc is None:
            raise KeyError(f"Document not found: {doc_id!r}")
        envelope = DocumentEnvelope.from_dict(doc)
        return self._unwrap(envelope)

    def query(
        self,
        criteria: dict,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """Query stored documents and return decoded results."""
        docs = self.backend.query(criteria, limit=limit, offset=offset)
        results = []
        for doc in docs:
            envelope = DocumentEnvelope.from_dict(doc)
            results.append(self._unwrap(envelope))
        return results

    def _unwrap(self, envelope: DocumentEnvelope):
        """Decode envelope payload if it has MSON metadata, else return raw dict."""
        payload = envelope.payload
        if isinstance(payload, dict) and "@module" in payload and "@class" in payload:
            return self.codec.decode(envelope)
        return payload

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID. Return True if it existed."""
        return self.backend.delete(doc_id)

    def flush(self) -> None:
        """Force pending writes to durable storage."""
        self.backend.flush()

    def close(self) -> None:
        """Close the storage backend."""
        self.backend.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


__all__ = ["DataStorage"]
